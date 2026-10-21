# DataPilot

[Português](readme.MD) | **English**

A sales analytics portal with an AI assistant: ask a business question, read the answer, and optionally open charts to explore the numbers.

A personal learning and portfolio project developed with AI assistance. The goal is to build a usable application and understand its engineering decisions, with deterministic metric calculations and documented limitations. The application interface is in Brazilian Portuguese.

## Project status

**Working local prototype; deployment validation in progress.**

| Component | Status on October 21, 2026 |
| --- | --- |
| CSV loading, API, filters, KPIs and charts | Implemented and checked locally |
| Groq chat with a Qwen model | Answer and charts confirmed locally by the user |
| Gemini | One complete live API analysis passed, but planning failed again in the browser; unresolved |
| Email-link login and persistent balance | Validated locally with Neon |
| Vercel | Build and deployment completed; requesting an access email fails on the deployed site |

The complete authentication and AI flow on Vercel **has not been validated**. Provider availability and the accuracy of generated explanations are not guaranteed.

## Features

- Sales overview with date, channel and category filters.
- Revenue, distinct orders, average order value, units, cost and gross margin.
- Sales, order-value, margin and product questions, with KPIs and charts selected from approved options.
- Answers shown before optional charts.
- Context from the last four exchanges and previous analysis filters. **Nova conversa**, filter changes or a reload clear the in-memory history.
- Calculated panels remain available if the explanation stage fails.
- Configurable providers and models; server-approved choices in demo mode.
- Email access, four questions per account by default, a shared daily cap and a per-account cooldown.

## Architecture

```text
6 CSVs → validated Python load → read-only SQLite
                                       ↓
                               FastAPI → web interface

Question → validated AI plan → SQL/Python metrics → AI explanation

Neon Auth → verified identity → Neon PostgreSQL → quota reservation
```

AI selects an analysis through a validated contract; it cannot execute arbitrary SQL. The application calculates the numbers. Filters, available options and aggregates are sent to the provider as needed for each stage; textual explanations can still be wrong.

SQLite stores the demonstration analytics dataset. Neon PostgreSQL stores authentication data and quotas. Vercel rebuilds SQLite from versioned CSVs during the build; account balances do not depend on local files.

**Stack:** Python, FastAPI, SQLite, PostgreSQL/Neon Auth, HTML, CSS and JavaScript, with Chat Completions-compatible AI APIs.

## Run locally

Requirements: Python 3.12–3.14 and a terminal. From the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.etl.build_database
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive API documentation is available at `/docs`.

Create the virtual environment only if it does not already exist. The dashboard works without an AI provider. Stop the server before rebuilding SQLite on Windows.

### Configure AI

Copy [.env.example](.env.example) to `.env`, enter credentials and model identifiers, and restart the server. Never commit `.env`.

Gemini, DeepSeek, OpenAI and other compatible endpoints are configurable. The working local configuration uses **Groq with Qwen** through the internal `deepseek` identifier, with `DEEPSEEK_BASE_URL` pointing to Groq. The variable name does not mean requests go to DeepSeek; the interface displays Groq when that endpoint is used.

Normal local mode does not require authentication or enforce demo quotas. Real calls still consume provider allowance. Do not expose this mode as a public service.

### Run the protected demo

After configuring Neon Auth, the PostgreSQL connection, quota tables and a provider following the [access guide](docs/demo-access.md):

```powershell
.\.venv\Scripts\python.exe -B -m scripts.run_demo
```

This mode requires a verified identity and available balance for AI requests. `DEMO_AI_ENABLED=false` pauses chat. The default allowance is **4 questions per account**, without renewal on reload or a new conversation. There is also a **20-question shared daily cap (UTC)** and a **15-second per-account cooldown**, configurable on the server.

Balance is reserved before calling AI; a later failure can consume the question. Both providers share the same balance. A question can involve planning, explanation and HTTP retries, so it does not correspond to a single provider call.

## Deployment

The repository includes Vercel FastAPI configuration and dependencies in `pyproject.toml` and `uv.lock`. Local `.env` values must be configured separately in Vercel. The production origin must be authorized in Neon Auth.

See the [deployment walkthrough — Portuguese](docs/deployment.pt-BR.md). The remote build completed, but requesting an access email on the deployed site remains unresolved; local success does not establish production readiness.

## Metrics and limitations

| Metric | Definition |
| --- | --- |
| Orders | Distinct sales orders in the selection, not row count |
| Average order value | Selected revenue ÷ distinct selected orders |
| Gross profit | Revenue − product cost |
| Gross margin | Gross profit ÷ revenue, where defined |

Monetary values are stored in cents. The source uses `$`; the currency has not been confirmed. Gross profit excludes operating expenses and is not net profit.

The loader checks keys, relationships, dates, values and total reconciliation before replacing the database. The dataset is a static sales example, not an integration with actual companies. Partial months, missing benchmarks and absent causal data limit conclusions.

AI cannot run freely generated SQL, but it can misunderstand questions or make unsupported statements. QVD ingestion, per-client configuration and client isolation are not implemented.

## Verification

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Last recorded run: **65 tests passed and 3 optional PostgreSQL tests were skipped**. Standard provider tests use simulated responses. UI checks cover login, quotas, failures and mobile layouts; real provider checks are separate and consume allowance. A successful real example does not establish accuracy across all questions.

## Repository layout

| Location | Responsibility |
| --- | --- |
| `data/raw/` | Source CSVs for the demonstration |
| `src/etl/` and `sql/schema.sql` | Validated loading and relational schema |
| `src/analytics/` | Deterministic metrics and queries |
| `src/ai/` | Provider integration and analysis-plan validation |
| `src/api/` | Routes, authentication and analysis orchestration |
| `src/demo/` | Identity, configuration and persistent quotas |
| `src/web/` | Brazilian Portuguese interface and charts |
| `tests/` and `scripts/` | Tests and execution/verification utilities |
| `docs/` | Technical guides, decisions and historical checkpoints |

## Documentation and direction

- [Prototype guide](docs/prototype.md) · [Português](docs/prototype.pt-BR.md)
- [Access, authentication and quotas](docs/demo-access.md) · [Português](docs/demo-access.pt-BR.md)
- [Vercel deployment — Portuguese](docs/deployment.pt-BR.md)
- [Technical analysis flow](docs/business-analysis.md)
- [Development and learning guide — Portuguese](docs/desenvolvimento.pt-BR.md)
- [Tests](tests/README.md) · [October 21 diagnosis](docs/checkpoint-2026-10-21.md)

Checkpoints describe individual sessions and may contain superseded statements. This README summarizes the current status.

The next objective is to validate authentication and AI on the deployed site and finish a reliable demo. Future work aims to reuse data prepared in Qlik Sense, with explicit metrics and relationships per dataset. Reading QVDs does not automatically reproduce Qlik application measures or associations and is not currently implemented.
