"""Cliente da API do MVP com tentativas e espera crescente (backoff exponencial)."""
import time
from datetime import datetime

import httpx

from .config import Config
from .logs import LogAuditoria


class ApiIndisponivel(Exception):
    """A API não respondeu depois de todas as tentativas."""


class ClienteMVP:
    def __init__(self, cfg: Config, log: LogAuditoria, http: httpx.Client | None = None, dormir=time.sleep):
        self.cfg = cfg
        self.log = log
        self.http = http or httpx.Client(base_url=cfg.api_url, timeout=cfg.timeout_s)
        self.dormir = dormir

    def _chamar(self, metodo: str, caminho: str, **kwargs) -> httpx.Response:
        espera = self.cfg.espera_inicial_s
        ultimo_erro = ""
        for tentativa in range(1, self.cfg.tentativas + 1):
            try:
                r = self.http.request(metodo, caminho, **kwargs)
                if r.status_code >= 500:
                    raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
                r.raise_for_status()  # 4xx não é repetido: é erro de dado, não de disponibilidade
                return r
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500:
                    raise
                ultimo_erro = f"{type(e).__name__}: {e}"
                self.log.aviso("api_tentativa_falhou", metodo=metodo, caminho=caminho.split("?")[0],
                               tentativa=tentativa, de=self.cfg.tentativas, erro=ultimo_erro[:200])
                if tentativa < self.cfg.tentativas:
                    self.dormir(espera)
                    espera *= 2
        raise ApiIndisponivel(ultimo_erro)

    def listar(self, status: str | None = None, desde: datetime | None = None) -> list[dict]:
        params = {"limite": 2000}
        if status:
            params["status"] = status
        if desde:
            params["desde"] = desde.isoformat()
        return self._chamar("GET", "/api/ocorrencias", params=params).json()

    def criar(self, ocorrencia: dict) -> dict:
        return self._chamar("POST", "/api/ocorrencias", json=ocorrencia).json()

    def atualizar(self, oc_id: str, campos: dict) -> dict:
        return self._chamar("PATCH", f"/api/ocorrencias/{oc_id}", json=campos,
                            headers={"X-API-Key": self.cfg.api_key}).json()
