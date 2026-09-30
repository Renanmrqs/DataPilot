# Entendendo o desenvolvimento do DataPilot

## Onde estamos

O DataPilot é um protótipo local de um portal de vendas com um assistente de IA. O usuário aprovou a experiência em exemplos reais de margem, bicicletas e acessórios, incluindo continuidade da conversa e gráficos. Os principais agregados desses exemplos foram conferidos no banco durante o [checkup de 30/09/2026](checkup-2026-09-30.md). Isso não equivale a homologação com dados de clientes.

**Direção acordada:** fontes → tratamento no Qlik Sense → QVDs tratados → DataPilot → painel + IA. O tratamento de negócio continua no Qlik; o DataPilot deve consumir sua saída. Hoje a implementação ainda é CSV/SQLite.

## Acompanhe uma pergunta pelo código

Imagine perguntar: **“Qual é o ticket médio de bicicletas?”**

1. **A interface recebe a pergunta.** `src/web/app.js` envia o texto, os filtros e até quatro trocas recentes para `/api/analysis`.
2. **A API coordena a análise.** `src/api/analysis.py` valida o pedido e aciona o planejador.
3. **A IA escolhe o que analisar.** `src/ai/analysis_plan.py` valida o plano retornado: assunto, filtros, indicadores e gráficos permitidos. A IA não recebe permissão para executar SQL livre.
4. **O sistema calcula.** `src/analytics/analysis.py` consulta o SQLite. Ticket médio é a receita selecionada dividida pela quantidade de pedidos distintos selecionados.
5. **A IA explica os resultados.** `src/ai/copilot.py` recebe o contexto calculado. A explicação pode errar, por isso os valores calculados precisam continuar acessíveis.
6. **A interface mostra a resposta.** `src/web/analysis-panel.js` apresenta a seleção analisada, indicadores e gráficos. Os gráficos abrem sob demanda, sem outra chamada ao provedor.

Antes disso tudo, `src/etl/build_database.py` carrega os seis CSVs, valida chaves, relacionamentos, datas e valores e confere os totais. `sql/schema.sql` define como os dados se relacionam.

## O que já existe e o que falta

| Parte | Situação |
|---|---|
| Dados | Carga validada de CSVs em SQLite e testes de integridade |
| Portal | Filtros, indicadores, evolução mensal, categorias e temas |
| Assistente | Planos limitados às análises suportadas, contexto recente e provedores configuráveis |
| Continuidade em falhas | O painel calculado é devolvido se a etapa de explicação falhar |
| Avaliação da IA | Testes simulados e exemplos reais aprovados pelo usuário; avaliação sistemática ainda pendente |
| Reutilização de QVDs | Direção definida; leitor e configuração por conjunto de dados ainda não implementados |
| Uso compartilhado | Ainda sem autenticação ou implantação de produção |
| Histórico | Mantido apenas na memória do navegador; recarregar a página perde a conversa |

## Melhoria de 30/09/2026

**Problema:** uma resposta podia ter indicadores calculados e nenhum gráfico. A interface mostrava apenas os filtros e escondia os indicadores. Isso também prejudicava a recuperação quando a explicação da IA falhava.

**Mudança:** respostas com indicadores e sem gráficos agora exibem o painel diretamente. Respostas com gráficos mantêm o botão para abri-los. Seleções vazias continuam sem botão.

**Como conferir:** obtenha uma análise com indicadores e sem gráficos; os cartões devem aparecer abaixo da resposta. Na análise com gráficos, abra e feche o painel. Para reproduzir exatamente o primeiro caso sem depender da escolha de um modelo, use um retorno simulado com `kpis` preenchido e `charts: []`.

## Próximas entregas acordadas

1. **Separar acesso aos dados:** extrair do código dependências da base de demonstração, preservando filtros, indicadores e estrutura de resposta da API. Critério: resultados atuais continuam iguais nos testes.
2. **Definir configuração do conjunto de dados:** campos, tipos, chaves, relacionamentos, granularidade, métricas, moeda e atualização. Mapear também medidas que estejam nas expressões do aplicativo Qlik. Critério: definições explícitas e configurações inválidas rejeitadas.
3. **Simular uma segunda base já tratada:** usar nomes de campos diferentes e pedidos com múltiplos itens. Critério: trocar configuração e fonte sem reescrever chat e gráficos; totais e relacionamentos conferidos.
4. **Avaliar o acesso aos QVDs:** escolher e testar o mecanismo de leitura, tipos, precisão monetária e atualização sem recriar o tratamento do Qlik. Critério: comparação reproduzível entre origem e dados consultados. Leitura direta ou representação intermediária ainda será decidida.
5. **Preparar o piloto real:** reconciliar medidas com o Qlik sob os mesmos filtros, medir tempo e memória e validar separação de acesso por cliente antes de uso compartilhado.

PostgreSQL não é uma migração obrigatória. DuckDB/Parquet são possibilidades discutidas, não uma decisão de implementação. Volume, frequência de atualização e consultas simultâneas orientarão essa escolha.

Refinamentos de experiência continuam no backlog: datas parciais explícitas, evitar chamar variação de sazonalidade sem evidência, comparações entre categorias e legibilidade dos gráficos. Não são pré-requisitos para reescrever o tratamento de dados, que permanece no Qlik.

Faça cada entrega com um exemplo visível de antes/depois e uma verificação correspondente. Isso ajuda a aprender o motivo de cada mudança.

## Rodar e conferir

O [guia do protótipo](prototype.pt-BR.md) explica a configuração. Com as dependências instaladas, rode na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m src.etl.build_database
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Pare o servidor antes de reconstruir o banco. Acesse http://127.0.0.1:8000. O painel funciona sem chave de IA; o chat depende da configuração local de um provedor. Os testes automatizados de provedores usam simulações e não validam a qualidade de uma resposta real.
