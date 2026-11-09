"""Configuração do robô, toda por variável de ambiente (nada de segredo no código)."""
import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]  # pasta rpa/


@dataclass
class Config:
    api_url: str = field(default_factory=lambda: os.getenv("API_URL", "http://localhost:8000").rstrip("/"))
    api_key: str = field(default_factory=lambda: os.getenv("ROBO_API_KEY", ""))
    # Pastas de trabalho
    pasta_entrada: Path = field(default_factory=lambda: Path(os.getenv("PASTA_ENTRADA", RAIZ / "entrada")))
    pasta_saida: Path = field(default_factory=lambda: Path(os.getenv("PASTA_SAIDA", RAIZ / "saida")))
    pasta_logs: Path = field(default_factory=lambda: Path(os.getenv("PASTA_LOGS", RAIZ / "logs")))
    arquivo_pois: Path = field(default_factory=lambda: Path(os.getenv("ARQUIVO_POIS", RAIZ / "data" / "pontos_interesse.csv")))
    # Resiliência
    tentativas: int = int(os.getenv("TENTATIVAS", "4"))
    espera_inicial_s: float = float(os.getenv("ESPERA_INICIAL_S", "2"))
    timeout_s: float = float(os.getenv("TIMEOUT_S", "10"))
    # Regras de negócio
    raio_duplicada_m: float = float(os.getenv("RAIO_DUPLICADA_M", "20"))
    janela_duplicada_dias: int = int(os.getenv("JANELA_DUPLICADA_DIAS", "7"))
    raio_poi_m: float = float(os.getenv("RAIO_POI_M", "150"))
    limiar_chuva_prob: int = int(os.getenv("LIMIAR_CHUVA_PROB", "60"))
    confianca_minima_visao: float = float(os.getenv("CONFIANCA_MINIMA_VISAO", "0.5"))
    # Alerta (opcional): URL de webhook (Discord, Slack, Teams). Vazio = alerta só no log e em arquivo.
    alerta_webhook_url: str = field(default_factory=lambda: os.getenv("ALERTA_WEBHOOK_URL", ""))
    # Execução contínua
    intervalo_min: int = int(os.getenv("INTERVALO_MIN", "15"))
