# DataPilot

**Checkpoint de 20/10/2026:** login da demo confirmado; análise real com IA ainda falhando. [Estado salvo e próximos passos](docs/checkpoint-2026-10-20.md).

**Português** | [English](README.en.md)

Projeto de aprendizado e portfólio que combina um portal de análise independente com um assistente de IA para perguntas sobre o negócio.

**Estado atual: protótipo local.** A interface está em português brasileiro e funciona fora do Qlik Sense. O visual e a experiência de análise ainda precisam de refinamento.

**Para acompanhar o código:** [Entendendo o desenvolvimento e as próximas entregas](docs/desenvolvimento.pt-BR.md).

**Guias:** [Protótipo em português](docs/prototype.pt-BR.md) · [Protótipo em inglês](docs/prototype.md) · [Fluxo técnico da análise — em inglês](docs/business-analysis.md)

**Demo pública em preparação:** [login por e-mail, quatro perguntas por conta e roteiro para entender a implementação](docs/demo-access.pt-BR.md). A interface e as cotas estão implementadas; deploy ainda precisa de validação. A IA pública permanece pausada por padrão; a configuração local pode habilitá-la para testes.

## O que funciona hoje

- Carregamento validado de seis conjuntos de dados CSV no SQLite.
- Um painel web com filtros, indicadores de vendas e gráficos.
- Perguntas de negócio que geram painéis predefinidos de vendas, ticket médio, margem bruta e produtos.
- Cálculos feitos em SQL/Python; a IA, quando configurada, escolhe o plano de análise e explica os resultados.
- Provedores e modelos configuráveis, incluindo Gemini, DeepSeek, OpenAI e serviços com API compatível.
- O painel calculado continua disponível se a explicação da IA falhar.

O usuário faz uma pergunta sobre o negócio, e o assistente escolhe os indicadores e gráficos relacionados. A IA escolhe gráficos e indicadores entre opções permitidas. O chat considera as últimas quatro trocas e os filtros da análise anterior. Os gráficos são opcionais.

## Como executar localmente

Na pasta principal do projeto, abra o PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.etl.build_database
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Crie o ambiente virtual somente se ele ainda não existir. Abra http://127.0.0.1:8000.
No Windows, pare o servidor antes de reconstruir o banco de dados.

A IA é opcional: copie [.env.example](.env.example) para `.env`, configure as credenciais e os identificadores dos modelos localmente e reinicie o servidor. Nunca inclua credenciais em commits. Consulte os guias para detalhes de configuração e limitações.

## Como as partes se conectam

O caminho dos dados:

```text
CSVs originais -> validação e carga em Python -> SQLite -> FastAPI -> portal web
```

O caminho de uma análise:

```text
Pergunta -> plano validado da IA -> indicadores e gráficos calculados -> explicação da IA
```

A API coordena esse fluxo, consultando o banco para calcular os valores usados no painel e na explicação.

| Local | Responsabilidade |
|---|---|
| `src/etl/build_database.py` | Validar e carregar os CSVs originais |
| `sql/schema.sql` | Definir tabelas, restrições e a visão de vendas |
| `src/api/` | Receber requisições HTTP e coordenar a análise |
| `src/analytics/` | Definir métricas, consultas e estruturas dos painéis |
| `src/ai/` | Enviar requisições aos provedores e validar planos de análise |
| `src/web/` | Exibir a interface em português e desenhar os gráficos |
| `tests/` | Verificar dados, API e integração com respostas de IA simuladas |
| `docs/` | Documentar configuração, métricas e limitações conhecidas |

O SQLite atende à execução local atual. PostgreSQL não é uma migração obrigatória nem uma próxima entrega definida. O script antigo `transform_sales.py` é separado do carregamento do banco usado pelo protótipo.

## Validação e limites

A quantidade de pedidos usa a contagem distinta dos pedidos de venda. O ticket médio divide a receita selecionada pelos pedidos distintos da seleção. O lucro bruto desconta o custo dos produtos; despesas necessárias ao cálculo do lucro líquido não estão disponíveis. A moeda da fonte ainda não foi identificada além do símbolo de dólar.

O carregamento verifica chaves, relacionamentos, datas e valores monetários, depois confere os totais antes de substituir o banco. A IA usa dados agregados validados e não pode executar SQL arbitrário. Mesmo assim, pode interpretar uma pergunta incorretamente ou inventar uma explicação.

Para executar os testes:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Os testes automatizados dos provedores usam respostas simuladas. Uma análise real com Gemini foi concluída após uma falha temporária do serviço. Essa verificação não garante confiabilidade para todos os provedores ou perguntas.

Este é um protótipo local para um usuário, sem autenticação ou configuração de produção. A base atual cobre perguntas relacionadas a vendas. A conversa mantém contexto recente na memória do navegador. Uma análise suportada normalmente usa duas etapas de IA; uma falha temporária pode gerar uma nova tentativa por etapa. O uso está sujeito aos custos e limites da conta no provedor.

## Próximos passos: reutilizar QVDs tratados

1. Separar o acesso aos dados do planejamento, cálculo e apresentação das análises.
2. Configurar campos, chaves, relacionamentos e métricas por conjunto de dados.
3. Validar a reutilização com uma segunda base de teste já tratada, preservando chat e gráficos.
4. Avaliar a leitura dos QVDs e reconciliar os indicadores com o aplicativo Qlik antes do piloto real.

A direção acordada é **fontes → tratamento no Qlik Sense → QVDs tratados → DataPilot → painel + IA**. O tratamento de negócio permanece no Qlik. Medidas definidas no aplicativo precisam ser mapeadas; ler QVD não reproduz automaticamente expressões e associações do Qlik.

A implementação ainda usa CSV/SQLite. Leitura QVD, configuração por cliente e isolamento entre clientes não estão implementados. PostgreSQL e DuckDB não foram escolhidos como destino obrigatório.

Em 30/09/2026, o usuário aprovou exemplos reais de margem bruta, bicicletas e acessórios, com continuidade da conversa e gráficos. Isso valida a experiência observada, não todas as afirmações da IA. Consulte o [checkup](docs/checkup-2026-09-30.md), o [plano de desenvolvimento](docs/desenvolvimento.pt-BR.md) e o [guia dos testes](tests/README.md).
