import os
import sys
from pathlib import Path

import httpx
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from triagem.config import Config  # noqa: E402

import mvp_simulado  # noqa: E402

# Se o repositório do MVP estiver ao lado (ou em MVP_DIR), os testes rodam contra o MVP REAL.
MVP_DIR = Path(os.getenv("MVP_DIR", RAIZ.parent / "calcada-livre" / "mvp"))
USA_MVP_REAL = (MVP_DIR / "app" / "main.py").exists()
if USA_MVP_REAL:
    sys.path.insert(0, str(MVP_DIR))
    os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(__file__).parent / "_teste_mvp.db")
    os.environ["ROBO_API_KEY"] = mvp_simulado.CHAVE


def pytest_report_header(config):
    return f"MVP usado nos testes: {'REAL em ' + str(MVP_DIR) if USA_MVP_REAL else 'simulado (tests/mvp_simulado.py)'}"


@pytest.fixture()
def mvp():
    if not USA_MVP_REAL:
        yield mvp_simulado.criar_cliente()
        return
    from fastapi.testclient import TestClient
    from app.db import Base, engine
    from app.main import app

    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(engine)


@pytest.fixture()
def cfg(tmp_path):
    return Config(
        api_url="http://testserver",
        api_key=mvp_simulado.CHAVE,
        pasta_entrada=tmp_path / "entrada",
        pasta_saida=tmp_path / "saida",
        pasta_logs=tmp_path / "logs",
        arquivo_pois=RAIZ / "data" / "pontos_interesse.csv",
        alerta_webhook_url="",
    )


def clima(prob: int):
    """Open-Meteo simulado com a probabilidade de chuva desejada."""
    def responder(req):
        return httpx.Response(200, json={"hourly": {"precipitation_probability": [0, prob, 10]}})
    return httpx.Client(transport=httpx.MockTransport(responder))


@pytest.fixture()
def sem_chuva():
    return clima(5)


@pytest.fixture()
def com_chuva():
    return clima(90)
