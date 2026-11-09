"""Pacote de encaminhamento por subprefeitura e alerta de prioridade alta.

IMPORTANTE: o encaminhamento é SIMULADO. Nada é enviado ao SP156 ou à prefeitura.
O robô gera um CSV por subprefeitura e um e-mail em arquivo .eml, prontos para
quem for operar o serviço de verdade.
"""
import csv
import unicodedata
from collections import defaultdict
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import httpx

from .logs import LogAuditoria

COLUNAS = ["protocolo", "tipo", "prioridade", "razoes", "subprefeitura", "latitude", "longitude", "origem", "criada_em"]


def _arquivo_seguro(nome: str) -> str:
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in nome).strip("_").lower()


def gerar_pacotes(encaminhadas: list[dict], pasta: Path, quando: datetime, log: LogAuditoria) -> list[Path]:
    if not encaminhadas:
        return []
    destino = pasta / f"{quando:%Y%m%d-%H%M%S}"
    destino.mkdir(parents=True, exist_ok=True)
    grupos: dict[str, list[dict]] = defaultdict(list)
    for oc in encaminhadas:
        grupos[oc["subprefeitura"]].append(oc)

    gerados = []
    for sub, itens in sorted(grupos.items()):
        itens.sort(key=lambda o: ["alta", "media", "baixa"].index(o["prioridade"]))
        base = _arquivo_seguro(sub)
        arq_csv = destino / f"{base}.csv"
        with arq_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
            w.writeheader()
            w.writerows(itens)

        email = EmailMessage()
        email["From"] = "robo-triagem@calcadalivre.example"
        email["To"] = f"zeladoria.{base}@prefeitura.example"
        email["Subject"] = f"[SIMULADO] Calçada Livre: {len(itens)} barreira(s) para a Subprefeitura {sub}"
        altas = sum(1 for o in itens if o["prioridade"] == "alta")
        email.set_content(
            f"Mensagem simulada, gerada automaticamente pelo robô de triagem da Calçada Livre.\n\n"
            f"Subprefeitura: {sub}\nOcorrências: {len(itens)} ({altas} de prioridade alta)\n\n"
            + "\n".join(f"- {o['protocolo']} · {o['tipo']} · prioridade {o['prioridade']}" for o in itens)
            + "\n\nO detalhamento está no CSV anexo.\n"
        )
        email.add_attachment(arq_csv.read_bytes(), maintype="text", subtype="csv", filename=arq_csv.name)
        arq_eml = destino / f"{base}.eml"
        arq_eml.write_bytes(bytes(email))
        gerados += [arq_csv, arq_eml]
        log.info("pacote_gerado", subprefeitura=sub, ocorrencias=len(itens), altas=altas, arquivo=arq_csv.name)
    return gerados


def alertar(altas: list[dict], webhook_url: str, log: LogAuditoria, http: httpx.Client | None = None) -> None:
    if not altas:
        return
    texto = f"Calçada Livre: {len(altas)} barreira(s) de prioridade ALTA: " + ", ".join(
        f"{o['protocolo']} ({o['tipo']}, {o['subprefeitura']})" for o in altas
    )
    if not webhook_url:
        log.aviso("alerta_prioridade_alta", quantidade=len(altas), protocolos=[o["protocolo"] for o in altas],
                  canal="log")
        return
    try:
        (http or httpx.Client(timeout=10)).post(webhook_url, json={"content": texto, "text": texto}).raise_for_status()
        log.info("alerta_prioridade_alta", quantidade=len(altas), protocolos=[o["protocolo"] for o in altas],
                 canal="webhook")
    except httpx.HTTPError as e:
        log.erro("alerta_falhou", quantidade=len(altas), erro=type(e).__name__)
