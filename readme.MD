# DataPilot

**Português** | [English](README.en.md)

Portal de análise de vendas com um assistente de IA: faça uma pergunta sobre o negócio, leia a resposta e abra os gráficos quando quiser explorar os números.

Projeto pessoal de estudo e portfólio, desenvolvido com auxílio de IA. O foco é aprender a construir uma aplicação utilizável e compreender suas decisões técnicas, com métricas calculadas de forma determinística e limitações documentadas. A interface está em português brasileiro.

## Estado do projeto

**Protótipo funcional localmente; publicação em validação.**

| Componente | Situação em 21/10/2026 |
| --- | --- |
| Carga dos CSVs, API, filtros, indicadores e gráficos | Implementados e verificados localmente |
| Chat com Groq e modelo Qwen | Resposta e gráficos confirmados pelo usuário localmente |
| Gemini | Uma análise completa pela API foi validada, mas houve nova falha de planejamento no navegador; problema em aberto |
| Login por link de e-mail e saldo persistente | Validados localmente com Neon |
| Vercel | Build e publicação concluídos; solicitação do link de acesso falha no ambiente publicado |

O fluxo completo de autenticação e IA na Vercel **ainda não está validado**. Não há garantia de disponibilidade dos provedores nem de exatidão das explicações geradas.

## Funcionalidades

- Painel de vendas com filtros de período, canal e categoria.
- Receita, pedidos distintos, ticket médio, unidades, custo e margem bruta.
- Perguntas sobre vendas, ticket, margem e produtos, com seleção de indicadores e gráficos entre opções permitidas.
- Resposta antes dos gráficos, que podem ser abertos opcionalmente.
- Contexto das últimas quatro trocas e dos filtros da análise anterior. **Nova conversa**, alteração dos filtros ou recarga limpam o histórico em memória.
- Painel calculado preservado se a etapa de explicação da IA falhar.
- Provedores e modelos configuráveis; modo de demonstração com opções aprovadas pelo servidor.
- Acesso por e-mail, quatro perguntas por conta por padrão, cota diária global e intervalo entre perguntas.

## Arquitetura

```text
6 CSVs → carga e validação em Python → SQLite somente leitura
                                              ↓
                                  FastAPI → interface web

Pergunta → plano da IA validado → métricas em SQL/Python → explicação da IA

Neon Auth → identidade confirmada → PostgreSQL no Neon → reserva de saldo
```

A IA escolhe uma análise dentro de um contrato validado; ela não executa SQL arbitrário. Os números são calculados pelo sistema. Filtros, opções disponíveis e agregados são enviados ao provedor conforme a etapa; a explicação textual ainda pode conter erros.

O SQLite guarda a base analítica de demonstração. O PostgreSQL do Neon guarda autenticação e cotas. Na Vercel, o SQLite é recriado durante o build a partir dos CSVs versionados; o saldo não depende de arquivos locais.

**Stack:** Python, FastAPI, SQLite, PostgreSQL/Neon Auth, HTML, CSS e JavaScript, com APIs de IA compatíveis com Chat Completions.

## Executar localmente

Requisitos: Python 3.12–3.14 e acesso ao terminal. Exemplo para PowerShell, na raiz do repositório:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.etl.build_database
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000). A documentação interativa da API fica em `/docs`.

Crie o ambiente virtual somente se ainda não existir. O painel funciona sem provedor de IA. No Windows, pare o servidor antes de reconstruir o banco.

### Configurar IA

Copie [.env.example](.env.example) para `.env`, preencha as credenciais e os identificadores dos modelos e reinicie o servidor. Não inclua `.env` em commits.

Gemini, DeepSeek, OpenAI e outros endpoints compatíveis são configuráveis. A configuração local que funcionou usa **Groq com Qwen** no identificador interno `deepseek`, com `DEEPSEEK_BASE_URL` apontando para a Groq. O nome do campo não significa que a requisição vai para a DeepSeek; a interface mostra Groq quando esse endpoint é usado.

O modo local normal não exige autenticação nem aplica cotas da demo. Chamadas reais continuam consumindo a franquia do provedor. Não exponha esse modo como serviço público.

### Executar a demo protegida

Após configurar Neon Auth, a conexão PostgreSQL, as tabelas de cotas e o provedor conforme o [guia de acesso](docs/demo-access.pt-BR.md):

