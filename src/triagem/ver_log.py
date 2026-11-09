"""Mostra o log de auditoria (JSON Lines) em formato legível no terminal.

Uso:
  python -m triagem 2>&1 | python -m triagem.ver_log
  python -m triagem.ver_log < logs/robo-triagem-20261109.jsonl
"""
import json
import sys
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
    FUSO = ZoneInfo("America/Sao_Paulo")
except Exception:  # sem base de fusos (ex.: Windows sem tzdata): mostra em UTC
    FUSO = None

ESCONDER = {"ts", "nivel", "execucao", "evento"}


def formatar(linha: str) -> str:
    try:
        e = json.loads(linha)
    except json.JSONDecodeError:
        return linha.rstrip()
    ts = datetime.fromisoformat(e["ts"])
    hora = (ts.astimezone(FUSO) if FUSO else ts).strftime("%H:%M:%S")
    campos = []
    for k, v in e.items():
        if k in ESCONDER:
            continue
        if k in ("id", "duplicada_de") and isinstance(v, str):
            v = v[:8]
        if isinstance(v, list):
            v = ",".join(map(str, v))
        if isinstance(v, dict):
            v = " ".join(f"{a}={b}" for a, b in v.items())
        campos.append(f"{k}={v}")
    return f"{hora} {e['nivel']:<5} {e['evento']}  " + " ".join(campos)


def main() -> None:
    try:
        for linha in sys.stdin:
            if linha.strip():
                print(formatar(linha), flush=True)
    except BrokenPipeError:  # saída cortada (ex.: | head): encerra sem erro
        pass


if __name__ == "__main__":
    main()
