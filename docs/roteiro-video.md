# Roteiro do vídeo (2:49)

O vídeo mostra uma **execução real** da automação contra a API do MVP, gravada da tela, com legendas. A narração abaixo acompanha as cenas; o tempo de cada fala cabe na cena (cerca de 2,5 palavras por segundo).

**Cenário da gravação:** MVP rodando localmente (`uvicorn app.main:app`) com banco limpo, automação rodando a partir deste repositório com `python -m triagem` e o log formatado por `python -m triagem.ver_log`. Os dados são os do `python -m triagem.semear` (ocorrências fictícias, sem dados pessoais reais). O serviço de previsão do tempo estava inacessível no ambiente da gravação; o vídeo mostra a automação seguindo sem a regra de chuva, e essa regra é coberta pelos testes.

| Tempo | Tela | Narração |
|---|---|---|
| 0:00 | Título e integrantes | "Somos a equipe Calçada Livre. Barreiras nas calçadas de São Paulo chegam pelo app do cidadão, pelo carrinho de sensores e pela câmera." |
| 0:09 | Título | "Conferir, priorizar e encaminhar cada relato à mão não escala. A nossa automação de RPA faz isso sozinha, a cada quinze minutos." |
| 0:18 | BPMN (percorrido da esquerda para a direita) | "No BPMN, a automação importa lotes CSV, lê as ocorrências novas na API do MVP, consulta a chuva e decide, uma a uma: é válida? É duplicada? Qual a prioridade?" |
| 0:29 | BPMN, parte final | "Depois gera um pacote por subprefeitura, alerta as urgentes e registra tudo num log de auditoria." |
| 0:36 | Terminal + MVP: `python -m triagem.semear` | "Para a demonstração, criamos oito ocorrências pela API do MVP e dois lotes CSV, um deles com formato errado." |
| 0:45 | MVP: tabela com tudo como "nova" | "No MVP, todas estão como nova, sem prioridade e sem protocolo." |
| 0:50 | Terminal: `python -m triagem` | "Agora, a execução real. Cada linha é um evento do log de auditoria." |
| 0:58 | Linhas do lote em destaque | "O lote com colunas erradas foi rejeitado, e a linha inválida do outro lote foi ignorada, sem parar a execução." |
| 1:05 | Aviso do clima em destaque | "A previsão do tempo ficou indisponível: a automação seguiu sem a regra de chuva e deixou um aviso no log." |
| 1:12 | Resumo da execução em destaque | "No total: dez lidas, sete encaminhadas, três de prioridade alta, duas em quarentena e uma duplicada." |
| 1:18 | Terminal: decisões filtradas do log | "Vamos às decisões." |
| 1:23 | Prioridade alta em destaque | "O degrau na frente do Hospital das Clínicas e os obstáculos perto de ponto de ônibus viraram prioridade alta." |
| 1:30 | Quarentena em destaque | "A coordenada no Rio de Janeiro e a detecção da câmera com baixa confiança foram para quarentena." |
| 1:37 | Duplicada em destaque | "O mesmo buraco relatado de novo virou duplicada e não é encaminhado duas vezes." |
| 1:43 | Dado pessoal removido em destaque | "E o telefone escrito na descrição foi removido, por causa da LGPD." |
| 1:48 | MVP atualizado + `GET /api/resumo` | "Integração com o MVP: a automação gravou status, prioridade, protocolo e subprefeitura pela API, com chave de acesso. A página já mostra o resultado." |
| 2:00 | Terminal: pasta `saida/`, CSV e e-mail | "Para cada subprefeitura sai um CSV e um e-mail. O envio ao SP156 é simulado: nada sai para a Prefeitura de verdade." |
| 2:10 | Terminal: MVP desligado e nova execução | "E se a API cair? Desligamos o MVP e rodamos de novo. A automação tenta quatro vezes, esperando dois, quatro e oito segundos…" |
| 2:28 | Erro final e código de saída 2 em destaque | "…e encerra com código dois, sem alterar nada. As ocorrências ficam para a próxima execução. Nenhuma falha é silenciosa." |
| 2:36 | Terminal: `pytest -v` (21 aprovados) | "São vinte e um testes automatizados, com sucesso, decisão e falha, rodando contra o MVP real." |
| 2:43 | Encerramento com o link do repositório | "Código, BPMN, logs e testes estão no GitHub. Obrigado!" |

Requisitos do enunciado cobertos: apresentação do problema e papel da automação (0:00–0:36), execução de ponta a ponta (0:36–1:18), regra de decisão (1:18–1:48), integração com o MVP (1:48–2:10) e tratamento de falhas (0:58, 1:05 e 2:10–2:36).
