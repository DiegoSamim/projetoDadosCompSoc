-- Schema da HDB: páginas a capturar, ocorrências dos termos, texto do OCR e log de tentativas.
-- Fonte única do banco: aplicar com apply_migration (nome `schema_inicial`). Idempotente.
-- Só a chave secreta (papel service_role) acessa: RLS ligado, sem políticas, anon/authenticated sem acesso.

create table if not exists public.acervos (
    bib       text primary key,
    nome      text,
    criado_em timestamptz not null default now()
);

create table if not exists public.paginas (
    id            bigint generated always as identity primary key,
    bib           text not null references public.acervos (bib),
    pagina_fisica int  not null,
    ano           smallint,
    edicao        text,
    pagina        text,
    link          text,
    status        text not null default 'pendente'
                  check (status in ('pendente', 'reservada', 'ok', 'erro')),
    tentativas    int  not null default 0,
    ultimo_erro   text,
    etapa_erro    text,  -- etapa da última falha; só falha de captura volta para a fila
    reservada_por text,
    reservada_em  timestamptz,
    largura       int,
    altura        int,
    bytes         int,
    capturada_em  timestamptz,
    criado_em     timestamptz not null default now(),
    atualizado_em timestamptz not null default now(),
    unique (bib, pagina_fisica)
);
alter table public.paginas add column if not exists etapa_erro text;
create index if not exists paginas_fila_idx on public.paginas (status, bib, pagina_fisica);

create table if not exists public.ocorrencias (
    id          bigint generated always as identity primary key,
    pagina_id   bigint not null references public.paginas (id),
    bib         text   not null,
    termo       text   not null,
    posicao     int    not null,
    total       int,
    coletada_em timestamptz not null default now(),
    unique (bib, termo, posicao)  -- retomada da busca
);
create index if not exists ocorrencias_pagina_idx on public.ocorrencias (pagina_id);
create index if not exists ocorrencias_termo_idx on public.ocorrencias (termo);

create table if not exists public.textos_ocr (
    id        bigint generated always as identity primary key,
    pagina_id bigint not null references public.paginas (id),
    motor     text   not null,
    texto     text   not null,
    confianca real,
    colunas   smallint,
    segundos  real,
    busca     tsvector generated always as (to_tsvector('portuguese', texto)) stored,
    criado_em timestamptz not null default now(),
    unique (pagina_id, motor)
);
create index if not exists textos_ocr_busca_idx on public.textos_ocr using gin (busca);

create table if not exists public.tentativas (
    id        bigint generated always as identity primary key,
    pagina_id bigint not null references public.paginas (id),
    quem      text,
    quando    timestamptz not null default now(),
    status    text not null check (status in ('ok', 'erro')),
    etapa     text not null check (etapa in ('captura', 'ocr', 'banco')),
    segundos  real,
    captchas  int not null default 0,
    erro      text
);
create index if not exists tentativas_pagina_idx on public.tentativas (pagina_id);

-- Anúncios separados de cada página por heurística (hdb.layout + hdb.anuncios), por versão da segmentação.
create table if not exists public.anuncios (
    id          bigint generated always as identity primary key,
    pagina_id   bigint not null references public.paginas (id),
    versao      text   not null,
    ordem       int    not null,  -- ordem de leitura na página, a partir de 1
    coluna      smallint,         -- a partir de 1, da esquerda para a direita
    titulo      text,
    abertura    text,             -- palavra de abertura reconhecida ("VENDE-SE"), se houver
    texto_bruto text,
    texto       text,
    confianca   real,
    x0          int,
    y0          int,
    x1          int,
    y1          int,
    n_linhas    int,
    largo       boolean,          -- algum segmento cruza colunas
    busca       tsvector generated always as (to_tsvector('portuguese', texto)) stored,
    criado_em   timestamptz not null default now(),
    unique (pagina_id, versao, ordem)
);
create index if not exists anuncios_pagina_idx on public.anuncios (pagina_id);
create index if not exists anuncios_busca_idx on public.anuncios using gin (busca);


-- Reserva até p_limite páginas para p_quem. Entram as pendentes, as com erro de captura que
-- ainda têm tentativas (erro de OCR não adianta recapturar) e as reservadas há mais de
-- p_expira_min minutos. p_excluir: ids que a execução já tentou, para não voltarem no lote seguinte. skip locked: duas pessoas
-- chamando ao mesmo tempo nunca recebem a mesma página.
create or replace function public.reservar_paginas(
    p_quem text,
    p_limite int,
    p_bib text default null,
    p_termo text default null,
    p_aleatorio boolean default false,
    p_max_tentativas int default 3,
    p_expira_min int default 30,
    p_excluir bigint[] default '{}'
)
returns table (id bigint, bib text, pagina_fisica int, ano smallint, edicao text, pagina text, link text)
language sql
security invoker
set search_path = ''
as $$
    with candidatas as (
        select p.id
        from public.paginas p
        where (p.status = 'pendente'
               or (p.status = 'erro' and p.etapa_erro = 'captura' and p.tentativas < p_max_tentativas)
               or (p.status = 'reservada'
                   and p.reservada_em < now() - make_interval(mins => p_expira_min)))
          and not (p.id = any(p_excluir))
          and (p_bib is null or p.bib = p_bib)
          and (p_termo is null or exists (
                select 1 from public.ocorrencias o
                where o.pagina_id = p.id and o.termo = p_termo))
        order by case when p_aleatorio then random() end, p.bib, p.pagina_fisica
        limit p_limite
        for update of p skip locked
    )
    update public.paginas pg
    set status = 'reservada', reservada_por = p_quem, reservada_em = now(), atualizado_em = now()
    from candidatas c
    where pg.id = c.id
    returning pg.id, pg.bib, pg.pagina_fisica, pg.ano, pg.edicao, pg.pagina, pg.link;
