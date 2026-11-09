"""Log de auditoria em JSON Lines: uma linha por evento, com data/hora em UTC.

Regra de LGPD: o log nunca recebe descrição livre, foto nem coordenada exata.
Só ids de ocorrência, contagens, códigos de motivo e mensagens de erro técnicas.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CAMPOS_PROIBIDOS = {"descricao", "foto_url", "latitude", "longitude", "email", "telefone", "cpf", "nome"}


class LogAuditoria:
    def __init__(self, pasta: Path, execucao_id: str, eco: bool = True):
        pasta.mkdir(parents=True, exist_ok=True)
        dia = datetime.now(timezone.utc).strftime("%Y%m%d")
        self.arquivo = pasta / f"robo-triagem-{dia}.jsonl"
        self.execucao_id = execucao_id
        self.eco = eco
        self.eventos: list[dict] = []

    def _gravar(self, nivel: str, evento: str, **dados) -> dict:
        vazou = CAMPOS_PROIBIDOS & dados.keys()
        if vazou:  # defesa extra: um campo pessoal nunca chega ao disco
            raise ValueError(f"Campo sensível no log: {sorted(vazou)}")
        linha = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "nivel": nivel,
            "execucao": self.execucao_id,
            "evento": evento,
            **dados,
        }
        with self.arquivo.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        self.eventos.append(linha)
        if self.eco:
            print(json.dumps(linha, ensure_ascii=False), file=sys.stderr)
        return linha

    def info(self, evento: str, **dados):
        return self._gravar("INFO", evento, **dados)

    def aviso(self, evento: str, **dados):
        return self._gravar("AVISO", evento, **dados)

    def erro(self, evento: str, **dados):
        return self._gravar("ERRO", evento, **dados)
