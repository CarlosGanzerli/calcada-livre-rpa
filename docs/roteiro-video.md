# Roteiro do vídeo (até 3 minutos)

Gravação de tela com narração. Ferramenta sugerida: OBS Studio ou a gravação de tela do Windows (Win + Alt + R) / do Mac (Cmd + Shift + 5). Publicar no YouTube como **Não listado** e colocar o link no PDF e no README.

**Antes de gravar:** MVP rodando (`docker compose up -d` no repositório `calcada-livre`, ou o MVP na URL pública), terminal aberto na pasta deste repositório com o `.env` carregado, banco limpo e o navegador no MVP. Deixe a fonte do terminal grande (pelo menos 16).

| Tempo | Tela | Fala (sugestão) |
|---|---|---|
| 0:00–0:20 | MVP aberto no navegador | "Somos a equipe da Calçada Livre: Carlos, Paulo, Lucas e Gustavo. Barreiras em calçadas chegam de três fontes: o cidadão pelo app, o nosso carrinho inspetor e a câmera com visão computacional. Alguém teria de conferir, priorizar e encaminhar cada uma à mão. O nosso robô de triagem faz isso sozinho, a cada 15 minutos." |
| 0:20–0:40 | `docs/processo-triagem.png` | "O fluxo em BPMN: importa lotes CSV, lê as ocorrências novas na API do MVP, consulta a previsão de chuva e, para cada ocorrência, decide: é válida? É duplicada? Qual a prioridade? Depois encaminha por subprefeitura e alerta as urgentes." |
| 0:40–1:00 | Terminal: `PYTHONPATH=src python -m triagem.semear`; depois o navegador recarregado | "Criamos um cenário com oito ocorrências e dois lotes CSV, um deles com formato errado. No MVP elas aparecem como 'nova', sem prioridade nem protocolo." |
| 1:00–1:40 | Terminal: `PYTHONPATH=src python -m triagem` (logs rolando) | "Rodamos o robô. Cada linha é um evento de auditoria em JSON, com data e hora. Vejam as decisões: o degrau na frente do Hospital das Clínicas virou prioridade **alta**; o relato no Rio de Janeiro foi para **quarentena**, fora do município; a detecção da câmera com confiança baixa também; o buraco relatado duas vezes virou **duplicada** da original; e o telefone que o cidadão escreveu na descrição foi **removido**, por LGPD. O CSV com formato errado foi rejeitado e o motivo ficou no log." |
| 1:40–2:05 | Navegador recarregado (tabela) e a pasta `saida/` com um `.csv` e um `.eml` abertos | "Integração com o MVP: o robô gravou status, prioridade, protocolo e subprefeitura pela API, e o cidadão já vê o resultado no mapa. Para cada subprefeitura sai um CSV e um e-mail. O encaminhamento é simulado: nada vai ao SP156 de verdade." |
| 2:05–2:40 | Parar o MVP (`docker compose stop api` ou Ctrl+C no uvicorn) e rodar o robô de novo | "E se a API cair? O robô tenta quatro vezes, esperando 2, 4 e 8 segundos. Como não voltou, registra ERRO, encerra com código 2 e não altera nada: as ocorrências ficam como 'nova' e entram na próxima execução. Se a previsão do tempo falhar, ele segue sem a regra de chuva e avisa no log. Nenhuma falha é silenciosa." |
| 2:40–2:55 | Terminal: `pytest -v` (20 aprovados) | "Temos 20 testes automatizados, com os cenários de sucesso, decisão e falha, rodando contra o MVP real." |
| 2:55–3:00 | README no GitHub | "Código, BPMN, logs e testes estão no repositório. Obrigado." |

**Dicas:** ensaie uma vez antes; se passar de 3 minutos, corte a parte do `pytest` (já está no PDF). Não mostre o arquivo `.env` na tela.