$$;

-- Grava o texto, marca a página como ok (limpando a reserva) e registra a tentativa, tudo
-- numa transação. Repetir a chamada atualiza o texto do mesmo motor.
create or replace function public.registrar_sucesso(
    p_pagina_id bigint,
    p_quem text,
    p_largura int,
    p_altura int,
    p_bytes int,
    p_motor text,
    p_texto text,
    p_confianca real,
    p_colunas smallint,
    p_segundos_ocr real,
    p_segundos real,
    p_captchas int
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    insert into public.textos_ocr (pagina_id, motor, texto, confianca, colunas, segundos)
    values (p_pagina_id, p_motor, p_texto, p_confianca, p_colunas, p_segundos_ocr)
    on conflict (pagina_id, motor) do update
        set texto = excluded.texto, confianca = excluded.confianca,
            colunas = excluded.colunas, segundos = excluded.segundos, criado_em = now();

    update public.paginas
    set status = 'ok', ultimo_erro = null, etapa_erro = null, reservada_por = null, reservada_em = null,
        largura = p_largura, altura = p_altura, bytes = p_bytes,
        capturada_em = now(), atualizado_em = now()
    where id = p_pagina_id;

    insert into public.tentativas (pagina_id, quem, status, etapa, segundos, captchas)
    values (p_pagina_id, p_quem, 'ok', 'banco', p_segundos, p_captchas);
end;
$$;

-- Grava uma releitura do OCR (motor novo ou atualizado). Se a página não estava ok (ex.: OCR que
-- falhou), marca ok, limpa o erro e registra a tentativa; se já estava ok, só o texto muda.
create or replace function public.registrar_reprocesso(
    p_pagina_id bigint,
    p_quem text,
    p_largura int,
    p_altura int,
    p_bytes int,
    p_motor text,
    p_texto text,
    p_confianca real,
    p_colunas smallint,
    p_segundos_ocr real
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    insert into public.textos_ocr (pagina_id, motor, texto, confianca, colunas, segundos)
    values (p_pagina_id, p_motor, p_texto, p_confianca, p_colunas, p_segundos_ocr)
    on conflict (pagina_id, motor) do update
        set texto = excluded.texto, confianca = excluded.confianca,
            colunas = excluded.colunas, segundos = excluded.segundos, criado_em = now();

    if exists (select 1 from public.paginas where id = p_pagina_id and status <> 'ok') then
        update public.paginas
        set status = 'ok', ultimo_erro = null, etapa_erro = null, reservada_por = null, reservada_em = null,
            largura = p_largura, altura = p_altura, bytes = p_bytes,
            capturada_em = coalesce(capturada_em, now()), atualizado_em = now()
        where id = p_pagina_id;

        insert into public.tentativas (pagina_id, quem, status, etapa, segundos, captchas)
        values (p_pagina_id, p_quem, 'ok', 'ocr', p_segundos_ocr, 0);
    end if;
end;
$$;

-- Marca a página como erro, conta a tentativa e guarda o motivo.
create or replace function public.registrar_erro(
    p_pagina_id bigint,
    p_quem text,
    p_etapa text,
    p_erro text,
    p_segundos real,
    p_captchas int
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    update public.paginas
    set status = 'erro', tentativas = tentativas + 1, ultimo_erro = p_erro, etapa_erro = p_etapa,
        reservada_por = null, reservada_em = null, atualizado_em = now()
    where id = p_pagina_id;

    insert into public.tentativas (pagina_id, quem, status, etapa, segundos, captchas, erro)
    values (p_pagina_id, p_quem, 'erro', p_etapa, p_segundos, p_captchas, p_erro);
end;
$$;

-- Troca os anúncios de (página, versão) pelos de p_anuncios (array de objetos com as colunas da tabela),
-- numa transação (a função inteira é uma). Retorna quantos foram gravados.
create or replace function public.registrar_anuncios(p_pagina_id bigint, p_versao text, p_anuncios jsonb)
returns int
language plpgsql
security invoker
set search_path = ''
as $$
declare
    gravados int;
begin
    delete from public.anuncios where pagina_id = p_pagina_id and versao = p_versao;

    insert into public.anuncios (pagina_id, versao, ordem, coluna, titulo, abertura, texto_bruto, texto,
                                 confianca, x0, y0, x1, y1, n_linhas, largo)
    select p_pagina_id, p_versao, a.ordem, a.coluna, a.titulo, a.abertura, a.texto_bruto, a.texto,
           a.confianca, a.x0, a.y0, a.x1, a.y1, a.n_linhas, a.largo
    from jsonb_to_recordset(p_anuncios) as a(
        ordem int, coluna smallint, titulo text, abertura text, texto_bruto text, texto text,
        confianca real, x0 int, y0 int, x1 int, y1 int, n_linhas int, largo boolean);
    get diagnostics gravados = row_count;
    return gravados;
end;
$$;

-- Devolve a pendente o que p_quem deixou reservado (Ctrl+C ou fim da execução). Retorna quantas.
create or replace function public.liberar_reservas(p_quem text)
returns int
language sql
security invoker
set search_path = ''
as $$
    with liberadas as (
        update public.paginas
        set status = 'pendente', reservada_por = null, reservada_em = null, atualizado_em = now()
        where status = 'reservada' and reservada_por = p_quem
        returning 1
    )
    select count(*)::int from liberadas;
$$;

-- Dados do `hdb status`: contagens por status, acervo e termo, últimos erros e páginas por CAPTCHA.
create or replace function public.resumo_status()
returns jsonb
language sql
security invoker
stable
set search_path = ''
as $$
    select jsonb_build_object(
        'por_status', coalesce((
            select jsonb_object_agg(status, n)
            from (select status, count(*) n from public.paginas group by status) s), '{}'),
        'por_acervo', coalesce((
            select jsonb_object_agg(bib, c)
            from (select bib, jsonb_object_agg(status, n) c
                  from (select bib, status, count(*) n from public.paginas group by bib, status) x
                  group by bib) s), '{}'),
        'por_termo', coalesce((
            select jsonb_object_agg(termo, c)
            from (select termo, jsonb_object_agg(status, n) c
                  from (select o.termo, p.status, count(distinct p.id) n
                        from public.ocorrencias o join public.paginas p on p.id = o.pagina_id
                        group by o.termo, p.status) x
                  group by termo) s), '{}'),
        'ultimos_erros', coalesce((
            select jsonb_agg(e)
            from (select p.bib, p.pagina_fisica, t.etapa, t.erro, t.quando
                  from public.tentativas t join public.paginas p on p.id = t.pagina_id
                  where t.status = 'erro'
                  order by t.quando desc limit 10) e), '[]'),
        'paginas_por_captcha', (
            select case when sum(captchas) > 0
                        then round(count(*) filter (where status = 'ok')::numeric / sum(captchas), 1) end
            from public.tentativas)
    );
$$;


-- Texto atual de cada página = a leitura mais recente (criado_em), qualquer que seja o motor.
create or replace view public.textos_atuais with (security_invoker = true) as
    select distinct on (pagina_id) id, pagina_id, motor, texto, confianca, colunas, segundos, criado_em
    from public.textos_ocr
    order by pagina_id, criado_em desc;

-- Segurança: RLS ligado e nenhuma política; só a chave secreta (service_role) acessa.
alter table public.acervos     enable row level security;
alter table public.paginas     enable row level security;
alter table public.ocorrencias enable row level security;
alter table public.textos_ocr  enable row level security;
alter table public.tentativas  enable row level security;
alter table public.anuncios    enable row level security;

revoke all on table public.acervos, public.paginas, public.ocorrencias,
                    public.textos_ocr, public.tentativas, public.anuncios from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on table public.textos_atuais from anon, authenticated;

-- Conforme a configuração da Data API, tabelas novas não ganham grant automático.
grant select, insert, update, delete on table public.acervos, public.paginas, public.ocorrencias,
                                              public.textos_ocr, public.tentativas, public.anuncios to service_role;
grant usage, select on all sequences in schema public to service_role;
grant select on table public.textos_atuais to service_role;

-- O Postgres dá execute a `public` em toda função nova; é isso que anon/authenticated herdam.
revoke all on function public.reservar_paginas(text, int, text, text, boolean, int, int, bigint[])
    from public, anon, authenticated;
revoke all on function public.registrar_sucesso(bigint, text, int, int, int, text, text, real, smallint, real, real, int)
    from public, anon, authenticated;
revoke all on function public.registrar_reprocesso(bigint, text, int, int, int, text, text, real, smallint, real)
    from public, anon, authenticated;
revoke all on function public.registrar_erro(bigint, text, text, text, real, int)
    from public, anon, authenticated;
revoke all on function public.registrar_anuncios(bigint, text, jsonb) from public, anon, authenticated;
revoke all on function public.liberar_reservas(text) from public, anon, authenticated;
revoke all on function public.resumo_status() from public, anon, authenticated;

grant execute on function public.reservar_paginas(text, int, text, text, boolean, int, int, bigint[]) to service_role;
grant execute on function public.registrar_sucesso(bigint, text, int, int, int, text, text, real, smallint, real, real, int) to service_role;
grant execute on function public.registrar_reprocesso(bigint, text, int, int, int, text, text, real, smallint, real) to service_role;
grant execute on function public.registrar_erro(bigint, text, text, text, real, int) to service_role;
grant execute on function public.registrar_anuncios(bigint, text, jsonb) to service_role;
grant execute on function public.liberar_reservas(text) to service_role;
grant execute on function public.resumo_status() to service_role;


-- ============================================================================================
-- Panorama de acervos (hdb.acervos). Nome sugerido da migração: `panorama_acervos`. Idempotente.
-- ============================================================================================

-- Anos e tamanho do acervo, lidos de AcervoDescLbl ("Jornal do Commercio (RJ) - 1850 a 1859") e do leitor.
alter table public.acervos add column if not exists ano_inicio    smallint;
alter table public.acervos add column if not exists ano_fim       smallint;
alter table public.acervos add column if not exists total_paginas int;

-- Lista de periódicos da tela de busca (estado + período). Um periódico pode aparecer em várias décadas, e a
-- posição na lista (os nomes se repetem) permite retomar a descoberta de onde parou.
create table if not exists public.acervos_periodos (
    id            bigint generated always as identity primary key,
    local         text not null,
    periodo       text not null,
    posicao       int  not null,
    nome_lista    text,
    bib           text references public.acervos (bib),
    erro          text,
    descoberto_em timestamptz not null default now(),
    unique (local, periodo, posicao)
);
create index if not exists acervos_periodos_bib_idx on public.acervos_periodos (bib);

-- Em quantas páginas do acervo inteiro o termo aparece (a HDB não filtra a contagem por década).
create table if not exists public.contagens (
    id        bigint generated always as identity primary key,
    bib       text not null references public.acervos (bib),
    termo     text not null,
    paginas   int  not null,
    contado_em timestamptz not null default now(),
    unique (bib, termo)
);

-- Ranking de cada (local, período, termo). `cobre_mais_que_a_decada`: o acervo começa antes ou termina depois
-- da década pedida, então a contagem inclui anos de fora dela (null se os anos do acervo não são conhecidos).
create or replace view public.panorama with (security_invoker = true) as
    select ap.local, ap.periodo, ap.posicao, ap.nome_lista, ap.bib, a.nome,
           a.ano_inicio, a.ano_fim, a.total_paginas,
           c.termo, c.paginas,
           c.paginas::numeric / nullif(a.total_paginas, 0) as percentual,
           case when a.ano_inicio is null or a.ano_fim is null or d.inicio is null then null
                else a.ano_inicio < d.inicio or a.ano_fim > d.fim end as cobre_mais_que_a_decada
    from public.acervos_periodos ap
    join public.acervos a on a.bib = ap.bib
    join public.contagens c on c.bib = ap.bib
    cross join lateral (
        select (m)[1]::int as inicio, (m)[2]::int as fim
        from (select regexp_match(ap.periodo, '(\d{4})\D+(\d{4})') as m) x
    ) d;

alter table public.acervos_periodos enable row level security;
alter table public.contagens        enable row level security;

revoke all on table public.acervos_periodos, public.contagens from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on table public.panorama from anon, authenticated;

grant select, insert, update, delete on table public.acervos_periodos, public.contagens to service_role;
grant usage, select on all sequences in schema public to service_role;
grant select on table public.panorama to service_role;


-- ============================================================================================
-- Campos dos anúncios (hdb.campos). Nome sugerido da migração: `campos_anuncios`. Idempotente.
-- ============================================================================================

-- Classificação e campos extraídos de cada anúncio, por versão da extração (c1, c2...).
create table if not exists public.anuncio_campos (
    anuncio_id bigint not null references public.anuncios (id) on delete cascade,
    versao     text   not null,
    tipo       text,  -- fuga, venda, compra, aluguel, aluguel_incerto (aluguel sem marca de escravizado), ama_de_leite, outro
    procura    boolean,  -- quem anuncia quer obter alguém (COMPRA-SE, PRECISA-SE)
    sexo       text,  -- m, f, ambos
    idade_min  smallint,
    idade_max  smallint,
    nacoes     text[],
    cores      text[],
    condicao   text,  -- escravizado, forro, livre, desconhecida (venda/compra/aluguel/ama sem pista da condição)
    nomes      text[],
    oficios    text[],
    recompensa boolean,
    valor      text,
    endereco   text,
    evidencias jsonb,  -- campo -> trecho do texto que o justificou
    criado_em  timestamptz not null default now(),
    primary key (anuncio_id, versao)
);
create index if not exists anuncio_campos_tipo_idx on public.anuncio_campos (tipo);
create index if not exists anuncio_campos_sexo_idx on public.anuncio_campos (sexo);

-- Grava (upsert por anúncio e versão) um array de objetos com as colunas da tabela. Retorna quantos.
-- Os arrays chegam como arrays JSON; jsonb_to_recordset com coluna text[] NÃO serve (o Postgres leria o JSON
-- como literal de array e falharia), então essas colunas entram como jsonb e viram text[] com
-- jsonb_array_elements_text, na ordem original (with ordinality). Valor ausente ou não-array vira {}.
create or replace function public.registrar_campos(p_versao text, p_campos jsonb)
returns int
language plpgsql
security invoker
set search_path = ''
as $$
declare
    gravados int;
begin
    insert into public.anuncio_campos (anuncio_id, versao, tipo, procura, sexo, idade_min, idade_max, nacoes,
                                       cores, condicao, nomes, oficios, recompensa, valor, endereco, evidencias)
    select c.anuncio_id, p_versao, c.tipo, c.procura, c.sexo, c.idade_min, c.idade_max,
           case when jsonb_typeof(c.nacoes) = 'array'
                then array(select e from jsonb_array_elements_text(c.nacoes) with ordinality t(e, i) order by i)
                else '{}'::text[] end,
           case when jsonb_typeof(c.cores) = 'array'
                then array(select e from jsonb_array_elements_text(c.cores) with ordinality t(e, i) order by i)
                else '{}'::text[] end,
           c.condicao,
           case when jsonb_typeof(c.nomes) = 'array'
                then array(select e from jsonb_array_elements_text(c.nomes) with ordinality t(e, i) order by i)
                else '{}'::text[] end,
           case when jsonb_typeof(c.oficios) = 'array'
                then array(select e from jsonb_array_elements_text(c.oficios) with ordinality t(e, i) order by i)
                else '{}'::text[] end,
           c.recompensa, c.valor, c.endereco, c.evidencias
    from jsonb_to_recordset(p_campos) as c(
        anuncio_id bigint, tipo text, procura boolean, sexo text, idade_min smallint, idade_max smallint,
        nacoes jsonb, cores jsonb, condicao text, nomes jsonb, oficios jsonb, recompensa boolean,
        valor text, endereco text, evidencias jsonb)
    on conflict (anuncio_id, versao) do update set
        tipo = excluded.tipo, procura = excluded.procura, sexo = excluded.sexo,
        idade_min = excluded.idade_min, idade_max = excluded.idade_max, nacoes = excluded.nacoes,
        cores = excluded.cores, condicao = excluded.condicao, nomes = excluded.nomes,
        oficios = excluded.oficios, recompensa = excluded.recompensa, valor = excluded.valor,
        endereco = excluded.endereco, evidencias = excluded.evidencias, criado_em = now();
    get diagnostics gravados = row_count;
    return gravados;
end;
$$;

-- Anúncio + página + acervo + campos, para consultar no SQL Editor. LEFT JOIN: anúncio sem campos aparece
-- com as colunas c_* nulas; cada anúncio tem uma linha por versão de campos (filtre por c_versao).
-- Colunas dos campos com prefixo c_ (a versão do anúncio e a dos campos têm o mesmo nome).
-- periodo_legal é por ANO, sem olhar mês e dia: o ano da lei vai para o período seguinte (1831 abre o primeiro,
-- 1850 o segundo, 1871 o terceiro) e 1888 ainda é o terceiro.
create or replace view public.anuncios_completos with (security_invoker = true) as
    select a.id, a.versao, a.ordem, a.coluna, a.titulo, a.abertura, a.texto, a.confianca, a.largo,
           p.bib, p.pagina_fisica, p.ano, p.edicao, p.pagina, p.link, ac.nome as acervo,
           case when p.ano is null then null
                when p.ano < 1831 then 'antes de 1831'
                when p.ano < 1850 then '1831–1850 (Feijó → Eusébio)'
                when p.ano < 1871 then '1850–1871 (Eusébio → Ventre Livre)'
                when p.ano <= 1888 then '1871–1888 (Ventre Livre → Áurea)'
                else 'depois de 1888' end as periodo_legal,
           c.versao as c_versao, c.tipo as c_tipo, c.procura as c_procura, c.sexo as c_sexo,
           c.idade_min as c_idade_min, c.idade_max as c_idade_max, c.nacoes as c_nacoes, c.cores as c_cores,
           c.condicao as c_condicao, c.nomes as c_nomes, c.oficios as c_oficios,
           c.recompensa as c_recompensa, c.valor as c_valor, c.endereco as c_endereco,
           c.evidencias as c_evidencias, c.criado_em as c_criado_em
    from public.anuncios a
    join public.paginas p on p.id = a.pagina_id
    left join public.acervos ac on ac.bib = p.bib
    left join public.anuncio_campos c on c.anuncio_id = a.id;

alter table public.anuncio_campos enable row level security;

revoke all on table public.anuncio_campos from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on table public.anuncios_completos from anon, authenticated;
revoke all on function public.registrar_campos(text, jsonb) from public, anon, authenticated;

grant select, insert, update, delete on table public.anuncio_campos to service_role;
grant select on table public.anuncios_completos to service_role;
grant execute on function public.registrar_campos(text, jsonb) to service_role;


-- ============================================================================================
-- Relatório metodológico (hdb.relatorio). Nome sugerido da migração: `relatorio_coleta`. Idempotente.
-- ============================================================================================

-- Tudo o que o relatório precisa, agregado no banco (a API devolve no máximo 1000 linhas por chamada).
create or replace function public.relatorio_coleta()
returns jsonb
language sql
security invoker
stable
set search_path = ''
as $$
    select jsonb_build_object(
        'gerado_em', now(),

        -- por (termo, bib): total no servidor x ocorrências listadas, datas e páginas por status
        'buscas', coalesce((
            select jsonb_agg(b order by b.termo, b.bib)
            from (select o.termo, o.bib, a.nome as acervo,
                         max(o.total) as total_servidor, count(*) as listadas,
                         min(o.coletada_em) as primeira_coleta, max(o.coletada_em) as ultima_coleta,
                         (select coalesce(jsonb_object_agg(s.status, s.n), '{}'::jsonb)
                          from (select p.status, count(distinct p.id) as n
                                from public.ocorrencias o2
                                join public.paginas p on p.id = o2.pagina_id
                                where o2.termo = o.termo and o2.bib = o.bib
                                group by p.status) s) as paginas
                  from public.ocorrencias o
                  left join public.acervos a on a.bib = o.bib
                  group by o.termo, o.bib, a.nome) b), '[]'::jsonb),

        -- por pessoa (tentativas)
        'capturas', coalesce((
            select jsonb_agg(c order by c.quem)
            from (select coalesce(t.quem, '(sem nome)') as quem,
                         count(*) filter (where t.status = 'ok') as ok,
                         coalesce((select jsonb_object_agg(e.etapa, e.n)
                                   from (select t2.etapa, count(*) as n
                                         from public.tentativas t2
                                         where t2.status = 'erro'
                                           and coalesce(t2.quem, '(sem nome)') = coalesce(t.quem, '(sem nome)')
                                         group by t2.etapa) e), '{}'::jsonb) as erros,
                         coalesce(sum(t.captchas), 0) as captchas,
                         round(avg(t.segundos)::numeric, 1) as segundos_medios,
                         min(t.quando) as primeira, max(t.quando) as ultima
                  from public.tentativas t
                  group by t.quem) c), '[]'::jsonb),

        -- motores de OCR e confiança média da leitura atual por acervo
        'ocr', jsonb_build_object(
            'motores', coalesce((
                select jsonb_agg(m order by m.motor)
                from (select motor, count(*) as paginas, round(avg(confianca)::numeric, 1) as confianca_media
                      from public.textos_ocr group by motor) m), '[]'::jsonb),
            'acervos', coalesce((
                select jsonb_agg(x order by x.bib)
                from (select p.bib, a.nome as acervo, count(*) as paginas,
                             round(avg(t.confianca)::numeric, 1) as confianca_media
                      from public.textos_atuais t
                      join public.paginas p on p.id = t.pagina_id
                      left join public.acervos a on a.bib = p.bib
                      group by p.bib, a.nome) x), '[]'::jsonb)),

        'anuncios', coalesce((
            select jsonb_agg(v order by v.versao)
            from (select versao, count(*) as total, count(*) filter (where largo) as largos,
                         count(distinct pagina_id) as paginas
                  from public.anuncios group by versao) v), '[]'::jsonb),

        'campos', coalesce((
            select jsonb_agg(v order by v.versao)
            from (select c.versao, count(*) as total,
                         (select coalesce(jsonb_object_agg(coalesce(x.tipo, '(sem tipo)'), x.n), '{}'::jsonb)
                          from (select tipo, count(*) as n from public.anuncio_campos
                                where versao = c.versao group by tipo) x) as por_tipo,
                         (select coalesce(jsonb_object_agg(coalesce(x.sexo, '(sem sexo)'), x.n), '{}'::jsonb)
                          from (select sexo, count(*) as n from public.anuncio_campos
                                where versao = c.versao group by sexo) x) as por_sexo,
                         count(*) filter (where c.idade_min is not null) as com_idade,
                         count(*) filter (where cardinality(c.nomes) > 0) as com_nome,
                         count(*) filter (where c.recompensa) as com_recompensa,
                         (select coalesce(jsonb_agg(jsonb_build_object('nacao', y.nacao, 'n', y.n) order by y.n desc, y.nacao), '[]'::jsonb)
                          from (select nacao, count(*) as n
                                from public.anuncio_campos ac, unnest(ac.nacoes) as nacao
                                where ac.versao = c.versao
                                group by nacao order by count(*) desc, nacao limit 10) y) as nacoes
                  from public.anuncio_campos c group by c.versao) v), '[]'::jsonb),

        'panorama', jsonb_build_object(
            'periodos', coalesce((
                select jsonb_agg(p order by p.local, p.periodo)
                from (select local, periodo, count(*) as na_lista,
                             count(*) filter (where bib is not null) as com_bib,
                             count(*) filter (where erro is not null) as com_erro
                      from public.acervos_periodos group by local, periodo) p), '[]'::jsonb),
            'termos', coalesce((
                select jsonb_agg(t order by t.local, t.periodo, t.termo)
                from (select ap.local, ap.periodo, c.termo,
                             count(distinct c.bib) filter (where c.paginas > 0) as acervos,
                             coalesce(sum(c.paginas), 0) as paginas
                      from public.acervos_periodos ap
                      join public.contagens c on c.bib = ap.bib
                      group by ap.local, ap.periodo, c.termo) t), '[]'::jsonb))
    );
$$;

revoke all on function public.relatorio_coleta() from public, anon, authenticated;
grant execute on function public.relatorio_coleta() to service_role;


-- ============================================================================================
-- Corpus para a modelagem de tópicos (hdb.corpus). Nome sugerido da migração: `corpus_anuncios`. Idempotente.
-- ============================================================================================

-- Texto padronizado (minúsculas, grafia atual, sem números e palavras vazias) ao lado do original, por versão.
create table if not exists public.anuncio_corpus (
    anuncio_id  bigint not null references public.anuncios (id) on delete cascade,
    versao      text   not null,
    texto_padrao text,
    n_palavras  int,
    criado_em   timestamptz not null default now(),
    primary key (anuncio_id, versao)
);

-- Upsert em lote: p_linhas = [{anuncio_id, texto_padrao, n_palavras}, ...]. Devolve quantas linhas gravou.
create or replace function public.registrar_corpus(p_versao text, p_linhas jsonb)
returns int
language plpgsql
security invoker
set search_path = ''
as $$
declare
    gravados int;
begin
    insert into public.anuncio_corpus (anuncio_id, versao, texto_padrao, n_palavras)
    select l.anuncio_id, p_versao, l.texto_padrao, l.n_palavras
    from jsonb_to_recordset(p_linhas) as l(anuncio_id bigint, texto_padrao text, n_palavras int)
    on conflict (anuncio_id, versao) do update set
        texto_padrao = excluded.texto_padrao, n_palavras = excluded.n_palavras, criado_em = now();
    get diagnostics gravados = row_count;
    return gravados;
end;
$$;

alter table public.anuncio_corpus enable row level security;

revoke all on table public.anuncio_corpus from anon, authenticated;
revoke all on function public.registrar_corpus(text, jsonb) from public, anon, authenticated;

grant select, insert, update, delete on table public.anuncio_corpus to service_role;
grant execute on function public.registrar_corpus(text, jsonb) to service_role;


-- ============================================================================================
-- Modelagem de tópicos, LDA (hdb.topicos). Nome sugerido da migração: `topicos_lda`. Idempotente.
-- ============================================================================================

create table if not exists public.topico_modelos (
    versao       text primary key,
    versao_corpus text,
    n_topicos    int,
    semente      int,
    n_docs       int,
    n_vocab      int,
    perplexidade double precision,
    criado_em    timestamptz not null default now()
);

create table if not exists public.topico_palavras (
    versao  text not null references public.topico_modelos (versao) on delete cascade,
    topico  int  not null,
    palavra text not null,
    peso    double precision,
    primary key (versao, topico, palavra)
);

create table if not exists public.anuncio_topicos (
    anuncio_id bigint not null references public.anuncios (id) on delete cascade,
    versao     text   not null references public.topico_modelos (versao) on delete cascade,
    topico     int    not null,
    proporcao  real,
    primary key (anuncio_id, versao, topico)
);

-- Regravar a versão substitui tudo (apaga o modelo e, em cascata, palavras e misturas).
-- p_modelo = {versao, versao_corpus, n_topicos, semente, n_docs, n_vocab, perplexidade};
-- p_palavras = [{topico, palavra, peso}]; p_misturas = [{anuncio_id, topico, proporcao}]. Devolve quantas misturas gravou.
create or replace function public.registrar_topicos(p_modelo jsonb, p_palavras jsonb, p_misturas jsonb)
returns int
language plpgsql
security invoker
set search_path = ''
as $$
declare
    v text := p_modelo ->> 'versao';
    gravados int;
begin
    delete from public.topico_modelos where versao = v;

    insert into public.topico_modelos (versao, versao_corpus, n_topicos, semente, n_docs, n_vocab, perplexidade)
    values (v, p_modelo ->> 'versao_corpus', (p_modelo ->> 'n_topicos')::int, (p_modelo ->> 'semente')::int,
            (p_modelo ->> 'n_docs')::int, (p_modelo ->> 'n_vocab')::int, (p_modelo ->> 'perplexidade')::double precision)
    on conflict (versao) do update set
        versao_corpus = excluded.versao_corpus, n_topicos = excluded.n_topicos, semente = excluded.semente,
        n_docs = excluded.n_docs, n_vocab = excluded.n_vocab, perplexidade = excluded.perplexidade, criado_em = now();

    insert into public.topico_palavras (versao, topico, palavra, peso)
    select v, l.topico, l.palavra, l.peso
    from jsonb_to_recordset(p_palavras) as l(topico int, palavra text, peso double precision)
    on conflict (versao, topico, palavra) do update set peso = excluded.peso;

    insert into public.anuncio_topicos (anuncio_id, versao, topico, proporcao)
    select l.anuncio_id, v, l.topico, l.proporcao
    from jsonb_to_recordset(p_misturas) as l(anuncio_id bigint, topico int, proporcao real)
    on conflict (anuncio_id, versao, topico) do update set proporcao = excluded.proporcao;
    get diagnostics gravados = row_count;
    return gravados;
end;
$$;

-- Por modelo, período legal e tópico: proporção média e nº de anúncios.
create or replace view public.topicos_por_periodo with (security_invoker = true) as
    select t.versao, a.periodo_legal, t.topico,
           avg(t.proporcao) as proporcao_media, count(distinct t.anuncio_id) as n_anuncios
    from public.anuncio_topicos t
    join (select distinct on (id) id, periodo_legal from public.anuncios_completos
          order by id, c_criado_em desc nulls last) a on a.id = t.anuncio_id  -- uma linha por anúncio (várias versões de campos)
    group by t.versao, a.periodo_legal, t.topico;

alter table public.topico_modelos enable row level security;
alter table public.topico_palavras enable row level security;
alter table public.anuncio_topicos enable row level security;

revoke all on table public.topico_modelos, public.topico_palavras, public.anuncio_topicos, public.topicos_por_periodo
    from anon, authenticated;
revoke all on function public.registrar_topicos(jsonb, jsonb, jsonb) from public, anon, authenticated;

grant select, insert, update, delete on table public.topico_modelos, public.topico_palavras, public.anuncio_topicos
    to service_role;
grant select on table public.topicos_por_periodo to service_role;
grant execute on function public.registrar_topicos(jsonb, jsonb, jsonb) to service_role;


-- ============================================================================================
-- Palavras do OCR com posição, para segmentar anúncios sem a imagem. Nome sugerido da migração:
-- `palavras_ocr`. Idempotente.
-- ============================================================================================

create table if not exists public.paginas_palavras (
    pagina_id  bigint primary key references public.paginas (id) on delete cascade,
    largura    int,
    altura     int,
    palavras_gz text,  -- JSON compacto da lista de palavras (t,x,y,w,h,c,b,p,l) em zlib + base64
    n_palavras int,
    criado_em  timestamptz not null default now()
);

-- Upsert de uma página: regravar substitui as palavras.
create or replace function public.registrar_palavras(
    p_pagina_id bigint, p_largura int, p_altura int, p_palavras_gz text, p_n int)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    insert into public.paginas_palavras (pagina_id, largura, altura, palavras_gz, n_palavras)
    values (p_pagina_id, p_largura, p_altura, p_palavras_gz, p_n)
    on conflict (pagina_id) do update set
        largura = excluded.largura, altura = excluded.altura, palavras_gz = excluded.palavras_gz,
        n_palavras = excluded.n_palavras, criado_em = now();
end;
$$;

alter table public.paginas_palavras enable row level security;

revoke all on table public.paginas_palavras from anon, authenticated;
revoke all on function public.registrar_palavras(bigint, int, int, text, int) from public, anon, authenticated;

grant select, insert, update, delete on table public.paginas_palavras to service_role;
grant execute on function public.registrar_palavras(bigint, int, int, text, int) to service_role;


-- ============================================================================================
-- Reserva equilibrada por ano: a cada rodada sai uma página de cada ano ainda disponível (a 1ª
-- sorteada de cada ano vem antes da 2ª de qualquer ano). Função nova, sem mexer em reservar_paginas.
-- Nome sugerido da migração: `reservar_equilibradas`. Idempotente.
-- ============================================================================================

create or replace function public.reservar_paginas_equilibradas(
    p_quem text,
    p_limite int,
    p_bib text default null,
    p_termo text default null,
    p_max_tentativas int default 3,
    p_expira_min int default 30,
    p_excluir bigint[] default '{}'
)
returns table (id bigint, bib text, pagina_fisica int, ano smallint, edicao text, pagina text, link text)
language sql
security invoker
set search_path = ''
as $$
    with elegiveis as (
        select p.id,
               row_number() over (partition by p.ano order by random()) as rodada
        from public.paginas p
        where (p.status = 'pendente'
               or (p.status = 'erro' and p.etapa_erro = 'captura' and p.tentativas < p_max_tentativas)
               or (p.status = 'reservada'
                   and p.reservada_em < now() - make_interval(mins => p_expira_min)))
          and not (p.id = any(p_excluir))
          and (p_bib is null or p.bib = p_bib)
          and (p_termo is null or exists (
                select 1 from public.ocorrencias o
                where o.pagina_id = p.id and o.termo = p_termo))
    ),
    candidatas as (
        select e.id from elegiveis e
        order by e.rodada, random()
        limit p_limite
    ),
    -- A condição de status e p_excluir se repete de propósito: em READ COMMITTED, quem espera o lock
    -- (skip locked só pula o que está travado agora) enxerga a linha já commitada por outra reserva, e o
    -- for update não reavalia o filtro do CTE `elegiveis`. Sem repetir, a página seria reservada duas vezes.
    travadas as (
        select p.id from public.paginas p
        where p.id in (select id from candidatas)
          and (p.status = 'pendente'
               or (p.status = 'erro' and p.etapa_erro = 'captura' and p.tentativas < p_max_tentativas)
               or (p.status = 'reservada'
                   and p.reservada_em < now() - make_interval(mins => p_expira_min)))
          and not (p.id = any(p_excluir))
        for update of p skip locked
    )
    update public.paginas pg
    set status = 'reservada', reservada_por = p_quem, reservada_em = now(), atualizado_em = now()
    from travadas t
    where pg.id = t.id
    returning pg.id, pg.bib, pg.pagina_fisica, pg.ano, pg.edicao, pg.pagina, pg.link;
$$;

revoke all on function public.reservar_paginas_equilibradas(text, int, text, text, int, int, bigint[])
    from public, anon, authenticated;
grant execute on function public.reservar_paginas_equilibradas(text, int, text, text, int, int, bigint[]) to service_role;
