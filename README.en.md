# DataPilot

**October 21, 2026 checkpoint:** demo login confirmed and a complete live API analysis validated with Gemini 2.5 Flash. User-browser verification and deployment remain pending. [Diagnosis and next steps](docs/checkpoint-2026-10-21.md).

Public demo preparation: [email authentication and persistent question quotas](docs/demo-access.md). UI and quota controls are implemented; real email delivery, browser authentication and Vercel deployment still require validation. Public AI is paused by default.

[Português](readme.MD) | **English**

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

The customer asks a business question, rather than specifying chart types. The assistant selects allowlisted charts and KPIs for each question. Optional charts follow the answer; the last four exchanges and previous analysis filters provide conversation context.

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

SQLite supports the current local setup. PostgreSQL is not a required migration or a committed next step. The older `transform_sales.py` script is separate from the prototype database load.

## Correctness and limits

Orders count distinct sales orders, not rows. Average order value uses selected revenue divided by distinct selected orders. Gross profit subtracts product cost and is not net profit. Source currency has not been identified beyond its dollar symbol.

The loader checks keys, relationships, dates and monetary values, then reconciles totals before replacing the database. AI uses validated aggregates and cannot execute arbitrary SQL; it can still misunderstand a question or invent a textual explanation.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Automated provider tests use mocks. A live Gemini analysis completed after a transient service failure; that does not establish reliability across providers or questions.

This is a single-user local prototype without authentication or production deployment. Supported data covers sales-related questions, not every department. Recent conversation context is kept in browser memory. A supported analysis normally has two AI stages; a transient failure can trigger one retry per stage. Provider usage and account limits apply.

## Next steps: reuse prepared QVDs

1. Separate data access from analysis planning, calculation and rendering.
2. Configure fields, keys, relationships and metrics per dataset.
3. Prove reuse with a second prepared test dataset, preserving chat and charts.
4. Evaluate QVD ingestion and reconcile metrics against the Qlik application before a real-client pilot.

The agreed direction is **sources → transformations in Qlik Sense → prepared QVDs → DataPilot → dashboard + AI**. Business transformations remain in Qlik. Application measures must be mapped; QVD ingestion does not automatically reproduce Qlik expressions or associations.

The implementation still uses CSV/SQLite. QVD ingestion, per-client configuration and client isolation are not implemented. Neither PostgreSQL nor DuckDB is a mandatory destination.

On 2026-09-30, the user approved live examples covering gross margin, Bikes and Accessories, with contextual answers and charts. This validates those interactions, not general model accuracy. See the [checkup](docs/checkup-2026-09-30.md), [development plan](docs/desenvolvimento.pt-BR.md) and [test guide](tests/README.md), in Portuguese.