```powershell
.\.venv\Scripts\python.exe -B -m scripts.run_demo
```

Nesse modo, a IA exige identidade confirmada e saldo. `DEMO_AI_ENABLED=false` pausa o chat. A cota padrão é de **4 perguntas por conta**, sem renovação ao recarregar ou iniciar outra conversa. Há também um limite global de **20 perguntas por dia UTC** e intervalo de **15 segundos** por conta, configuráveis no servidor.

O saldo é reservado antes de chamar a IA; uma falha posterior pode consumir a pergunta. Trocar de provedor compartilha o mesmo saldo. Uma pergunta pode envolver planejamento, explicação e novas tentativas HTTP, portanto não equivale a uma única chamada de IA.

## Publicação

O projeto tem configuração FastAPI para Vercel e dependências registradas em `pyproject.toml` e `uv.lock`. As variáveis do `.env` local devem ser cadastradas separadamente na Vercel. O domínio de produção precisa ser autorizado no Neon Auth.

Veja o [passo a passo de publicação](docs/deployment.pt-BR.md). O build remoto foi concluído, mas a falha de solicitação de e-mail no site publicado continua pendente; o funcionamento local não comprova o fluxo em produção.

## Métricas e limites

| Métrica | Definição |
| --- | --- |
| Pedidos | Contagem distinta de pedidos na seleção, não quantidade de linhas |
| Ticket médio | Receita selecionada ÷ pedidos distintos selecionados |
| Lucro bruto | Receita − custo dos produtos |
| Margem bruta | Lucro bruto ÷ receita, quando definida |

Valores monetários são armazenados em centavos. O símbolo `$` vem da fonte; a moeda não foi confirmada. Lucro bruto não inclui despesas operacionais e não representa lucro líquido.

O carregamento verifica chaves, relacionamentos, datas, valores e reconciliação de totais antes de substituir o banco. Os dados são uma base estática de exemplo de vendas, não uma integração com empresas reais. Meses parciais, ausência de benchmarks e falta de dados causais limitam as conclusões.

Não há execução de SQL gerado livremente pela IA, mas ela pode interpretar mal uma pergunta ou fazer afirmações sem suporte. Integração com QVD, configuração por cliente e isolamento entre clientes ainda não estão implementados.

## Verificação

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Última execução registrada: **65 testes aprovados e 3 testes opcionais de PostgreSQL pulados**. Os testes comuns de provedores usam respostas simuladas. Verificações de interface cobrem login, saldo, falhas e telas móveis; chamadas reais são verificações separadas e consomem franquia. Um caso real bem-sucedido não garante precisão em todas as perguntas.

## Organização do código

| Local | Responsabilidade |
| --- | --- |
| `data/raw/` | CSVs de origem usados na demonstração |
| `src/etl/` e `sql/schema.sql` | Carga validada e modelo relacional |
| `src/analytics/` | Métricas e consultas determinísticas |
| `src/ai/` | Integração com provedores e validação dos planos |
| `src/api/` | Rotas, autenticação e coordenação da análise |
| `src/demo/` | Identidade, configuração e cotas persistentes |
| `src/web/` | Interface e gráficos em português brasileiro |
| `tests/` e `scripts/` | Testes e utilitários de execução/verificação |
| `docs/` | Guias técnicos, decisões e checkpoints históricos |

## Documentação e evolução

- [Guia do protótipo](docs/prototype.pt-BR.md) · [English guide](docs/prototype.md)
- [Acesso, autenticação e cotas](docs/demo-access.pt-BR.md) · [English](docs/demo-access.md)
- [Publicação na Vercel](docs/deployment.pt-BR.md)
- [Fluxo técnico de análise — English](docs/business-analysis.md)
- [Guia de desenvolvimento e aprendizado](docs/desenvolvimento.pt-BR.md)
- [Testes](tests/README.md) · [Diagnóstico de 21/10/2026](docs/checkpoint-2026-10-21.md)

Os checkpoints registram o estado de cada sessão; afirmações históricas podem ter sido superadas. A situação atual está resumida neste README.

O próximo objetivo é validar o login e a IA no ambiente publicado e concluir uma demo confiável. Como evolução futura, pretende-se reutilizar dados já tratados no Qlik Sense, com métricas e relacionamentos explícitos por base. A leitura de QVDs não reproduz automaticamente medidas e associações de um aplicativo Qlik e ainda não faz parte da implementação.
