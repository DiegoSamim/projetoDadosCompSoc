"""Banco das páginas, ocorrências e textos: Supabase em produção, memória nos testes.

As duas classes têm a mesma interface. `BancoMemoria` reproduz a semântica das funções SQL de
db/schema.sql (reserva sem repetição, novas tentativas, reserva expirada), para os testes
rodarem sem rede.
"""
import os
import random
import re
from datetime import datetime, timedelta

from dotenv import load_dotenv

from hdb import config


def _int(valor):
    """Número inteiro de um valor vindo de CSV, HTML ou JSON; None se vazio."""
    return int(valor) if valor not in (None, "") else None


def _dados_pagina(linha):
    """Campos da tabela `paginas` a partir de uma linha da busca (ou do .json de uma captura)."""
    return {"bib": str(linha["bib"]), "pagina_fisica": int(linha["pagina_fisica"]),
            "ano": _int(linha.get("ano")), "edicao": linha.get("edicao"),
            "pagina": linha.get("pagina"), "link": linha.get("link")}


def _dados_sucesso(ocr, segundos):
    """Campos de `textos_ocr` e o tempo total, na forma que as duas classes usam."""
    return {"motor": ocr["motor"], "texto": ocr["texto"], "confianca": ocr["confianca"],
            "colunas": ocr["colunas"], "segundos_ocr": ocr["segundos"], "segundos": segundos}


def anos_da_decada(periodo):
    """(início, fim) da década de um período como "1850 - 1859"; None se o texto não tem dois anos."""
    m = re.search(r"(\d{4})\D+(\d{4})", periodo)
    return (int(m.group(1)), int(m.group(2))) if m else None


def cobre_mais_que_a_decada(periodo, ano_inicio, ano_fim):
    """O acervo começa antes ou termina depois do período? None se algum dos anos é desconhecido."""
    decada = anos_da_decada(periodo)
    if decada is None or ano_inicio is None or ano_fim is None:
        return None
    return ano_inicio < decada[0] or ano_fim > decada[1]


def _todas(consulta, tamanho=1000):
    """Todas as linhas de uma consulta ordenada; a API devolve no máximo 1000 por chamada."""
    linhas, inicio = [], 0
    while True:
        lote = consulta.range(inicio, inicio + tamanho - 1).execute().data
        linhas += lote
        if len(lote) < tamanho:
            return linhas
        inicio += tamanho


