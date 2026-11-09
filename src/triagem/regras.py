"""Regras de negócio da triagem. Funções puras, fáceis de testar."""
import csv
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TIPOS_VALIDOS = {"buraco", "obstaculo", "degrau", "calcada_estreita", "trecho_escuro", "sem_rampa", "outro"}

# Limites aproximados do município de São Paulo
LAT_MIN, LAT_MAX = -24.01, -23.35
LON_MIN, LON_MAX = -46.83, -46.36

# Prioridade base por tipo: o que impede a passagem de cadeira de rodas é média;
# o que dificulta, mas não bloqueia, é baixa. A proximidade de serviços e a chuva sobem o nível.
PRIORIDADE_BASE = {
    "buraco": "media",
    "degrau": "media",
    "sem_rampa": "media",
    "obstaculo": "media",
    "calcada_estreita": "baixa",
    "trecho_escuro": "baixa",
    "outro": "baixa",
}
NIVEIS = ["baixa", "media", "alta"]

# Centroides aproximados das 32 subprefeituras. A atribuição é pelo centroide mais
# próximo, uma aproximação documentada (em produção, usar os polígonos do GeoSampa).
SUBPREFEITURAS = {
    "Sé": (-23.5505, -46.6333), "Lapa": (-23.5235, -46.7012), "Pinheiros": (-23.5670, -46.6950),
    "Butantã": (-23.5880, -46.7480), "Vila Mariana": (-23.5893, -46.6340), "Ipiranga": (-23.5950, -46.6060),
    "Mooca": (-23.5580, -46.5900), "Santana/Tucuruvi": (-23.4870, -46.6200), "Casa Verde": (-23.5040, -46.6600),
    "Freguesia/Brasilândia": (-23.4700, -46.6900), "Pirituba/Jaraguá": (-23.4700, -46.7400),
    "Perus": (-23.4040, -46.7550), "Vila Maria/Vila Guilherme": (-23.5120, -46.5800),
    "Jaçanã/Tremembé": (-23.4500, -46.5800), "Penha": (-23.5250, -46.5420),
    "Ermelino Matarazzo": (-23.4950, -46.4800), "São Miguel": (-23.4980, -46.4440),
    "Itaim Paulista": (-23.4980, -46.4000), "Guaianases": (-23.5420, -46.4130), "Itaquera": (-23.5360, -46.4560),
    "Cidade Tiradentes": (-23.5830, -46.4060), "São Mateus": (-23.6000, -46.4800),
    "Vila Prudente": (-23.5850, -46.5800), "Sapopemba": (-23.6000, -46.5150),
    "Aricanduva/Formosa/Carrão": (-23.5600, -46.5300), "Jabaquara": (-23.6450, -46.6400),
    "Santo Amaro": (-23.6500, -46.7100), "Campo Limpo": (-23.6400, -46.7600), "M'Boi Mirim": (-23.6900, -46.7700),
    "Cidade Ademar": (-23.6750, -46.6550), "Capela do Socorro": (-23.7200, -46.7000),
    "Parelheiros": (-23.8300, -46.7300),
}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_TELEFONE = re.compile(r"(\(?\b\d{2}\)?\s?)?\b9?\d{4}[-\s]?\d{4}\b")


@dataclass
class PontoInteresse:
    nome: str
    categoria: str  # hospital, escola, ponto_onibus
    latitude: float
    longitude: float


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em metros pela fórmula de haversine."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def validar(oc: dict, confianca_minima_visao: float = 0.5) -> tuple[bool, str | None]:
    """Retorna (válida, código do motivo). Inválidas vão para quarentena, nunca são apagadas."""
    try:
        lat, lon = float(oc.get("latitude")), float(oc.get("longitude"))
    except (TypeError, ValueError):
        return False, "coordenada_ausente"
    if math.isnan(lat) or math.isnan(lon):
        return False, "coordenada_ausente"
    if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
        return False, "fora_do_municipio"
    if oc.get("tipo") not in TIPOS_VALIDOS:
        return False, "tipo_invalido"
    if oc.get("origem") == "visao":
        if not oc.get("foto_url"):
            return False, "visao_sem_foto"
        if (oc.get("confianca") or 0) < confianca_minima_visao:
            return False, "visao_baixa_confianca"
    return True, None


def achar_duplicada(oc: dict, referencias: list[dict], raio_m: float) -> dict | None:
    """Mesma barreira já registrada: mesmo tipo a menos de `raio_m` metros."""
    for ref in referencias:
        if ref["id"] == oc["id"] or ref["tipo"] != oc["tipo"]:
            continue
        if distancia_m(oc["latitude"], oc["longitude"], ref["latitude"], ref["longitude"]) <= raio_m:
            return ref
    return None


def poi_proximo(oc: dict, pois: list[PontoInteresse], raio_m: float) -> PontoInteresse | None:
    melhor, melhor_d = None, raio_m
    for p in pois:
        d = distancia_m(oc["latitude"], oc["longitude"], p.latitude, p.longitude)
        if d <= melhor_d:
            melhor, melhor_d = p, d
    return melhor


def subir(nivel: str) -> str:
    return NIVEIS[min(NIVEIS.index(nivel) + 1, len(NIVEIS) - 1)]


def decidir_prioridade(oc: dict, poi: PontoInteresse | None, chuva_prevista: bool) -> tuple[str, list[str]]:
    """Retorna a prioridade e as razões, para a decisão ser explicável e auditável."""
    nivel = PRIORIDADE_BASE.get(oc["tipo"], "baixa")
    razoes = [f"base_{oc['tipo']}={nivel}"]
    if poi:
        nivel = "alta"
        razoes.append(f"perto_de_{poi.categoria}")
    if chuva_prevista and nivel != "alta":
        nivel = subir(nivel)
        razoes.append("chuva_prevista")
    return nivel, razoes


def subprefeitura(lat: float, lon: float) -> str:
    return min(SUBPREFEITURAS, key=lambda n: distancia_m(lat, lon, *SUBPREFEITURAS[n]))


def gerar_protocolo(oc: dict, quando: datetime) -> str:
    """Determinístico: rodar o robô duas vezes não gera dois protocolos."""
    return f"CL-{quando:%Y%m%d}-{oc['id'].replace('-', '')[:8].upper()}"


def mascarar_dados_pessoais(texto: str | None) -> tuple[str | None, bool]:
    """Remove e-mail, CPF e telefone que o cidadão tenha escrito por engano (LGPD)."""
    if not texto:
        return texto, False
    novo = _EMAIL.sub("[e-mail removido]", texto)
    novo = _CPF.sub("[documento removido]", novo)
    novo = _TELEFONE.sub("[telefone removido]", novo)
    return novo, novo != texto


def carregar_pois(arquivo: Path) -> list[PontoInteresse]:
    with arquivo.open(encoding="utf-8") as f:
        return [
            PontoInteresse(l["nome"], l["categoria"], float(l["latitude"]), float(l["longitude"]))
            for l in csv.DictReader(f)
        ]
