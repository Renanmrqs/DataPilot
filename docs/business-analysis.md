# Business-question analysis

## Purpose

Users ask a business question; they do not need to request a chart type.
The assistant selects an approved analysis layout, Python calculates its values,
and the interface shows related KPIs, charts and an AI interpretation.

This first version covers four topics in the sales dataset.
It is an extensible starting point, not support for every department or arbitrary datasets.

## Request flow

1. The browser sends the question, selected provider/model and current filters to `POST /api/analysis`.
2. The first model call selects a topic, breakdown and optional explicit filter overrides.
3. Pydantic validates that plan. It cannot contain SQL, custom metrics or executable code.
4. Python runs approved, parameterized SQL and builds the panel.
5. The second model call interprets the calculated aggregates.
6. The browser renders the panel and explanation using text nodes, not model-generated HTML.

Two model stages are used per supported question. Unsupported questions, clarification and
empty selections skip the interpretation call. Each stage retries once for HTTP 500/502/503/504, only when Retry-After is absent or at most two seconds. HTTP 429, invalid requests and authentication errors are not retried.
If interpretation fails, the calculated panel is returned with a clear partial-result message.

## File map

| File | Responsibility |
|---|---|
| `src/ai/analysis_plan.py` | Understand the question and validate the model's plan |
| `src/analytics/catalog.py` | Approved metrics and topic layouts |
| `src/analytics/analysis.py` | SQL queries, ratios, filters and chart values |
| `src/api/analysis.py` | Coordinate planning, calculations and interpretation |
| `src/ai/copilot.py` | Shared provider HTTP calls and interpretation |
| `src/web/analysis-panel.js` | Render cards, charts and exact-value tables |
| `src/web/analysis-panel.css` | Styles for these panels |
| `tests/test_analysis.py` | Known-value calculations and mocked-provider behavior |

The existing overview and `/api/copilot` endpoint remain available.
The page's assistant form now uses `/api/analysis`.

## Initial topics

| Topic | Cards | Charts |
|---|---|---|
| Sales | Revenue, orders, units | Monthly revenue, revenue by a selected dimension, monthly orders |
| Average order value | Average order value, revenue, orders, units per order | Monthly order value, order value by dimension, monthly units per order |
| Gross margin | Margin, gross profit, revenue, product cost | Monthly margin, margin by dimension, monthly gross profit |
| Products | Units, revenue, distinct products sold | Monthly units, revenue by dimension, up to 10 products by revenue or units |

Available breakdowns: category, channel and country.
The model chooses the main topic and useful breakdown. Chart types are determined by the layout.

## Example questions

- “Por que o ticket médio está tão alto nesta seleção?”
- “Como estão as vendas por país?”
- “Quais canais têm a menor margem?”
- “Quais produtos vendem mais unidades?”
- “Como foram as vendas pela internet em 2023?”
- “Como estão os salários?” — requires data outside the current dataset.

These are manual evaluation examples, not a claim of verified model accuracy.

## Filters and interpretation

Current filters apply unless the question explicitly changes them.
The model can propose ISO dates, category, channel and country filters.
Categorical values must exist in the database. Dates and date order are validated.
The response displays its effective scope; it does not silently modify the overview's filters.
A null override explicitly clears a filter.

Average order value uses distinct order numbers, not sales line counts.
Margin is calculated from total revenue and cost, not an average of row margins.
Category filters produce partial-basket order values.
Null ratios appear as a dash and are not plotted as zero.
Negative amounts and margins retain their sign in the charts.
Product ranking is limited to 10 entries, but the cards cover all selected products.

Patterns do not prove causes. A high/low question has no established benchmark
unless one is supplied and supported. The model is instructed to acknowledge that.
Monthly charts can include partial months and omit months without matching sales.

## Current boundaries

- One primary topic per request. Multi-topic questions should ask which to start with.
- Each request stands alone; previous conversation context is not sent.
- Stock, payroll, expenses, budgets and net profit are not present.
- Product-level filters and calculated previous-period comparisons are not implemented.
- Questions requiring unsupported data or filters should explain the limitation.
- Ambiguous periods should request clarification rather than silently invent dates.
- The model can still misinterpret a question or make an unsupported textual claim.
  Schema validation controls execution, not semantic correctness.

## Verification

Run `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v`.

Tests cover known metrics, weighted margins, distinct orders, ranking metrics,
filter overrides, cleared filters, empty data, invalid plans, unavailable data and
preservation of panels when the explanation provider fails.

The browser was checked using real database values and mocked AI responses for all
four layouts, including mobile width and clearing results after filter changes.
Initial verification used mocked providers. Subsequent live Gemini testing reproduced HTTP 503 and truncated output.
The Gemini 3/2.5 adapter now requests low reasoning effort and an output budget of at least 4,096 tokens.
This is a ceiling, not a fixed token charge. Explanations are requested in at most 200 words.
Truncated explanations are not presented as complete.
A live Gemini end-to-end ticket analysis subsequently completed: the explanation recovered from one HTTP 503,
returned finish_reason=stop and preserved the calculated panel. Service availability can still vary.
