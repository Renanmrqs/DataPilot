# DataPilot

**Português** · [English](README.en.md)

### Análise de vendas com dados, contexto e IA.

Um painel para explorar indicadores de vendas e um assistente para fazer perguntas em linguagem natural. Os números são calculados pela aplicação; a IA organiza a análise e explica os resultados.

**[Abrir a demonstração →](https://data-pilot-neon.vercel.app/)** · [Executar localmente](#executar-localmente) · [Documentação](#documentação)

Projeto pessoal de estudo e portfólio, desenvolvido com auxílio de IA. O objetivo é conectar análise de dados, desenvolvimento web e engenharia de software em uma aplicação utilizável, com decisões técnicas e limitações documentadas. A interface está em português brasileiro.

## Demonstração

**Demo publicada na Vercel, com fluxo completo de acesso e análise confirmado pelo autor em 23/10/2026.** O problema anterior na solicitação de e-mail foi resolvido ao cadastrar novamente a origem no Neon Auth sem a barra final.

1. Abra o site e explore o painel e seus filtros.
2. Na seção do assistente, solicite um link de acesso por e-mail.
3. Abra o link no mesmo navegador e faça uma pergunta sobre os dados.
4. Leia a resposta e abra os gráficos para explorar os resultados.

A demo usa uma base estática de exemplo. O painel pode ser explorado sem login; a IA exige acesso confirmado e saldo. Por padrão, são **4 perguntas por conta**, com limite compartilhado de **20 perguntas por dia UTC** e intervalo de **15 segundos** entre perguntas. Esses valores são configuráveis.

As opções de IA dependem da configuração e da disponibilidade dos provedores. A validação do fluxo completo não significa que todos os modelos ou todas as perguntas foram validados.

## Veja o projeto

### Painel de vendas

Visão geral dos indicadores, filtros e evolução das vendas.

![Painel de vendas do DataPilot com indicadores e filtros](docs/images/dashboard.png)

### Assistente de análise

Pergunta em linguagem natural, resposta do assistente e gráficos com os dados da seleção.

![Assistente do DataPilot com resposta e gráficos da análise](docs/images/assistant.png)

## O que você pode fazer

- Filtrar vendas por período, canal e categoria.
- Acompanhar receita, pedidos distintos, ticket médio, unidades, custo e margem bruta.
- Perguntar sobre vendas, margem, ticket e produtos em linguagem natural.
- Explorar indicadores e gráficos selecionados entre opções permitidas pela aplicação.
- Continuar uma conversa com contexto das últimas quatro trocas e dos filtros da análise anterior.
- Consultar os indicadores calculados mesmo quando a etapa de explicação da IA falhar.
- Entrar por link de e-mail e manter o saldo da conta ao recarregar a página.

**Nova conversa**, alterações nos filtros ou recarga da página limpam o histórico em memória. O saldo da conta permanece no servidor; trocar de provedor não renova a cota. Uma falha após a reserva de saldo pode consumir a pergunta.

## Como funciona

```text
6 CSVs → carga e validação em Python → SQLite somente leitura
                                              ↓
                                   FastAPI → interface web

Pergunta → plano da IA validado → métricas em SQL/Python → explicação da IA

Neon Auth → identidade confirmada → PostgreSQL no Neon → controle de cotas
```

A IA propõe um plano dentro de um contrato validado. A aplicação executa as consultas permitidas e calcula as métricas; não há execução de SQL livre gerado pelo modelo. Filtros, opções disponíveis e agregados são enviados ao provedor conforme a etapa da análise.

O SQLite armazena os dados analíticos e é reconstruído a partir dos CSVs durante o build na Vercel. A autenticação e as cotas usam o Neon; o saldo não depende dos arquivos locais do deploy.

| Camada | Tecnologias |
| --- | --- |
| Dados e métricas | Python, pandas, SQL e SQLite |
| API | FastAPI e Pydantic |
| Interface | HTML, CSS e JavaScript |
| Acesso e cotas | Neon Auth e PostgreSQL |
| IA | APIs configuráveis, incluindo endpoints compatíveis com Chat Completions |
| Hospedagem | Vercel |

## Executar localmente

Requisitos: **Python 3.12–3.14**, Git e um terminal. Execute os comandos na raiz do repositório.

### Linux / macOS — Bash ou Zsh

```bash
git clone https://github.com/Renanmrqs/DataPilot.git
cd DataPilot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.etl.build_database
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

### Windows — PowerShell

```powershell
git clone https://github.com/Renanmrqs/DataPilot.git
cd DataPilot
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.etl.build_database
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Abra **[http://127.0.0.1:8000](http://127.0.0.1:8000)**. A documentação interativa da API fica em [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Se já clonou o projeto, comece na pasta existente e crie o `.venv` apenas se necessário. Após um `git pull`, instale novamente o `requirements.txt` para incluir novas dependências. No Windows, pare o servidor antes de reconstruir o banco.

### Configurar a IA

O painel funciona sem credenciais de IA. Para habilitar o assistente:

1. Copie [.env.example](.env.example) para `.env`.
2. Preencha as credenciais e os identificadores de modelos do provedor escolhido.
3. Reinicie o servidor.

Gemini, DeepSeek, OpenAI e outros endpoints compatíveis são configuráveis. A integração com **Groq** usa o identificador interno `deepseek`, com `DEEPSEEK_BASE_URL` apontando para a Groq; a interface identifica o provedor pelo endpoint.

O `.env` não é versionado e não vem no `git pull`. Mantenha as credenciais privadas. O modo local normal dispensa login e cotas da demo, mas chamadas reais consomem a franquia do provedor; esse modo se destina ao uso local.

### Executar com login e cotas

Configure Neon Auth, a conexão PostgreSQL, as tabelas de cotas e o provedor conforme o [guia de acesso](docs/demo-access.pt-BR.md). Depois, com o ambiente virtual ativo:

```bash
python -B -m scripts.run_demo
```

No PowerShell, use `.\.venv\Scripts\python.exe -B -m scripts.run_demo`. A variável `DEMO_AI_ENABLED=false` mantém o chat pausado.

## Publicação na Vercel

O [guia de publicação](docs/deployment.pt-BR.md) detalha o deploy. A configuração FastAPI fica no `pyproject.toml`, com dependências registradas também no `uv.lock`.

As variáveis locais precisam ser cadastradas separadamente na Vercel. No Neon Auth, autorize a origem exata do site, **sem barra final, caminho ou fragmento**:

```text
https://data-pilot-neon.vercel.app
```

URLs de preview são origens diferentes. Após alterar variáveis de ambiente na Vercel, faça um novo deploy. Os guias e checkpoints contêm registros históricos; o status atual da demo está neste README.

## Métricas e limites

| Métrica | Definição |
| --- | --- |
| Pedidos | Contagem distinta de pedidos na seleção |
| Ticket médio | Receita selecionada ÷ pedidos distintos selecionados |
| Lucro bruto | Receita − custo dos produtos |
| Margem bruta | Lucro bruto ÷ receita, quando definida |

Valores monetários são armazenados em centavos. O símbolo `$` vem da fonte; a moeda não foi confirmada. Lucro bruto não inclui despesas operacionais e não representa lucro líquido.

A carga verifica chaves, relacionamentos, datas, valores e reconciliação de totais antes de substituir o banco. A base não representa uma integração com empresas reais. Meses parciais e ausência de referências de comparação ou dados causais limitam as conclusões.

As explicações da IA podem conter erros, mesmo com métricas calculadas pela aplicação. Integração com QVD, configuração por cliente e isolamento entre clientes ainda não estão implementados.

## Testes

Com o ambiente virtual ativo:

```bash
python -B -m unittest discover -s tests -v
```

No PowerShell, use `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v`.

A suíte padrão usa bases temporárias e provedores simulados, sem chamadas reais de IA. Testes de PostgreSQL são opcionais. Verificações de interface e chamadas reais têm procedimentos separados no [guia de testes](tests/README.md).

## Organização do código

| Local | Responsabilidade |
| --- | --- |
| `data/raw/` | CSVs da demonstração |
| `src/etl/` e `sql/schema.sql` | Carga validada e modelo relacional |
| `src/analytics/` | Métricas e consultas determinísticas |
| `src/ai/` | Provedores e validação dos planos de análise |
| `src/api/` | Rotas, autenticação e coordenação da análise |
| `src/demo/` | Configuração, identidade e cotas persistentes |
| `src/web/` | Interface e gráficos |
| `tests/` e `scripts/` | Testes e utilitários |
| `docs/` | Guias técnicos, decisões e checkpoints |

## Próximos passos

- Melhorar as mensagens de erro e a observabilidade do fluxo de acesso e IA.
- Ampliar os exemplos e as verificações das respostas dos modelos.
- Evoluir as análises e comparações entre períodos.
- Investigar o reaproveitamento de dados tratados no Qlik Sense, com métricas e relacionamentos explícitos por base.

Esses itens são direções de evolução, não funcionalidades disponíveis. Ler QVDs não reproduz automaticamente as medidas e associações de um aplicativo Qlik.

## Documentação

- [Guia do protótipo](docs/prototype.pt-BR.md)
- [Acesso, autenticação e cotas](docs/demo-access.pt-BR.md)
- [Publicação na Vercel](docs/deployment.pt-BR.md)
- [Fluxo técnico de análise — English](docs/business-analysis.md)
- [Desenvolvimento e aprendizado](docs/desenvolvimento.pt-BR.md)
- [Testes e validação](tests/README.md)
