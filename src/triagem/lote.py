"""Importação de lotes em CSV deixados na pasta entrada/.

Exemplo de uso: o carrinho sem Wi-Fi grava as leituras num cartão e exporta um CSV;
a equipe de campo exporta uma planilha. O robô valida o arquivo inteiro antes de
importar: arquivo vazio, sem as colunas obrigatórias ou ilegível vai para
entrada/rejeitados/ e o motivo fica no log.
"""
import csv
import shutil
from pathlib import Path

from .cliente_api import ClienteMVP
from .logs import LogAuditoria

COLUNAS_OBRIGATORIAS = {"tipo", "latitude", "longitude", "origem"}
ORIGENS = {"app", "carrinho", "visao"}


def _mover(arquivo: Path, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    shutil.move(str(arquivo), destino / arquivo.name)


def importar_lotes(pasta: Path, api: ClienteMVP, log: LogAuditoria) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    totais = {"arquivos": 0, "rejeitados": 0, "linhas_importadas": 0, "linhas_ignoradas": 0}
    arquivos = sorted(pasta.glob("*.csv"))
    if not arquivos:
        log.info("lote_sem_arquivos", pasta=pasta.name)
        return totais

    for arq in arquivos:  # repetição sobre a coleção de arquivos
        totais["arquivos"] += 1
        try:
            with arq.open(encoding="utf-8") as f:
                leitor = csv.DictReader(f)
                faltando = COLUNAS_OBRIGATORIAS - set(leitor.fieldnames or [])
                linhas = list(leitor)
        except (UnicodeDecodeError, csv.Error) as e:
            faltando, linhas = {"arquivo_ilegivel"}, []
            log.erro("lote_ilegivel", arquivo=arq.name, erro=type(e).__name__)
        if faltando or not linhas:
            motivo = "vazio" if not faltando else "colunas_faltando:" + ",".join(sorted(faltando))
            log.erro("lote_rejeitado", arquivo=arq.name, motivo=motivo)
            _mover(arq, pasta / "rejeitados")
            totais["rejeitados"] += 1
            continue

        importadas = ignoradas = 0
        for n, linha in enumerate(linhas, start=2):
            try:
                corpo = {
                    "tipo": linha["tipo"].strip(),
                    "latitude": float(linha["latitude"]),
                    "longitude": float(linha["longitude"]),
                    "origem": linha["origem"].strip(),
                    "descricao": (linha.get("descricao") or "").strip() or None,
                    "foto_url": (linha.get("foto_url") or "").strip() or None,
                    "confianca": float(linha["confianca"]) if linha.get("confianca") else None,
                }
                if corpo["origem"] not in ORIGENS:
                    raise ValueError("origem")
            except (ValueError, KeyError, AttributeError):
                ignoradas += 1
                log.aviso("lote_linha_invalida", arquivo=arq.name, linha=n)
                continue
            api.criar(corpo)
            importadas += 1

        log.info("lote_importado", arquivo=arq.name, importadas=importadas, ignoradas=ignoradas)
        totais["linhas_importadas"] += importadas
        totais["linhas_ignoradas"] += ignoradas
        _mover(arq, pasta / "processados")
    return totais
