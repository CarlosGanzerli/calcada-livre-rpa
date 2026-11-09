"""Testes unitários das regras de negócio."""
from datetime import datetime

from triagem import regras
from triagem.regras import PontoInteresse

BASE = {"id": "a1", "tipo": "buraco", "latitude": -23.5700, "longitude": -46.6900, "origem": "app"}


def test_valida_ocorrencia_normal():
    assert regras.validar(BASE) == (True, None)


def test_fora_do_municipio():
    assert regras.validar({**BASE, "latitude": -22.9, "longitude": -43.2}) == (False, "fora_do_municipio")


def test_tipo_invalido_e_coordenada_ausente():
    assert regras.validar({**BASE, "tipo": "ovni"})[1] == "tipo_invalido"
    assert regras.validar({**BASE, "latitude": None})[1] == "coordenada_ausente"


def test_visao_exige_foto_e_confianca():
    visao = {**BASE, "origem": "visao"}
    assert regras.validar(visao)[1] == "visao_sem_foto"
    assert regras.validar({**visao, "foto_url": "http://x/f.jpg", "confianca": 0.3})[1] == "visao_baixa_confianca"
    assert regras.validar({**visao, "foto_url": "http://x/f.jpg", "confianca": 0.8}) == (True, None)


def test_duplicada_ate_20m_e_mesmo_tipo():
    perto = {**BASE, "id": "b2", "latitude": BASE["latitude"] + 0.0001}  # ~11 m
    longe = {**BASE, "id": "c3", "latitude": BASE["latitude"] + 0.001}  # ~111 m
    outro_tipo = {**perto, "id": "d4", "tipo": "degrau"}
    assert regras.achar_duplicada(perto, [BASE], 20)["id"] == "a1"
    assert regras.achar_duplicada(longe, [BASE], 20) is None
    assert regras.achar_duplicada(outro_tipo, [BASE], 20) is None


def test_prioridade():
    hospital = PontoInteresse("H", "hospital", BASE["latitude"], BASE["longitude"])
    assert regras.decidir_prioridade(BASE, None, False)[0] == "media"
    assert regras.decidir_prioridade(BASE, hospital, False) == ("alta", ["base_buraco=media", "perto_de_hospital"])
    assert regras.decidir_prioridade({**BASE, "tipo": "trecho_escuro"}, None, True)[0] == "media"
    assert regras.decidir_prioridade(BASE, None, True)[0] == "alta"


def test_subprefeitura_e_protocolo():
    assert regras.subprefeitura(-23.5505, -46.6333) == "Sé"
    assert regras.subprefeitura(-23.8300, -46.7300) == "Parelheiros"
    p = regras.gerar_protocolo({"id": "1234abcd-0000"}, datetime(2026, 11, 9))
    assert p == "CL-20261109-1234ABCD"


def test_mascara_dados_pessoais():
    texto, mudou = regras.mascarar_dados_pessoais(
        "Buraco enorme, me liga (11) 98765-4321 ou joao@email.com, CPF 123.456.789-09")
    assert mudou
    assert "98765" not in texto and "joao@" not in texto and "123.456" not in texto
    assert regras.mascarar_dados_pessoais("Buraco na esquina") == ("Buraco na esquina", False)
