# Testes e validação

```bash
pip install -r requirements-dev.txt
pytest -v
```

Para rodar contra o **MVP real** (recomendado), deixe o repositório `calcada-livre` na mesma pasta que este, ou aponte `MVP_DIR` para a pasta `mvp/` dele, e instale `calcada-livre/mvp/requirements.txt`. O cabeçalho do pytest mostra qual MVP foi usado.

Resultado da última execução: [`evidencias/resultado-testes.txt`](evidencias/resultado-testes.txt) (21 de 21 aprovados, contra o MVP real).

| Cenário | Teste | O que comprova |
|---|---|---|
| Sucesso | `test_sucesso_encaminha_e_gera_pacote` | Ocorrência válida vira `encaminhada`, com protocolo e subprefeitura; CSV e e-mail simulado gerados; log fecha com `execucao_concluida` |
| Sucesso | `test_idempotente_segunda_execucao_nao_reprocessa` | Rodar de novo não reprocessa nada |
| Decisão | `test_decisao_perto_de_hospital_vira_alta_e_alerta` | Degrau a poucos metros do Hospital das Clínicas vira `alta` e dispara alerta |
| Decisão | `test_decisao_chuva_sobe_um_nivel` | Com chuva prevista, trecho escuro sobe de baixa para média |
| Decisão | `test_decisao_quarentena_e_duplicada` | Coordenada no Rio e câmera sem foto vão para quarentena; relato repetido vira `duplicada` da original |
| Decisão | `test_decisao_remove_dado_pessoal_e_log_nao_vaza` | Telefone some da descrição; log não tem telefone nem coordenada |
| Decisão | `test_lote_csv_valido_e_invalido` | CSV bom é importado (linha ruim ignorada); CSV sem colunas vai para `rejeitados/` |
| Falha | `test_falha_api_fora_do_ar_tenta_com_espera_crescente` | 4 tentativas com espera de 2, 4 e 8 s; código de saída 2; nada alterado |
| Falha | `test_falha_api_cai_no_meio_preserva_o_restante` | Uma ocorrência gravada, a outra continua `nova` para a próxima execução |
| Falha | `test_falha_clima_fora_do_ar_degrada_sem_parar` | Open-Meteo fora: segue sem a regra de chuva e registra AVISO |
| Falha | `test_falha_arquivo_de_pois_ausente` | Arquivo de apoio ausente: segue sem a regra de proximidade e registra AVISO |
| Falha | `test_falha_sem_chave_nao_executa` | Sem `ROBO_API_KEY` o robô não executa |
| Unidade | `test_regras.py` (8 testes) | Validação, distância, duplicidade, prioridade, subprefeitura, protocolo e máscara de dados pessoais |

## Teste manual (o mesmo do vídeo)

1. Suba o MVP e rode `PYTHONPATH=src python -m triagem.semear`.
2. Abra o MVP no navegador: 8 ocorrências `nova`.
3. Rode `PYTHONPATH=src python -m triagem` e recarregue a página: status, prioridade, protocolo e subprefeitura preenchidos.
4. Pare o MVP e rode o robô de novo: 4 tentativas com espera crescente e ERRO no log, código de saída 2.
