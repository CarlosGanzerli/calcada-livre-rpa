# Calçada Livre · Automação de triagem de ocorrências (RPA)

[![Testes](https://github.com/CarlosGanzerli/calcada-livre-rpa/actions/workflows/testes.yml/badge.svg)](https://github.com/CarlosGanzerli/calcada-livre-rpa/actions/workflows/testes.yml)

Componente de **Automação** da CitizenTech **Calçada Livre**, FIAP Global Solution 2026.2, Engenharia de Software 4º ano, disciplina *Robotic Process Automation* (profs. Bruno Diniz e Cibele Ribeiro).

| Entrega | Onde está |
|---|---|
| Vídeo de demonstração (2 min 49 s) | [`assets/video-demonstracao.mp4`](https://github.com/CarlosGanzerli/calcada-livre-rpa/raw/main/assets/video-demonstracao.mp4) (MP4 de 6,4 MB; o link baixa o vídeo) |
| Relatório técnico em PDF | [`docs/Relatorio-RPA-Calcada-Livre.pdf`](docs/Relatorio-RPA-Calcada-Livre.pdf) |
| Fluxo do processo (BPMN 2.0) | [`docs/processo-triagem.bpmn`](docs/processo-triagem.bpmn) · [imagem](docs/processo-triagem.svg) |
| Código-fonte | [`src/triagem/`](src/triagem/) |
| Amostra do log de auditoria | [`logs/amostra-execucao-20261116.jsonl`](logs/amostra-execucao-20261116.jsonl) |
| Testes e evidências | [`tests/`](tests/) · [`assets/`](assets/) |

## Integrantes

| Nome completo | RM |
|---|---|
| Carlos Ganzerli | 99840 |
| Paulo Lopes | 551137 |
| Lucas Bandeira | 98640 |
| Gustavo Melo | 98809 |

## Ficha Técnica do MVP

| Item | Conteúdo |
|---|---|
| Nome | Calçada Livre |
| Cidadão e território | Pessoas com deficiência, idosos e pais com carrinho de bebê em São Paulo (SP) |
| Problema em uma frase | Barreiras em calçadas (buracos, degraus, obstáculos, falta de rampa, trechos escuros) impedem a circulação e não chegam organizadas a quem pode corrigi-las |
| Proposta de valor | Mapear as barreiras com cidadãos, um carrinho inspetor (Maker Lab) e visão computacional, triar automaticamente e encaminhar à subprefeitura certa com prioridade |
| Componentes | App web com mapa (MVP), carrinho inspetor (Maker Lab), visão computacional, **automação de triagem (este repositório)**, pipeline de dados, assistente com LLM local, infraestrutura DevSecOps |
| Fontes de dados | Relatos do app, leituras do carrinho, detecções da câmera, previsão Open-Meteo, pontos de interesse (hospitais, escolas, terminais) |
| Modelos de IA | YOLO (detecção de barreiras), classificador embarcado no carrinho, LLM local (assistente) |
| Repositórios | MVP e infraestrutura: [calcada-livre](https://github.com/CarlosGanzerli/calcada-livre) · Esta automação: [calcada-livre-rpa](https://github.com/CarlosGanzerli/calcada-livre-rpa) |
| Indicadores de impacto | Tempo entre relato e encaminhamento; relatos triados sem intervenção humana; barreiras de prioridade alta perto de serviços essenciais |
| ODS | 11 (cidades sustentáveis: mobilidade acessível), 10 (redução das desigualdades), 3 (saúde e bem-estar: quedas evitadas) |

> **Sobre os nomes.** No vocabulário de RPA, este componente é um robô de software. Neste repositório ele é chamado de **automação de triagem**, para não ser confundido com o **carrinho** do Maker Lab, que é um equipamento físico de outra disciplina. No código, os nomes `robo.py` e `ROBO_API_KEY` se referem sempre à automação.

## O problema e o papel da automação

Sem a automação, alguém da operação teria de abrir cada relato, conferir se o local existe, procurar se a barreira já foi relatada, decidir a urgência, descobrir a subprefeitura responsável e montar um encaminhamento. Isso é lento, repetitivo e sujeito a erro, e o cidadão fica sem resposta.

A automação faz esse trabalho sozinha a cada 15 minutos: recebe ocorrências do app, do carrinho e da câmera, valida, elimina duplicadas, prioriza, encaminha e devolve o resultado ao MVP, onde o cidadão vê o status e o protocolo.

## Arquitetura

![Onde a automação se encaixa: fontes, API do MVP, automação de triagem e saídas](docs/arquitetura.svg)

As setas mostram o caminho dos dados. A automação só conversa com o MVP pela API REST, o mesmo contrato usado pelas outras fontes.

## Fluxo do processo

O BPMN editável está em [`docs/processo-triagem.bpmn`](docs/processo-triagem.bpmn) (abre no [bpmn.io](https://demo.bpmn.io)). A imagem abaixo é vetorial: clique para ampliar.

![BPMN do processo de triagem](docs/processo-triagem.svg)

1. **Importa lotes CSV** da pasta `entrada/` (por exemplo, o carrinho sem Wi-Fi exporta as leituras). Arquivo inválido vai para `entrada/rejeitados/`.
2. **Lê as ocorrências `nova`** na API do MVP.
3. **Consulta a previsão de chuva** (Open-Meteo, sem chave).
4. **Para cada ocorrência** (repetição):
   - **Decisão 1, validade:** coordenada fora de São Paulo, tipo desconhecido, detecção da câmera sem foto ou com confiança abaixo de 0,5 → `quarentena`, com o motivo.
   - **Decisão 2, duplicidade:** mesmo tipo a até 20 m nos últimos 7 dias → `duplicada`, apontando a original.
   - **Decisão 3, prioridade:** prioridade base pelo tipo; a até 150 m de hospital, escola ou ponto de ônibus → `alta`; chuva prevista (60% ou mais) sobe um nível.
   - Atribui a **subprefeitura**, gera o **protocolo** (`CL-AAAAMMDD-XXXXXXXX`) e **remove telefone, e-mail e CPF** que o cidadão tenha escrito na descrição.
   - Grava tudo de volta na API com status `encaminhada`.
5. **Gera o pacote de encaminhamento**: um CSV e um e-mail `.eml` por subprefeitura em `saida/`.
6. **Alerta** as ocorrências de prioridade alta (webhook do Discord, Slack ou Teams ou, sem webhook, no log).
7. **Registra o resumo** da execução no log de auditoria.

> **O encaminhamento é simulado.** Nada é enviado ao SP156 nem à Prefeitura. Os arquivos em `saida/` mostram o que seria enviado.

## Regras de negócio

| Regra | Valor | Onde mudar |
|---|---|---|
| Área válida | Município de São Paulo (lat −24,01 a −23,35; lon −46,83 a −46,36) | `regras.py` |
| Confiança mínima da câmera | 0,5 | `CONFIANCA_MINIMA_VISAO` |
| Duplicada | mesmo tipo, até 20 m, últimos 7 dias | `RAIO_DUPLICADA_M`, `JANELA_DUPLICADA_DIAS` |
| Prioridade base | média: buraco, degrau, falta de rampa, obstáculo; baixa: calçada estreita, trecho escuro, outro | `regras.py` |
| Perto de serviço essencial | até 150 m → alta | `RAIO_POI_M` |
| Chuva | probabilidade máxima nas próximas 24 h igual ou maior que 60% → sobe um nível | `LIMIAR_CHUVA_PROB` |
| Subprefeitura | centro mais próximo entre as 32 (aproximação; em produção, polígonos do GeoSampa) | `regras.py` |

## Exceções e resiliência

| Falha | O que a automação faz |
|---|---|
| API do MVP fora do ar | 4 tentativas com espera crescente (2 s, 4 s, 8 s). Se não voltar, registra ERRO e encerra **sem alterar nada**; as ocorrências continuam `nova` e são processadas na próxima execução |
| API cai no meio da execução | Para a execução; o que já foi gravado fica, o resto continua `nova` |
| Erro de dado em uma ocorrência (HTTP 4xx) | Registra o erro daquele item e segue para o próximo |
| Arquivo CSV vazio, ilegível ou sem colunas | Move para `entrada/rejeitados/` e registra o motivo |
| Linha inválida dentro de um CSV bom | Ignora a linha, registra o número dela e importa as demais |
| Open-Meteo fora do ar | Segue sem a regra de chuva e registra AVISO |
| Arquivo de pontos de interesse ausente | Segue sem a regra de proximidade e registra AVISO |
| Duplicada | Marca `duplicada` e aponta a original |
| Chave de acesso não configurada | Não executa e registra ERRO de configuração |
| Automação executada duas vezes | Nada é processado de novo: só lê `nova`, e o protocolo é determinístico |

Nenhuma falha é silenciosa: toda exceção vira uma linha de log com nível AVISO ou ERRO, e o código de saída do processo indica o resultado (0 = sucesso, 1 = concluído com erros, 2 = API indisponível).

## Logs e auditoria

Uma linha JSON por evento em `logs/robo-triagem-AAAAMMDD.jsonl`, com data e hora UTC, id da execução, evento, contagens, motivos e erros. A amostra [`logs/amostra-execucao-20261116.jsonl`](logs/amostra-execucao-20261116.jsonl) é real e traz quatro execuções seguidas: uma completa, duas do modo contínuo (a segunda tria um relato novo) e uma com o MVP desligado.

```json
{"ts": "2026-11-16T18:01:12+00:00", "nivel": "INFO", "execucao": "09aa3e12", "evento": "ocorrencia_encaminhada", "id": "13b8b1d2-6c03-48bd-a584-16370973e549", "protocolo": "CL-20261116-13B8B1D2", "prioridade": "alta", "razoes": ["base_degrau=media", "perto_de_hospital"], "subprefeitura": "Pinheiros", "dado_pessoal_removido": false}
```

O log **nunca** recebe descrição, foto ou coordenada: a classe `LogAuditoria` recusa esses campos.

Para ler o log no terminal em formato legível (hora de Brasília, uma linha por evento):

```bash
python -m triagem 2>&1 | python -m triagem.ver_log          # durante a execução
python -m triagem.ver_log < logs/amostra-execucao-20261116.jsonl
```

## Integração com o MVP

A automação lê e grava no mesmo contrato usado por todos os componentes (a ocorrência), pela API REST do MVP:

| Chamada | Uso |
|---|---|
| `GET /api/ocorrencias?status=nova` | ocorrências a triar |
| `GET /api/ocorrencias?desde=…` | referências para checar duplicadas |
| `POST /api/ocorrencias` | importar lotes CSV |
| `PATCH /api/ocorrencias/{id}` com `X-API-Key` | gravar status, prioridade, protocolo, subprefeitura e motivo |

O resultado é consumido pelo MVP: a página e o resumo da API passam a mostrar status, prioridade, protocolo e subprefeitura.

| Antes da execução | Depois da execução |
|---|---|
| ![Página do MVP antes: 8 ocorrências novas, sem prioridade nem protocolo](assets/mvp-antes-da-triagem.png) | ![Página do MVP depois: 7 encaminhadas, 2 em quarentena e 1 duplicada](assets/mvp-depois-da-triagem.png) |

O pacote gerado nessa execução está em [`assets/exemplo-saida/`](assets/exemplo-saida/) (um CSV e um e-mail simulado por subprefeitura).

## Como executar

Requisitos: Python 3.11 ou mais novo e o MVP rodando (repositório [`calcada-livre`](https://github.com/CarlosGanzerli/calcada-livre)).

```bash
# 1. Suba o MVP (no repositório calcada-livre)
cd calcada-livre && cp .env.example .env && docker compose up -d
#    ou, sem Docker: cd mvp && pip install -r requirements.txt && ROBO_API_KEY=minha-chave uvicorn app.main:app

# 2. Prepare a automação (neste repositório)
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env    # preencha API_URL e ROBO_API_KEY (a mesma chave do MVP)
export $(grep -v '^#' .env | xargs)                    # Windows PowerShell: defina as variáveis manualmente

# 3. Cenário de demonstração e execução
PYTHONPATH=src python -m triagem.semear     # cria ocorrências de todos os casos + 2 lotes CSV
PYTHONPATH=src python -m triagem            # uma execução
PYTHONPATH=src python -m triagem --continuo # a cada 15 minutos

# Com Docker
docker build -t calcada-livre-rpa . && docker run --env-file .env calcada-livre-rpa
```

## Testes

```bash
pytest -v
```

21 testes cobrindo os três cenários exigidos: **sucesso** (encaminha, gera pacote, não reprocessa), **decisão** (alta perto de hospital, chuva sobe nível, quarentena, duplicada, remoção de dado pessoal, lote CSV) e **falha** (API fora do ar com espera crescente, API cai no meio da execução, previsão fora do ar, arquivo ausente, chave ausente). Se o repositório `calcada-livre` estiver na mesma pasta que este, os testes rodam contra o **MVP real**; senão, contra um MVP simulado com o mesmo contrato. Detalhes e resultado em [`tests/README.md`](tests/README.md). A cada envio de código, o GitHub Actions roda os testes e publica a imagem do container.

## Segurança e LGPD

- Nenhum dado pessoal é coletado: a ocorrência não tem nome, CPF, telefone nem e-mail.
- Se o cidadão escrever telefone, e-mail ou CPF na descrição, a automação remove antes de encaminhar.
- Logs sem descrição, foto ou coordenada exata.
- A chave de acesso (`ROBO_API_KEY`) fica em variável de ambiente ou no GitHub Secrets, nunca no código; `.env` está no `.gitignore`.
- Só a automação (com a chave) altera ocorrências; o cidadão só cria e consulta.
- O container roda com usuário sem privilégio.
- Os dados de demonstração são fictícios e o encaminhamento é simulado.

## Estrutura

```
src/triagem/   código da automação (robo.py orquestra; regras.py tem as decisões)
docs/          BPMN (.bpmn, .svg e .png), arquitetura, relatório em PDF e roteiro do vídeo
assets/        vídeo, evidências visuais e exemplo de saída (CSV e e-mail simulado)
logs/          amostra de log real, sem dados sensíveis
tests/         testes automatizados, instruções e evidências
data/          pontos de interesse (amostra de hospitais, escolas e terminais)
```