class BancoSupabase:
    """Acesso ao Supabase com a chave secreta (ignora RLS), lida do .env."""

    def __init__(self):
        from supabase import create_client

        load_dotenv(config.RAIZ / ".env")
        url, chave = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
        faltam = [n for n, v in (("SUPABASE_URL", url), ("SUPABASE_SECRET_KEY", chave)) if not v]
        if faltam:
            raise RuntimeError(f"faltam {' e '.join(faltam)} no arquivo {config.RAIZ / '.env'} "
                               "(ver README, seção Banco e captura)")
        self.cliente = create_client(url, chave)

    def _rpc(self, nome, **params):
        return self.cliente.rpc(nome, params).execute().data

    def garantir_acervo(self, bib, nome):
        self.cliente.table("acervos").upsert(
            {"bib": str(bib), "nome": nome}, on_conflict="bib", ignore_duplicates=True).execute()

    def pagina(self, bib, pagina_fisica):
        """A página como {id, bib, pagina_fisica, status}, ou None se não existe."""
        dados = (self.cliente.table("paginas").select("id,bib,pagina_fisica,status")
                 .eq("bib", str(bib)).eq("pagina_fisica", int(pagina_fisica)).limit(1).execute().data)
        return dados[0] if dados else None

    def garantir_pagina(self, linha):
        """Cria a página como pendente se não existir (sem mexer na que existe). Devolve a página."""
        self.garantir_acervo(linha["bib"], linha.get("acervo"))
        dados = _dados_pagina(linha)
        self.cliente.table("paginas").upsert(
            dados, on_conflict="bib,pagina_fisica", ignore_duplicates=True).execute()
        return self.pagina(dados["bib"], dados["pagina_fisica"])

    def registrar_ocorrencia(self, linha):
        """Grava a página (pendente, se nova) e a ocorrência `linha` (colunas dos CSVs da busca)."""
        pagina = self.garantir_pagina(linha)
        self.cliente.table("ocorrencias").upsert(
            {"pagina_id": pagina["id"], "bib": str(linha["bib"]), "termo": linha["termo"],
             "posicao": int(linha["ocorrencia"]), "total": _int(linha.get("total_ocorrencias"))},
            on_conflict="bib,termo,posicao", ignore_duplicates=True).execute()

    def contar_ocorrencias(self, bib, termo):
        resposta = (self.cliente.table("ocorrencias").select("id", count="exact", head=True)
                    .eq("bib", str(bib)).eq("termo", termo).execute())
        return resposta.count

    def reservar(self, quem, limite, bib=None, termo=None, aleatorio=False, excluir=()):
        """Reserva até `limite` páginas para `quem` (sem os ids de `excluir`); devolve a lista de dicts."""
        return self._rpc("reservar_paginas", p_quem=quem, p_limite=limite, p_bib=bib, p_termo=termo,
                         p_aleatorio=aleatorio, p_max_tentativas=config.MAX_TENTATIVAS,
                         p_expira_min=config.RESERVA_MINUTOS, p_excluir=list(excluir))

    def registrar_sucesso(self, pagina_id, quem, largura, altura, nbytes, ocr, segundos, captchas):
        d = _dados_sucesso(ocr, segundos)
        self._rpc("registrar_sucesso", p_pagina_id=pagina_id, p_quem=quem, p_largura=largura,
                  p_altura=altura, p_bytes=nbytes, p_motor=d["motor"], p_texto=d["texto"],
                  p_confianca=d["confianca"], p_colunas=d["colunas"],
                  p_segundos_ocr=d["segundos_ocr"], p_segundos=segundos, p_captchas=captchas)

    def registrar_reprocesso(self, pagina_id, quem, largura, altura, nbytes, ocr):
        d = _dados_sucesso(ocr, ocr["segundos"])
        self._rpc("registrar_reprocesso", p_pagina_id=pagina_id, p_quem=quem, p_largura=largura,
                  p_altura=altura, p_bytes=nbytes, p_motor=d["motor"], p_texto=d["texto"],
                  p_confianca=d["confianca"], p_colunas=d["colunas"], p_segundos_ocr=d["segundos_ocr"])

    def textos(self, pagina_id):
        """As leituras da página como [{motor, confianca, texto, criado_em}]."""
        return (self.cliente.table("textos_ocr").select("motor,confianca,texto,criado_em")
                .eq("pagina_id", pagina_id).execute().data)

    def registrar_anuncios(self, pagina_id, versao, anuncios):
        """Substitui os anúncios da página nessa versão pelos de `anuncios`. Devolve quantos ficaram."""
        return self._rpc("registrar_anuncios", p_pagina_id=pagina_id, p_versao=versao, p_anuncios=anuncios)

    def anuncios(self, pagina_id, versao=None):
        """Os anúncios da página (de uma versão, ou de todas) em ordem de leitura."""
        consulta = self.cliente.table("anuncios").select("*").eq("pagina_id", pagina_id)
        if versao is not None:
            consulta = consulta.eq("versao", versao)
        return consulta.order("versao").order("ordem").execute().data

    def anuncios_para_campos(self, versao_anuncios):
        """Todos os anúncios da versão como [{id, titulo, abertura, texto}], por id."""
        return _todas(self.cliente.table("anuncios").select("id,titulo,abertura,texto")
                      .eq("versao", versao_anuncios).order("id"))

    def registrar_campos(self, versao, campos):
        """Grava (upsert por anúncio e versão) as linhas [{anuncio_id, tipo, ...}]. Devolve quantas."""
        return self._rpc("registrar_campos", p_versao=versao, p_campos=campos)

    def registrar_erro(self, pagina_id, quem, etapa, erro, segundos, captchas):
        self._rpc("registrar_erro", p_pagina_id=pagina_id, p_quem=quem, p_etapa=etapa,
                  p_erro=erro, p_segundos=segundos, p_captchas=captchas)

    def registrar_acervo_periodo(self, local, periodo, posicao, nome_lista, bib=None, erro=None):
        """Grava (ou regrava) a posição da lista de periódicos de (local, período) com o bib descoberto ou o erro."""
        self.cliente.table("acervos_periodos").upsert(
            {"local": local, "periodo": periodo, "posicao": int(posicao), "nome_lista": nome_lista,
             "bib": bib, "erro": erro, "descoberto_em": datetime.now().isoformat()},
            on_conflict="local,periodo,posicao").execute()

    def acervos_do_periodo(self, local, periodo):
        """As posições já gravadas, em ordem, como [{posicao, nome_lista, bib, erro}]."""
        return _todas(self.cliente.table("acervos_periodos").select("posicao,nome_lista,bib,erro")
                      .eq("local", local).eq("periodo", periodo).order("posicao"))

    def acervo(self, bib):
        """{bib, nome, ano_inicio, ano_fim, total_paginas} do acervo, ou None."""
        dados = (self.cliente.table("acervos").select("bib,nome,ano_inicio,ano_fim,total_paginas")
                 .eq("bib", str(bib)).limit(1).execute().data)
        return dados[0] if dados else None

    def atualizar_acervo(self, bib, nome=None, ano_inicio=None, ano_fim=None, total_paginas=None):
        """Preenche só o que vier (o que for None fica como está)."""
        campos = {k: v for k, v in (("nome", nome), ("ano_inicio", ano_inicio), ("ano_fim", ano_fim),
                                    ("total_paginas", total_paginas)) if v is not None}
        if campos:
            self.cliente.table("acervos").update(campos).eq("bib", str(bib)).execute()

    def registrar_contagem(self, bib, termo, paginas, contado_em=None):
        """Grava (ou atualiza) em quantas páginas do acervo o termo aparece."""
        self.cliente.table("contagens").upsert(
            {"bib": str(bib), "termo": termo, "paginas": int(paginas),
             "contado_em": contado_em or datetime.now().isoformat()}, on_conflict="bib,termo").execute()

    def contagem(self, bib, termo):
        """Páginas com o termo no acervo, ou None se ainda não foi contado."""
        dados = (self.cliente.table("contagens").select("paginas")
                 .eq("bib", str(bib)).eq("termo", termo).limit(1).execute().data)
        return dados[0]["paginas"] if dados else None

    def panorama(self, local, periodo, termo):
        """As linhas da view `panorama` de (local, período, termo)."""
        return _todas(self.cliente.table("panorama").select("*").eq("local", local).eq("periodo", periodo)
                      .eq("termo", termo).order("posicao"))

    def relatorio(self):
        """Os números do relatório metodológico, agregados no banco (função `relatorio_coleta`)."""
        return self._rpc("relatorio_coleta")

    def liberar_reservas(self, quem):
        return self._rpc("liberar_reservas", p_quem=quem)

    def status(self):
        return self._rpc("resumo_status")


