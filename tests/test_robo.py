"""Testes de ponta a ponta do robô contra o MVP real (cenários de sucesso, decisão e falha)."""
import json

import httpx

from triagem import robo

LIVRE = {"tipo": "buraco", "latitude": -23.6100, "longitude": -46.6950, "origem": "app"}  # longe de POI
HOSPITAL = {"tipo": "degrau", "latitude": -23.5573, "longitude": -46.6697, "origem": "carrinho"}  # Hospital das Clínicas


def criar(mvp, **campos):
    r = mvp.post("/api/ocorrencias", json=campos)
    assert r.status_code == 201
    return r.json()


def eventos(cfg):
    linhas = []
    for arq in cfg.pasta_logs.glob("*.jsonl"):
        linhas += [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines()]
    return linhas


# ---------- SUCESSO ----------

def test_sucesso_encaminha_e_gera_pacote(mvp, cfg, sem_chuva):
    oc = criar(mvp, **LIVRE)
    codigo, res = robo.executar(cfg, http_api=mvp, http_externo=sem_chuva, eco=False)

    assert codigo == robo.OK
    assert res["encaminhadas"] == 1
    salvo = mvp.get(f"/api/ocorrencias/{oc['id']}").json()
    assert salvo["status"] == "encaminhada"
    assert salvo["prioridade"] == "media"
    assert salvo["protocolo"].startswith("CL-")
    assert salvo["subprefeitura"]
    csvs = list(cfg.pasta_saida.rglob("*.csv"))
    emls = list(cfg.pasta_saida.rglob("*.eml"))
    assert len(csvs) == 1 and len(emls) == 1
    assert salvo["protocolo"] in csvs[0].read_text(encoding="utf-8")
    assert "[SIMULADO]" in emls[0].read_text(encoding="utf-8")
    assert eventos(cfg)[-1]["evento"] == "execucao_concluida"


def test_idempotente_segunda_execucao_nao_reprocessa(mvp, cfg, sem_chuva):
    criar(mvp, **LIVRE)
    robo.executar(cfg, http_api=mvp, http_externo=sem_chuva, eco=False)
    _, res = robo.executar(cfg, http_api=mvp, http_externo=sem_chuva, eco=False)
    assert res["lidas"] == 0


# ---------- DECISÃO ----------

def test_decisao_perto_de_hospital_vira_alta_e_alerta(mvp, cfg, sem_chuva):
    oc = criar(mvp, **HOSPITAL)
    _, res = robo.executar(cfg, http_api=mvp, http_externo=sem_chuva, eco=False)
    salvo = mvp.get(f"/api/ocorrencias/{oc['id']}").json()
    assert salvo["prioridade"] == "alta"
    assert "perto_de_hospital" in salvo["motivo"]
    assert res["alta"] == 1
    assert any(e["evento"] == "alerta_prioridade_alta" for e in eventos(cfg))


def test_decisao_chuva_sobe_um_nivel(mvp, cfg, com_chuva):
    oc = criar(mvp, **{**LIVRE, "tipo": "trecho_escuro"})
    robo.executar(cfg, http_api=mvp, http_externo=com_chuva, eco=False)
    salvo = mvp.get(f"/api/ocorrencias/{oc['id']}").json()
    assert salvo["prioridade"] == "media"
    assert "chuva_prevista" in salvo["motivo"]


def test_decisao_quarentena_e_duplicada(mvp, cfg, sem_chuva):
    original = criar(mvp, **LIVRE)
    repetida = criar(mvp, **{**LIVRE, "latitude": LIVRE["latitude"] + 0.0001, "origem": "carrinho"})
    fora = criar(mvp, tipo="buraco", latitude=-22.90, longitude=-43.20, origem="app")  # Rio de Janeiro
    sem_foto = criar(mvp, tipo="obstaculo", latitude=-23.60, longitude=-46.70, origem="visao", confianca=0.9)

    _, res = robo.executar(cfg, http_api=mvp, http_externo=sem_chuva, eco=False)

    assert res == {**res, "lidas": 4, "encaminhadas": 1, "duplicadas": 1, "quarentena": 2}
    rep = mvp.get(f"/api/ocorrencias/{repetida['id']}").json()
    assert rep["status"] == "duplicada" and rep["duplicada_de"] == original["id"]
    assert mvp.get(f"/api/ocorrencias/{fora['id']}").json()["motivo"] == "fora_do_municipio"
    assert mvp.get(f"/api/ocorrencias/{sem_foto['id']}").json()["motivo"] == "visao_sem_foto"


