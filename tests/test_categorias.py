from hdb.categorias import DEFEITOS, MARCAS_CORPO, QUALIDADES, categorias, contar, ocorrencias


def test_qualidades_sem_vicios_e_fiel():
    c = categorias("VENDE-SE huma preta, de 20 annos, sem vícios, muito fiel; na rua do Ouvidor n. 5.")
    assert set(c["qualidades"]) == {"sem vicios", "fiel"}
    assert c["defeitos"] == []  # "sem vícios" não é defeito


def test_defeito_vicios_e_doente_sem_negacao():
    c = categorias("Vende-se um preto que tem vícios e é doente do peito.")
    assert c["defeitos"] == ["vicios", "doente"]
    assert c["qualidades"] == []


def test_negacao_sem_defeito_e_nao_tem():
    assert contar("sem vicio nem defeito algum", DEFEITOS) == []
    assert categorias("sem defeito")["qualidades"] == ["sem vicios"]  # variantes ficam no mesmo grupo
    assert contar("affiança-se não ter vícios nem molestias", DEFEITOS) == []
    assert contar("tem molestias antigas", DEFEITOS) == ["molestias"]
    assert contar("livre de achaques e doente", DEFEITOS) == ["doente"]


def test_negacao_so_olha_12_caracteres_antes():
    assert contar("sem barba e sem dentes na frente, muito cheio de vicios", DEFEITOS) == ["vicios"]


def test_marcas_no_corpo():
    c = categorias("Fugio hum preto com uma cicatriz na barriga, falto de dentes, signal de ferida no braço.")
    assert c["marcas"] == ["cicatriz", "falta de dentes", "signal", "ferida"]
    assert c["defeitos"] == []


def test_erro_de_ocr_de_uma_letra_em_palavra_longa():
    assert contar("com huma cicatrir no peito", MARCAS_CORPO) == ["cicatriz"]  # 8 letras: tolera
    assert contar("preta intelligenta e carinhosa", QUALIDADES) == ["intelligente", "carinhosa"]


def test_palavra_curta_nao_tolera_erro():
    assert contar("preta fial", QUALIDADES) == []       # "fiel" tem 4 letras
    assert contar("preta sadea", QUALIDADES) == []      # "sadia" tem 5
    assert contar("dois erros: cicatrxx", MARCAS_CORPO) == []


def test_plural_automatico_e_sem_falso_positivo_de_dentes():
    assert contar("tem bexigas e cicatrizes", MARCAS_CORPO) == ["bexigas", "cicatriz"]
    assert contar("sem dentes", DEFEITOS) == []  # "doentes" (plural) não pode casar com "dentes"
    assert contar("sabe tratar doentes", DEFEITOS) == ["doente"]


def test_marca_sozinha_e_verbo_de_costura():
    assert contar("cose, marca, engomma e cozinha", MARCAS_CORPO) == []
    assert contar("tem marca no peito esquerdo", MARCAS_CORPO) == ["marca"]


def test_texto_vazio_e_posicoes():
    assert categorias(None) == {"qualidades": [], "defeitos": [], "marcas": []}
    texto = "Preta FIEL"
    (canonica, i, j), = ocorrencias(texto, QUALIDADES)
    assert (canonica, texto[i:j]) == ("fiel", "FIEL")
