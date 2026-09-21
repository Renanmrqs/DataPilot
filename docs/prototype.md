# Local prototype

[Versão em português](prototype.pt-BR.md) · [Project overview](../readme.MD)

## Run

From the repository root in PowerShell:

```powershell
# First setup, if .venv does not exist:
py -m venv .venv

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.etl.build_database
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. API documentation: http://127.0.0.1:8000/docs.
Stop the server with Ctrl+C. The dashboard uses no external fonts, chart libraries or network services.
The database load reads the original CSVs directly; the older processed sales CSV is not required.
Stop the server before rebuilding the database, to avoid file locks on Windows.

## Scope and architecture

`Original CSVs -> validated Python load -> SQLite -> FastAPI -> local HTML/CSS/JavaScript dashboard`

The first demonstration must run outside Qlik. SQLite allows a local prototype without a database service.
PostgreSQL remains a future migration; this version is a local, single-user demonstration, with no authentication or deployment setup.
The overview covers fixed sales questions. The assistant now selects approved topic panels from business questions; see [business-question analysis](business-analysis.md). The planner now selects allowlisted charts per question and receives the last four exchanges; see [conversational analysis](conversation.md). Arbitrary chart generation remains outside the scope.

Implemented:
- Six source datasets loaded into related tables with primary and foreign key constraints.
- Filtered revenue, distinct orders, units, average order value, gross profit and gross margin.
- Monthly revenue and category revenue, with inclusive order-date, channel and category filters.
- An accessible monthly values table, loading/error/empty states, and API documentation.
- A deterministic summary clearly labeled as calculated, with optional AI interpretation through configurable providers.

## Data model

Sales grain: one order item, identified by `order_line_key`.
Each sales item references one product, customer, reseller, territory and order-line detail.
`order_number` may repeat across items and is used for distinct order counts.
Dimensions keep the fields needed for this prototype; original CSVs retain all attributes.
Customer and reseller key `-1` is preserved; its business meaning is not inferred.
SKU is not a primary key because the source contains repeated SKUs.

See [schema](../sql/schema.sql).
SQLite date columns contain validated ISO date strings. Monetary columns contain integer cents.
A failed load does not publish its temporary database over a previously successful load.

## Metric definitions

| Metric | Definition |
|---|---|
| Revenue | Sum of source Sales Amount |
| Orders | Distinct Sales Order values among selected items |
| Units | Sum of Order Quantity |
| Average order value | Selected revenue / selected distinct orders |
| Gross profit | Revenue minus source Total Product Cost |
| Gross margin | Gross profit / revenue x 100 |

Revenue and cost are independently rounded in the original data; use their recorded values rather than reconstructing them from unit prices.
Gross profit is not net profit: operating expenses and taxes are not available.
The source uses a dollar sign; a currency code has not been established.
When filtering categories, average order value reflects selected items, not each order's full basket.
Ratios with a zero denominator return null and appear as a dash.
Monthly groups contain observed months only; date filters can produce partial first and last months.
The current chart is designed for this positive-sales dataset; returns and multi-currency data are outside the reviewed scope.

## Validation

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

The loader validates keys, relationships, monetary precision, discount bounds, dates and positive quantities.
It reconciles joined row counts, revenue and cost to the parsed source records before publishing.
These checks do not establish that all source business definitions are correct.
The loader stores its report inside the database, exposed through `/api/metadata`.

Reference totals from the current source:
- 121,253 sales items; 31,455 distinct orders; 274,776 units.
- Revenue: 109,809,274.00; product cost: 97,257,988.07.
- Gross profit: 12,551,285.93; gross margin: approximately 11.4301%.
- Order dates: 2021-07-01 through 2024-06-15.
- 2,113 missing shipping dates, intentionally preserved.

API tests use a small independent fixture with two orders and three lines.
They check exact expected metrics, combined filters, inclusive dates, empty selections,
invalid inputs, missing databases and database constraints.
Serving HTML successfully is not a browser rendering test.

## Remaining prototype validation

- [x] Local database, API and fixed dashboard implemented.
- [x] Metric definitions and reproducible startup commands documented.
- [x] Check the page in Chrome, including narrow screens and filter interactions.
- [x] Configure providers locally and complete a live Gemini analysis; credentials remain outside Git.
- [x] Add configurable AI interpretation over validated aggregates, with missing-key and provider-error states.
- [ ] Test that explanations retain metric values and do not invent causes.
- [ ] Refine chart readability and the combined chat/portal experience.

Suggested manual verification:
1. Show the full-period totals and metric definitions.
2. Select Internet sales and a date range; show the charts updating.
3. Filter a category and explain the resulting average order value.
4. Show the API response and data validation report.
5. With a configured provider, ask the AI to explain this exact selection and compare a second model.

Technical references: [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/) and
[FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/).

## Configure and compare AI providers

Copy `.env.example` to `.env` and fill only the providers you want to use.
For each provider, set its `*_API_KEY` and comma-separated `*_MODELS` list.
Use exact model IDs available to your account. Restart the server after changes.
The model list is user-configured, not fetched automatically.

Example configuration shape (replace placeholders locally):

```dotenv
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODELS=first_model_id,second_model_id
GEMINI_API_KEY=your_key_here
GEMINI_MODELS=your_model_id
```

DeepSeek, Gemini and OpenAI have predefined endpoints. Other Chat Completions-compatible
providers can use `COMPATIBLE_BASE_URL`, `COMPATIBLE_API_KEY` and `COMPATIBLE_MODELS`.
This shared adapter uses basic text completion features, not provider-specific tools.
Some model-specific request formats may require another adapter.

Use the provider and model selectors in the copilot. Ask the same question without changing filters.
Responses remain in the page with provider, model, latency and a context identifier.
Changing filters clears responses; reloading the page clears the comparison.
The server rebuilds metrics for every question rather than accepting client-provided totals.
The context identifier hashes the supplied metrics, not the question, and helps identify equivalent data inputs.
The request sends only the question, aggregate metrics, filters and metric definitions.
No CSV upload, customer names, repository files or planning documents are sent.

Provider requests occur only when the user clicks Analisar pergunta and can incur provider charges.
An unconfigured provider leaves analytics usable and does not generate a fake response.
Timeouts, missing configuration, invalid models and upstream errors have explicit messages.
The model is instructed to preserve values and avoid invented causes; this is not a guarantee.
Compare each live response against the visible metrics before relying on it.

Automated AI tests use HTTP mocks, not live model calls. A live Gemini business-question analysis completed after recovering from one HTTP 503. Broader compatibility and factual quality still need evaluation.

A supported question normally uses two AI stages: planning and explanation. Selected transient server failures allow one retry per stage; rate-limit responses are not automatically retried. An incomplete explanation is reported as unavailable while the calculated panel remains visible.

References: [DeepSeek API](https://api-docs.deepseek.com/),
[Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai),
[OpenAI Chat Completions](https://developers.openai.com/api/reference/cli/resources/chat/subresources/completions).
