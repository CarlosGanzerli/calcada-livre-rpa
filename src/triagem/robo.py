"""Robô de triagem de ocorrências da Calçada Livre.

Fluxo (ver docs/processo-triagem.bpmn):
  1. Importa lotes CSV da pasta entrada/.
  2. Lê na API do MVP as ocorrências com status "nova".
  3. Para cada uma: valida (inválida -> quarentena), procura duplicada
     (mesmo tipo a menos de 20 m em 7 dias -> duplicada), decide a prioridade
     (perto de hospital, escola ou ponto de ônibus -> alta; chuva prevista sobe um nível),
     atribui subprefeitura, gera protocolo, remove dado pessoal da descrição e
     grava tudo de volta na API com status "encaminhada".
  4. Gera o pacote de encaminhamento (CSV + e-mail simulado) por subprefeitura.
  5. Alerta as ocorrências de prioridade alta.
  6. Registra o resumo da execução no log de auditoria.

Uso:
  python -m triagem               # uma execução
  python -m triagem --continuo    # repete a cada INTERVALO_MIN minutos
"""
import argparse
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from . import clima, encaminhamento, lote, regras
from .cliente_api import ApiIndisponivel, ClienteMVP
from .config import Config
from .logs import LogAuditoria

OK, COM_ERROS, API_FORA = 0, 1, 2


def _parse_data(valor: str) -> datetime:
    d = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def executar(cfg: Config | None = None, http_api: httpx.Client | None = None,
             http_externo: httpx.Client | None = None, dormir=time.sleep, eco: bool = True) -> tuple[int, dict]:
    cfg = cfg or Config()
    inicio = datetime.now(timezone.utc)
    log = LogAuditoria(cfg.pasta_logs, execucao_id=uuid.uuid4().hex[:8], eco=eco)
    api = ClienteMVP(cfg, log, http=http_api, dormir=dormir)
    res = {"lidas": 0, "quarentena": 0, "duplicadas": 0, "encaminhadas": 0, "alta": 0,
           "dados_pessoais_removidos": 0, "erros": 0}
    log.info("execucao_iniciada", api=cfg.api_url)

    if not cfg.api_key:
        log.erro("configuracao_invalida", motivo="ROBO_API_KEY ausente")
        return COM_ERROS, res

    # Arquivo de apoio ausente não derruba o robô: ele segue sem a regra de proximidade.
    try:
        pois = regras.carregar_pois(cfg.arquivo_pois)
    except (FileNotFoundError, KeyError, ValueError) as e:
        pois = []
        log.aviso("pois_indisponiveis", arquivo=cfg.arquivo_pois.name, erro=type(e).__name__,
                  efeito="regra de proximidade ignorada nesta execução")

    try:
        res["lote"] = lote.importar_lotes(cfg.pasta_entrada, api, log)
        novas = list(reversed(api.listar(status="nova")))  # mais antigas primeiro
        desde = inicio - timedelta(days=cfg.janela_duplicada_dias)
        referencias = [o for o in api.listar(desde=desde) if o["status"] in ("validada", "encaminhada")]
    except ApiIndisponivel as e:
        log.erro("api_indisponivel", etapa="leitura", erro=str(e)[:200],
                 efeito="nada foi alterado; as ocorrências serão processadas na próxima execução")
        return API_FORA, res

    res["lidas"] = len(novas)
    log.info("ocorrencias_lidas", quantidade=len(novas), referencias_7d=len(referencias))
    chuva = clima.chuva_prevista_24h(log, cfg.limiar_chuva_prob, http=http_externo) if novas else False

    encaminhadas: list[dict] = []
    for oc in novas:  # estrutura de repetição sobre a coleção
        try:
            valida, motivo = regras.validar(oc, cfg.confianca_minima_visao)
            if not valida:  # decisão 1: dado inválido
                api.atualizar(oc["id"], {"status": "quarentena", "motivo": motivo})
                res["quarentena"] += 1
                log.info("ocorrencia_quarentena", id=oc["id"], motivo=motivo)
                continue

            original = regras.achar_duplicada(oc, referencias, cfg.raio_duplicada_m)
            if original:  # decisão 2: barreira já registrada
                api.atualizar(oc["id"], {"status": "duplicada", "duplicada_de": original["id"],
                                         "motivo": "mesmo_tipo_ate_%dm_em_%dd" % (cfg.raio_duplicada_m, cfg.janela_duplicada_dias)})
                res["duplicadas"] += 1
                log.info("ocorrencia_duplicada", id=oc["id"], duplicada_de=original["id"])
                continue

            poi = regras.poi_proximo(oc, pois, cfg.raio_poi_m)
            prioridade, razoes = regras.decidir_prioridade(oc, poi, chuva)  # decisão 3: prioridade
            descricao, mascarou = regras.mascarar_dados_pessoais(oc.get("descricao"))
            campos = {
                "status": "encaminhada",
                "prioridade": prioridade,
                "subprefeitura": regras.subprefeitura(oc["latitude"], oc["longitude"]),
                "protocolo": regras.gerar_protocolo(oc, _parse_data(oc["criada_em"])),
                "motivo": ";".join(razoes),
            }
            if mascarou:
                campos["descricao"] = descricao
                res["dados_pessoais_removidos"] += 1
            atualizada = api.atualizar(oc["id"], campos)
            encaminhadas.append({**atualizada, "razoes": campos["motivo"]})
            referencias.append(atualizada)
            res["encaminhadas"] += 1
            res["alta"] += prioridade == "alta"
            log.info("ocorrencia_encaminhada", id=oc["id"], protocolo=campos["protocolo"], prioridade=prioridade,
                     razoes=razoes, subprefeitura=campos["subprefeitura"], dado_pessoal_removido=mascarou)
        except ApiIndisponivel as e:
            res["erros"] += 1
            log.erro("api_indisponivel", etapa="atualizacao", id=oc["id"], erro=str(e)[:200],
                     efeito="execução interrompida; o restante continua como 'nova'")
            break
        except httpx.HTTPStatusError as e:  # erro de dado em um item: registra e segue para o próximo
            res["erros"] += 1
            log.erro("ocorrencia_falhou", id=oc["id"], http=e.response.status_code)

    encaminhamento.gerar_pacotes(encaminhadas, cfg.pasta_saida, inicio, log)
    encaminhamento.alertar([o for o in encaminhadas if o["prioridade"] == "alta"], cfg.alerta_webhook_url, log,
                           http=http_externo)

    res["duracao_s"] = round((datetime.now(timezone.utc) - inicio).total_seconds(), 2)
    codigo = COM_ERROS if res["erros"] else OK
    (log.erro if codigo else log.info)("execucao_concluida", **res)
    return codigo, res


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Robô de triagem de ocorrências da Calçada Livre")
    p.add_argument("--continuo", action="store_true", help="repete a cada INTERVALO_MIN minutos")
    args = p.parse_args(argv)
    cfg = Config()
    if not args.continuo:
        return executar(cfg)[0]
    while True:
        executar(cfg)
        time.sleep(cfg.intervalo_min * 60)


if __name__ == "__main__":
    sys.exit(main())