def test_decisao_remove_dado_pessoal_e_log_nao_vaza(mvp, cfg, sem_chuva):
    oc = criar(mvp, **LIVRE, descricao="Buraco grande. Meu zap (11) 98765-4321")
    robo.executar(cfg, http_api=mvp, http_externo=sem_chuva, eco=False)
    salvo = mvp.get(f"/api/ocorrencias/{oc['id']}").json()
    assert "98765" not in salvo["descricao"]
    bruto = "".join(a.read_text(encoding="utf-8") for a in cfg.pasta_logs.glob("*.jsonl"))
    assert "98765" not in bruto and "-46.695" not in bruto  # nem telefone nem coordenada no log


def test_lote_csv_valido_e_invalido(mvp, cfg, sem_chuva):
    cfg.pasta_entrada.mkdir(parents=True)
    (cfg.pasta_entrada / "carrinho_offline.csv").write_text(
        "tipo,latitude,longitude,origem\nobstaculo,-23.61,-46.70,carrinho\nburaco,abc,-46.7,carrinho\n",
        encoding="utf-8")
    (cfg.pasta_entrada / "planilha_quebrada.csv").write_text("coluna_errada\n1\n", encoding="utf-8")

    _, res = robo.executar(cfg, http_api=mvp, http_externo=sem_chuva, eco=False)

    assert res["lote"] == {"arquivos": 2, "rejeitados": 1, "linhas_importadas": 1, "linhas_ignoradas": 1}
    assert (cfg.pasta_entrada / "rejeitados" / "planilha_quebrada.csv").exists()
    assert (cfg.pasta_entrada / "processados" / "carrinho_offline.csv").exists()
    assert res["encaminhadas"] == 1


# ---------- FALHA ----------

def test_falha_api_fora_do_ar_tenta_com_espera_crescente(cfg):
    def recusar(req):
        raise httpx.ConnectError("Connection refused", request=req)

    esperas = []
    fora = httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(recusar))
    codigo, _ = robo.executar(cfg, http_api=fora, dormir=esperas.append, eco=False)

    assert codigo == robo.API_FORA
    assert esperas == [2, 4, 8]  # backoff exponencial, 4 tentativas
    ev = eventos(cfg)
    assert sum(e["evento"] == "api_tentativa_falhou" for e in ev) == 4
    assert ev[-1]["evento"] == "api_indisponivel" and ev[-1]["nivel"] == "ERRO"


def test_falha_api_cai_no_meio_preserva_o_restante(mvp, cfg, sem_chuva):
    a = criar(mvp, **LIVRE)
    b = criar(mvp, **{**LIVRE, "latitude": -23.62})
    chamadas = {"patch": 0}

    def instavel(req):
        if req.method == "PATCH":
            chamadas["patch"] += 1
            if chamadas["patch"] > 1:
                return httpx.Response(503)
        r = mvp.request(req.method, str(req.url), content=req.content, headers=dict(req.headers))
        return httpx.Response(r.status_code, content=r.content, headers=r.headers)

    cli = httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(instavel))
    codigo, res = robo.executar(cfg, http_api=cli, http_externo=sem_chuva, dormir=lambda s: None, eco=False)

    assert codigo == robo.COM_ERROS
    assert res["encaminhadas"] == 1 and res["erros"] == 1
    estados = {mvp.get(f"/api/ocorrencias/{x['id']}").json()["status"] for x in (a, b)}
    assert estados == {"encaminhada", "nova"}  # a que falhou volta na próxima execução


def test_falha_clima_fora_do_ar_degrada_sem_parar(mvp, cfg):
    def cair(req):
        raise httpx.ConnectTimeout("timeout", request=req)

    criar(mvp, **LIVRE)
    externo = httpx.Client(transport=httpx.MockTransport(cair))
    codigo, res = robo.executar(cfg, http_api=mvp, http_externo=externo, eco=False)
    assert codigo == robo.OK and res["encaminhadas"] == 1
    assert any(e["evento"] == "clima_indisponivel" and e["nivel"] == "AVISO" for e in eventos(cfg))


def test_falha_arquivo_de_pois_ausente(mvp, cfg, sem_chuva, tmp_path):
    cfg.arquivo_pois = tmp_path / "nao_existe.csv"
    criar(mvp, **HOSPITAL)
    codigo, res = robo.executar(cfg, http_api=mvp, http_externo=sem_chuva, eco=False)
    assert codigo == robo.OK and res["alta"] == 0
    assert any(e["evento"] == "pois_indisponiveis" for e in eventos(cfg))


def test_falha_sem_chave_nao_executa(cfg):
    cfg.api_key = ""
    codigo, _ = robo.executar(cfg, eco=False)
    assert codigo == robo.COM_ERROS
