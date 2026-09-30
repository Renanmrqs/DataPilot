# Conversational analysis

The interface sends at most four recent question/answer exchanges to the planner and interpreter. History is untrusted context, not a source of metric values. Every analysis recalculates values from the database.

The previous analysis filters are validated and reused until the new question overrides them. Changing overview filters, reloading the page or using **Nova conversa** clears the conversation. The history is held only in browser memory; recent questions and answers are sent to the selected provider, including when switching models.

The planner can select zero to three charts and zero to four KPIs from an allowlist. Dimensions include month, category, channel, country and product; product charts show at most ten products. SQL/Python computes the values. Older plans without explicit chart selections retain the recipe fallback.

Answers appear first. Charts open on demand without another provider request. Empty selections and answers without charts do not show a chart button. When an answer has KPIs but no charts, its calculated indicators appear directly below the answer, including if the AI explanation fails.

## Verification

Automated cases cover Bikes-only quantities and product rankings, follow-up filters, fresh calculation despite incorrect historical text, category changes, chartless answers, history bounds and invalid chart specifications.

On 2026-09-30, the user approved live examples explaining gross margin, detailing Bikes and switching to Accessories, with charts and visible category filters. These are user-reported observations, not a comprehensive model benchmark. See the [checkup](checkup-2026-09-30.md).

Continue evaluating short follow-ups such as “e por mês?” and checking effective filters. The model may still choose the wrong plan. There is no durable chat storage, product-level filter, arbitrary SQL generation or causal inference. Preserve this conversational behavior when adapting the data layer to prepared QVDs; that adapter is still planned.