class BancoMemoria:
    """Mesma interface de `BancoSupabase`, em dicionários. `agora` permite simular o tempo."""

    def __init__(self, agora=datetime.now):
        self.agora = agora
        self.acervos = {}  # bib -> nome
        self.paginas = {}  # id -> dict
        self.ocorrencias = {}  # (bib, termo, posicao) -> dict
        self.leituras = {}  # (pagina_id, motor) -> dict
        self.tentativas = []
        self.lista_anuncios = {}  # (pagina_id, versao) -> lista de dicts
        self.campos = {}  # (anuncio_id, versao) -> dict
        self.proximo_anuncio = 1
        self.dados_acervos = {}  # bib -> {ano_inicio, ano_fim, total_paginas}
        self.periodos = {}  # (local, periodo, posicao) -> {nome_lista, bib, erro}
        self.contagens = {}  # (bib, termo) -> paginas

    def garantir_acervo(self, bib, nome):
        self.acervos.setdefault(str(bib), nome)

    def pagina(self, bib, pagina_fisica):
        for p in self.paginas.values():
            if p["bib"] == str(bib) and p["pagina_fisica"] == int(pagina_fisica):
                return {c: p[c] for c in ("id", "bib", "pagina_fisica", "status")}
        return None

    def garantir_pagina(self, linha):
        self.garantir_acervo(linha["bib"], linha.get("acervo"))
        dados = _dados_pagina(linha)
        if not self.pagina(dados["bib"], dados["pagina_fisica"]):
            id_ = len(self.paginas) + 1
            self.paginas[id_] = {**dados, "id": id_, "status": "pendente", "tentativas": 0,
                                 "ultimo_erro": None, "etapa_erro": None, "reservada_por": None, "reservada_em": None}
        return self.pagina(dados["bib"], dados["pagina_fisica"])

    def registrar_ocorrencia(self, linha):
        pagina = self.garantir_pagina(linha)
        chave = (str(linha["bib"]), linha["termo"], int(linha["ocorrencia"]))
        self.ocorrencias.setdefault(chave, {"pagina_id": pagina["id"], "bib": chave[0], "termo": chave[1],
                                            "posicao": chave[2], "total": _int(linha.get("total_ocorrencias"))})

    def contar_ocorrencias(self, bib, termo):
        return sum(1 for b, t, _ in self.ocorrencias if b == str(bib) and t == termo)

    def _elegivel(self, p):
        expirada = p["reservada_em"] is not None and p["reservada_em"] < (
            self.agora() - timedelta(minutes=config.RESERVA_MINUTOS))
        return (p["status"] == "pendente"
                or (p["status"] == "erro" and p["etapa_erro"] == "captura"
                    and p["tentativas"] < config.MAX_TENTATIVAS)
                or (p["status"] == "reservada" and expirada))

    def reservar(self, quem, limite, bib=None, termo=None, aleatorio=False, excluir=()):
        com_termo = {o["pagina_id"] for o in self.ocorrencias.values() if o["termo"] == termo}
        candidatas = [p for p in self.paginas.values() if self._elegivel(p) and p["id"] not in excluir
                      and (bib is None or p["bib"] == bib) and (termo is None or p["id"] in com_termo)]
        candidatas.sort(key=lambda p: (p["bib"], p["pagina_fisica"]))
        if aleatorio:
            random.shuffle(candidatas)
        escolhidas = candidatas[:limite]
        for p in escolhidas:
            p.update(status="reservada", reservada_por=quem, reservada_em=self.agora())
        return [{c: p[c] for c in ("id", "bib", "pagina_fisica", "ano", "edicao", "pagina", "link")}
                for p in escolhidas]

    def _tentativa(self, pagina_id, quem, status, etapa, segundos, captchas, erro=None):
        self.tentativas.append({"pagina_id": pagina_id, "quem": quem, "quando": self.agora(),
                                "status": status, "etapa": etapa, "segundos": segundos,
                                "captchas": captchas, "erro": erro})

    def _gravar_texto(self, pagina_id, d):
        self.leituras[(pagina_id, d["motor"])] = {
            "texto": d["texto"], "confianca": d["confianca"], "colunas": d["colunas"],
            "segundos": d["segundos_ocr"], "criado_em": self.agora()}

    def registrar_sucesso(self, pagina_id, quem, largura, altura, nbytes, ocr, segundos, captchas):
        d = _dados_sucesso(ocr, segundos)
        self._gravar_texto(pagina_id, d)
        self.paginas[pagina_id].update(
            status="ok", ultimo_erro=None, etapa_erro=None, reservada_por=None, reservada_em=None,
            largura=largura, altura=altura, bytes=nbytes, capturada_em=self.agora())
        self._tentativa(pagina_id, quem, "ok", "banco", segundos, captchas)

    def registrar_reprocesso(self, pagina_id, quem, largura, altura, nbytes, ocr):
        d = _dados_sucesso(ocr, ocr["segundos"])
        self._gravar_texto(pagina_id, d)
        p = self.paginas[pagina_id]
        if p["status"] != "ok":
            p.update(status="ok", ultimo_erro=None, etapa_erro=None, reservada_por=None, reservada_em=None,
                     largura=largura, altura=altura, bytes=nbytes,
                     capturada_em=p.get("capturada_em") or self.agora())
            self._tentativa(pagina_id, quem, "ok", "ocr", d["segundos_ocr"], 0)

    def textos(self, pagina_id):
        return [{"motor": motor, "confianca": t["confianca"], "texto": t["texto"], "criado_em": t["criado_em"]}
                for (id_, motor), t in self.leituras.items() if id_ == pagina_id]

    def registrar_anuncios(self, pagina_id, versao, anuncios):
        novos = []
        for a in anuncios:  # como no banco, cada anúncio gravado ganha um id novo
            novos.append({**a, "id": self.proximo_anuncio, "pagina_id": pagina_id, "versao": versao,
                          "criado_em": self.agora()})
            self.proximo_anuncio += 1
        self.lista_anuncios[(pagina_id, versao)] = novos
        return len(anuncios)

    def anuncios(self, pagina_id, versao=None):
        return [dict(a) for (id_, v), lista in sorted(self.lista_anuncios.items())
                if id_ == pagina_id and versao in (None, v) for a in sorted(lista, key=lambda a: a["ordem"])]

    def anuncios_para_campos(self, versao_anuncios):
        achados = [a for (_, v), lista in self.lista_anuncios.items() if v == versao_anuncios for a in lista]
        return [{k: a.get(k) for k in ("id", "titulo", "abertura", "texto")} for a in sorted(achados, key=lambda a: a["id"])]

    def registrar_campos(self, versao, campos):
        for c in campos:
            self.campos[(c["anuncio_id"], versao)] = {**c, "versao": versao, "criado_em": self.agora()}
        return len(campos)

    def registrar_erro(self, pagina_id, quem, etapa, erro, segundos, captchas):
        p = self.paginas[pagina_id]
        p.update(status="erro", tentativas=p["tentativas"] + 1, ultimo_erro=erro, etapa_erro=etapa,
                 reservada_por=None, reservada_em=None)
        self._tentativa(pagina_id, quem, "erro", etapa, segundos, captchas, erro)

    def registrar_acervo_periodo(self, local, periodo, posicao, nome_lista, bib=None, erro=None):
        self.periodos[(local, periodo, int(posicao))] = {"nome_lista": nome_lista, "bib": bib, "erro": erro}

    def acervos_do_periodo(self, local, periodo):
        return [{"posicao": pos, **dados} for (l, p, pos), dados in sorted(self.periodos.items())
                if (l, p) == (local, periodo)]

    def acervo(self, bib):
        bib = str(bib)
        if bib not in self.acervos:
            return None
        return {"bib": bib, "nome": self.acervos[bib], "ano_inicio": None, "ano_fim": None,
                "total_paginas": None, **self.dados_acervos.get(bib, {})}

    def atualizar_acervo(self, bib, nome=None, ano_inicio=None, ano_fim=None, total_paginas=None):
        bib = str(bib)
        if bib not in self.acervos:
            return
        if nome is not None:
            self.acervos[bib] = nome
        novos = {"ano_inicio": ano_inicio, "ano_fim": ano_fim, "total_paginas": total_paginas}
        self.dados_acervos.setdefault(bib, {}).update({k: v for k, v in novos.items() if v is not None})

    def registrar_contagem(self, bib, termo, paginas, contado_em=None):
        self.contagens[(str(bib), termo)] = int(paginas)

    def contagem(self, bib, termo):
        return self.contagens.get((str(bib), termo))

    def panorama(self, local, periodo, termo):
        linhas = []
        for item in self.acervos_do_periodo(local, periodo):
            bib = item["bib"]
            paginas = self.contagem(bib, termo) if bib else None
            if paginas is None or bib not in self.acervos:
                continue
            a = self.acervo(bib)
            total = a["total_paginas"]
            linhas.append({
                "local": local, "periodo": periodo, "posicao": item["posicao"], "nome_lista": item["nome_lista"],
                "bib": bib, "nome": a["nome"], "ano_inicio": a["ano_inicio"], "ano_fim": a["ano_fim"],
                "total_paginas": total, "termo": termo, "paginas": paginas,
                "percentual": paginas / total if total else None,
                "cobre_mais_que_a_decada": cobre_mais_que_a_decada(periodo, a["ano_inicio"], a["ano_fim"])})
        return linhas

    def relatorio(self):
        """Mesmas chaves de `relatorio_coleta` (db/schema.sql), calculadas dos dicionários."""
        return {"gerado_em": self.agora().isoformat(), "buscas": self._rel_buscas(),
                "capturas": self._rel_capturas(), "ocr": self._rel_ocr(), "anuncios": self._rel_anuncios(),
                "campos": self._rel_campos(), "panorama": self._rel_panorama()}

    def _rel_buscas(self):
        grupos = {}
        for o in self.ocorrencias.values():
            grupos.setdefault((o["termo"], o["bib"]), []).append(o)
        saida = []
        for (termo, bib), lista in sorted(grupos.items()):
            paginas = {}
            for i in {o["pagina_id"] for o in lista}:
                status = self.paginas[i]["status"]
                paginas[status] = paginas.get(status, 0) + 1
            saida.append({"termo": termo, "bib": bib, "acervo": self.acervos.get(bib),
                          "total_servidor": max((o["total"] for o in lista if o["total"] is not None), default=None),
                          "listadas": len(lista), "primeira_coleta": None, "ultima_coleta": None,
                          "paginas": paginas})
        return saida

    def _rel_capturas(self):
        saida = []
        for quem in sorted({t["quem"] or "(sem nome)" for t in self.tentativas}):
            ts = [t for t in self.tentativas if (t["quem"] or "(sem nome)") == quem]
            erros = {}
            for t in ts:
                if t["status"] == "erro":
                    erros[t["etapa"]] = erros.get(t["etapa"], 0) + 1
            segundos = [t["segundos"] for t in ts if t["segundos"] is not None]
            saida.append({"quem": quem, "ok": sum(t["status"] == "ok" for t in ts), "erros": erros,
                          "captchas": sum(t["captchas"] for t in ts),
                          "segundos_medios": round(sum(segundos) / len(segundos), 1) if segundos else None,
                          "primeira": min(t["quando"] for t in ts).isoformat(),
                          "ultima": max(t["quando"] for t in ts).isoformat()})
        return saida

    def _rel_ocr(self):
        def media(valores):
            valores = [v for v in valores if v is not None]
            return round(sum(valores) / len(valores), 1) if valores else None

        motores = {}
        for (_, motor), t in self.leituras.items():
            motores.setdefault(motor, []).append(t["confianca"])
        atuais = {}  # a leitura mais recente de cada página
        for (pid, _), t in self.leituras.items():
            if pid not in atuais or t["criado_em"] > atuais[pid]["criado_em"]:
                atuais[pid] = t
        por_acervo = {}
        for pid, t in atuais.items():
            por_acervo.setdefault(self.paginas[pid]["bib"], []).append(t["confianca"])
        return {"motores": [{"motor": m, "paginas": len(c), "confianca_media": media(c)}
                            for m, c in sorted(motores.items())],
                "acervos": [{"bib": b, "acervo": self.acervos.get(b), "paginas": len(c),
                             "confianca_media": media(c)} for b, c in sorted(por_acervo.items())]}

    def _rel_anuncios(self):
        versoes = {}
        for (pid, versao), lista in self.lista_anuncios.items():
            v = versoes.setdefault(versao, {"total": 0, "largos": 0, "paginas": set()})
            v["total"] += len(lista)
            v["largos"] += sum(bool(a.get("largo")) for a in lista)
            v["paginas"].add(pid)
        return [{"versao": versao, "total": v["total"], "largos": v["largos"], "paginas": len(v["paginas"])}
                for versao, v in sorted(versoes.items())]

    def _rel_campos(self):
        saida = []
        for versao in sorted({v for _, v in self.campos}):
            cs = [c for (_, v), c in self.campos.items() if v == versao]
            por_tipo, por_sexo, nacoes = {}, {}, {}
            for c in cs:
                tipo, sexo = c.get("tipo") or "(sem tipo)", c.get("sexo") or "(sem sexo)"
                por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
                por_sexo[sexo] = por_sexo.get(sexo, 0) + 1
                for n in c.get("nacoes") or []:
                    nacoes[n] = nacoes.get(n, 0) + 1
            top = sorted(nacoes.items(), key=lambda x: (-x[1], x[0]))[:10]
            saida.append({"versao": versao, "total": len(cs), "por_tipo": por_tipo, "por_sexo": por_sexo,
                          "com_idade": sum(c.get("idade_min") is not None for c in cs),
                          "com_nome": sum(bool(c.get("nomes")) for c in cs),
                          "com_recompensa": sum(bool(c.get("recompensa")) for c in cs),
                          "nacoes": [{"nacao": n, "n": q} for n, q in top]})
        return saida

    def _rel_panorama(self):
        grupos = {}
        for (local, periodo, _), d in self.periodos.items():
            g = grupos.setdefault((local, periodo), {"na_lista": 0, "com_bib": 0, "com_erro": 0})
            g["na_lista"] += 1
            g["com_bib"] += d["bib"] is not None
            g["com_erro"] += d["erro"] is not None
        termos = {}
        for (local, periodo, _), d in self.periodos.items():
            for (bib, termo), paginas in self.contagens.items():
                if bib == d["bib"]:
                    t = termos.setdefault((local, periodo, termo), {"bibs": set(), "paginas": 0})
                    if paginas > 0:
                        t["bibs"].add(bib)
                    t["paginas"] += paginas
        return {"periodos": [{"local": l, "periodo": p, **g} for (l, p), g in sorted(grupos.items())],
                "termos": [{"local": l, "periodo": p, "termo": t, "acervos": len(v["bibs"]),
                            "paginas": v["paginas"]} for (l, p, t), v in sorted(termos.items())]}

    def liberar_reservas(self, quem):
        minhas = [p for p in self.paginas.values() if p["status"] == "reservada" and p["reservada_por"] == quem]
        for p in minhas:
            p.update(status="pendente", reservada_por=None, reservada_em=None)
        return len(minhas)

    def status(self):
        def contar(paginas):
            c = {}
            for p in paginas:
                c[p["status"]] = c.get(p["status"], 0) + 1
            return c

        paginas = list(self.paginas.values())
        termos = {o["termo"] for o in self.ocorrencias.values()}
        erros = sorted((t for t in self.tentativas if t["status"] == "erro"),
                       key=lambda t: t["quando"], reverse=True)[:10]
        captchas = sum(t["captchas"] for t in self.tentativas)
        oks = sum(1 for t in self.tentativas if t["status"] == "ok")
        return {
            "por_status": contar(paginas),
            "por_acervo": {b: contar(p for p in paginas if p["bib"] == b)
                           for b in sorted({p["bib"] for p in paginas})},
            "por_termo": {t: contar(self.paginas[i] for i in
                                    {o["pagina_id"] for o in self.ocorrencias.values() if o["termo"] == t})
                          for t in sorted(termos)},
            "ultimos_erros": [{"bib": self.paginas[t["pagina_id"]]["bib"],
                               "pagina_fisica": self.paginas[t["pagina_id"]]["pagina_fisica"],
                               "etapa": t["etapa"], "erro": t["erro"], "quando": t["quando"].isoformat()}
                              for t in erros],
            "paginas_por_captcha": round(oks / captchas, 1) if captchas else None,
        }
