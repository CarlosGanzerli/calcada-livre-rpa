"""Previsão de chuva pelo Open-Meteo (gratuito, sem chave).

Se o serviço falhar, o robô continua sem a regra de chuva e registra um AVISO:
degrada com transparência, nunca falha em silêncio.
"""
import httpx

from .logs import LogAuditoria

URL = "https://api.open-meteo.com/v1/forecast"


def chuva_prevista_24h(log: LogAuditoria, limiar_prob: int, http: httpx.Client | None = None,
                       lat: float = -23.55, lon: float = -46.63) -> bool:
    http = http or httpx.Client(timeout=10)
    try:
        r = http.get(URL, params={
            "latitude": lat, "longitude": lon,
            "hourly": "precipitation_probability", "forecast_days": 1, "timezone": "America/Sao_Paulo",
        })
        r.raise_for_status()
        probs = [p for p in r.json()["hourly"]["precipitation_probability"] if p is not None]
        maxima = max(probs) if probs else 0
        prevista = maxima >= limiar_prob
        log.info("clima_consultado", prob_max_chuva=maxima, limiar=limiar_prob, chuva_prevista=prevista)
        return prevista
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as e:
        log.aviso("clima_indisponivel", erro=f"{type(e).__name__}: {str(e)[:150]}",
                  efeito="regra de chuva ignorada nesta execução")
        return False
