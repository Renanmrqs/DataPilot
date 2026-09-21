# DataPilot

A learning and portfolio project combining a standalone analytics portal with an AI assistant for business questions.

**Status: local prototype.** The interface is in Brazilian Portuguese and runs outside Qlik Sense. Visual design and the analysis experience still need refinement.

**Guides:** [Português](docs/prototype.pt-BR.md) · [English](docs/prototype.md) · [Technical analysis flow](docs/business-analysis.md)

## What works today

- Validated loading of six CSV datasets into SQLite.
- A web overview with filters, sales KPIs and charts.
- Business questions mapped to approved panels for sales, average order value, gross margin and products.
- SQL/Python calculates the values; an optional AI provider selects the analysis plan and explains the results.
- Configurable providers and models, including Gemini, DeepSeek, OpenAI and compatible endpoints.
- A calculated panel remains available if its AI explanation fails.

The customer asks a business question, rather than specifying chart types. Current panels use predefined layouts; unrestricted dashboard generation and conversation memory are not implemented.

## Run locally

From the repository root in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.etl.build_database
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Create the virtual environment only if it does not exist. Open http://127.0.0.1:8000.
Stop the server before rebuilding the database on Windows.

AI is optional: copy [.env.example](.env.example) to `.env`, configure credentials and model IDs locally, and restart the server. Never commit credentials. See the guides for setup and limitations.

## How it fits together

```text
Source CSVs -> validated Python load -> SQLite -> FastAPI -> web portal
                                                   |
Business question -> approved AI plan -> calculated KPIs/charts -> AI explanation
```

| Location | Responsibility |
|---|---|
| `src/etl/build_database.py` | Validate and load original CSVs |
| `sql/schema.sql` | Relational tables, constraints and sales view |
| `src/api/` | HTTP routes and analysis orchestration |
| `src/analytics/` | Approved metrics, queries and panel recipes |
| `src/ai/` | Provider requests and validated analysis plans |
| `src/web/` | Portuguese interface and chart rendering |
| `tests/` | Data, API and mocked AI regression tests |
| `docs/` | Setup, metric definitions and known limitations |

SQLite supports the current local setup. PostgreSQL is a planned migration, not a current dependency. The older `transform_sales.py` script is separate from the prototype database load.

## Correctness and limits

Orders count distinct sales orders, not rows. Average order value uses selected revenue divided by distinct selected orders. Gross profit subtracts product cost and is not net profit. Source currency has not been identified beyond its dollar symbol.

The loader checks keys, relationships, dates and monetary values, then reconciles totals before replacing the database. AI uses validated aggregates and cannot execute arbitrary SQL; it can still misunderstand a question or invent a textual explanation.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Automated provider tests use mocks. A live Gemini analysis completed after a transient service failure; that does not establish reliability across providers or questions.

This is a single-user local prototype without authentication or production deployment. Supported data covers sales-related questions, not every department. Each question is independent. A supported analysis normally has two AI stages; a transient failure can trigger one retry per stage. Provider usage and account limits apply.

## Next refinement

1. Improve chart readability, labels, spacing and the visual hierarchy of the portal.
2. Refine how questions, answers and related panels fit together.
3. Evaluate representative questions across configured providers against the calculated values.
4. Keep changes small, understandable and verifiable before expanding the supported data.

The product direction is **chat + an analytics portal outside BI**, sharing the same validated metric layer.
