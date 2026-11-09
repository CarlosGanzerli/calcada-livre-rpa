"""Popula a API com um cenário de demonstração (para o vídeo e para testar à mão).

Uso: python -m triagem.semear
Cria ocorrências de cada origem cobrindo todas as decisões do robô e deixa um
lote CSV válido e um inválido na pasta entrada/.
"""
import httpx

from .config import Config

CENARIO = [
    # (descrição para o operador, corpo)
    ("buraco comum, longe de serviços", {"tipo": "buraco", "latitude": -23.6105, "longitude": -46.6952, "origem": "app",
                                         "descricao": "Buraco na calçada em frente ao número 120"}),
    ("degrau na frente do Hospital das Clínicas", {"tipo": "degrau", "latitude": -23.5574, "longitude": -46.6699,
                                                  "origem": "carrinho"}),
    ("obstáculo detectado pela câmera perto do MASP", {"tipo": "obstaculo", "latitude": -23.5615, "longitude": -46.6560,
                                                      "origem": "visao", "foto_url": "https://example.org/frames/0412.jpg",
                                                      "confianca": 0.87}),
    ("mesmo buraco relatado de novo (duplicada)", {"tipo": "buraco", "latitude": -23.6106, "longitude": -46.6951,
                                                   "origem": "app"}),
    ("coordenada no Rio de Janeiro (quarentena)", {"tipo": "buraco", "latitude": -22.9068, "longitude": -43.1729,
                                                    "origem": "app"}),
    ("câmera com confiança baixa (quarentena)", {"tipo": "buraco", "latitude": -23.5900, "longitude": -46.6400,
                                                  "origem": "visao", "foto_url": "https://example.org/frames/0999.jpg",
                                                  "confianca": 0.21}),
    ("relato com telefone na descrição (LGPD)", {"tipo": "sem_rampa", "latitude": -23.5300, "longitude": -46.7000,
                                                  "origem": "app",
                                                  "descricao": "Esquina sem rampa. Qualquer coisa me liga (11) 98765-4321"}),
    ("trecho escuro lido pelo LDR do carrinho", {"tipo": "trecho_escuro", "latitude": -23.6400, "longitude": -46.7600,
                                                  "origem": "carrinho"}),
]

LOTE_OK = """tipo,latitude,longitude,origem,descricao
obstaculo,-23.5420,-46.4712,carrinho,Lixeira bloqueando a calçada perto do terminal
calcada_estreita,-23.5000,-46.6200,carrinho,
buraco,nao-e-numero,-46.62,carrinho,linha com erro de leitura do GPS
"""
LOTE_RUIM = "data;sensor;valor\n2026-11-09;ldr;512\n"


def main() -> None:
    cfg = Config()
    with httpx.Client(base_url=cfg.api_url, timeout=10) as http:
        for rotulo, corpo in CENARIO:
            r = http.post("/api/ocorrencias", json=corpo)
            r.raise_for_status()
            print(f"criada  {r.json()['id'][:8]}  {rotulo}")
    cfg.pasta_entrada.mkdir(parents=True, exist_ok=True)
    (cfg.pasta_entrada / "carrinho_sem_wifi.csv").write_text(LOTE_OK, encoding="utf-8")
    (cfg.pasta_entrada / "planilha_formato_errado.csv").write_text(LOTE_RUIM, encoding="utf-8")
    print(f"lotes CSV deixados em {cfg.pasta_entrada}")


if __name__ == "__main__":
    main()
