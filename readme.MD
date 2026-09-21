# DataPilot

**Português** | [English](README.en.md)

Projeto de aprendizado e portfólio que combina um portal de análise independente com um assistente de IA para perguntas sobre o negócio.

**Estado atual: protótipo local.** A interface está em português brasileiro e funciona fora do Qlik Sense. O visual e a experiência de análise ainda precisam de refinamento.

**Guias:** [Protótipo em português](docs/prototype.pt-BR.md) · [Protótipo em inglês](docs/prototype.md) · [Fluxo técnico da análise — em inglês](docs/business-analysis.md)

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

O SQLite atende à execução local atual. A migração para PostgreSQL está planejada. O script antigo `transform_sales.py` é separado do carregamento do banco usado pelo protótipo.

## Validação e limites

A quantidade de pedidos usa a contagem distinta dos pedidos de venda. O ticket médio divide a receita selecionada pelos pedidos distintos da seleção. O lucro bruto desconta o custo dos produtos; despesas necessárias ao cálculo do lucro líquido não estão disponíveis. A moeda da fonte ainda não foi identificada além do símbolo de dólar.

O carregamento verifica chaves, relacionamentos, datas e valores monetários, depois confere os totais antes de substituir o banco. A IA usa dados agregados validados e não pode executar SQL arbitrário. Mesmo assim, pode interpretar uma pergunta incorretamente ou inventar uma explicação.

Para executar os testes:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Os testes automatizados dos provedores usam respostas simuladas. Uma análise real com Gemini foi concluída após uma falha temporária do serviço. Essa verificação não garante confiabilidade para todos os provedores ou perguntas.

Este é um protótipo local para um usuário, sem autenticação ou configuração de produção. A base atual cobre perguntas relacionadas a vendas. A conversa mantém contexto recente na memória do navegador. Uma análise suportada normalmente usa duas etapas de IA; uma falha temporária pode gerar uma nova tentativa por etapa. O uso está sujeito aos custos e limites da conta no provedor.

## Próximos refinamentos

1. Melhorar a legibilidade dos gráficos, os rótulos, os espaçamentos e a organização visual do portal.
2. Refinar como perguntas, respostas e painéis relacionados aparecem juntos.
3. Comparar perguntas representativas entre os provedores configurados, conferindo as respostas com os valores calculados.
4. Manter as mudanças pequenas, compreensíveis e verificáveis antes de ampliar os dados suportados.

A direção do produto é **chat + portal de análise fora do BI**, compartilhando as mesmas definições e cálculos validados de métricas.
