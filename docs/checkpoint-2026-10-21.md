# Checkpoint: Gemini analysis, October 21, 2026

## Outcome

The saved October 20 work was pushed to GitHub as commit `6829424`. The remaining Gemini problem was investigated through the full analysis API.

After the changes below, a real request returned **HTTP 200, `status: complete`, a calculated panel, four KPIs and a completed explanation** using `gemini-2.5-flash`. The user still needs to restart their existing local server and verify the response in their own browser. This is one successful live case, not a model benchmark or evidence of uninterrupted provider availability.

## Findings

- Local configuration was already selecting Gemini, not DeepSeek. The endpoint was Google's official `generativelanguage.googleapis.com` host.
- `gemini-3.8-flash` metadata was available, but generation failed with HTTP 503. A minimal native `generateContent` request also returned `UNAVAILABLE` with a high-demand message. This was not fixed by changing local credentials or browser sessions.
- A real planning attempt using Gemini 2.5 Flash reproduced local schema rejection with `string_too_long`, even though the response was JSON and not truncated. The exact field was not captured in that failing attempt; the subsequent diagnostic passed. Do not claim the original output was fully recovered.
- The planning prompt previously used pipe-separated alternatives inside an example JSON string. It also did not explicitly require an empty `message` for supported analyses. These were ambiguous generation instructions.

## Changes

- Gemini planning requests now include `response_format: json_schema`, generated from the same `AnalysisPlan` Pydantic model used for local validation. Other providers retain their previous request format; explanation requests remain plain text.
- The example plan now contains actual allowed values. Enum choices are listed separately.
- Supported topics explicitly require `message: ""`; only unsupported/clarification may contain a brief message. The message field's schema description reiterates that the business explanation belongs to a separate call.
- Local validation remains strict. Unknown fields, invalid enum values, oversized messages and truncated output are still rejected. Invalid output does not trigger a new automatic planning call.
- The local demo now selects `gemini-2.5-flash`. It was added to `GEMINI_MODELS`, preserving the configured `gemini-3.8-flash` entry for comparison. Secrets and local selection remain in the ignored `.env`.
- Added an explicitly opt-in `scripts.check_live_analysis --live` diagnostic. It invokes the full analysis route in a separate in-process client and does not modify live server authentication or account quota counters.

## Evidence

Question: "Por que o ticket medio esta tao alto nesta selecao?"

Selection: July 1, 2021 through June 15, 2024, all channels/categories.

The successful run completed planning without truncation in approximately 7.4 seconds and explanation without truncation in approximately 10.4 seconds. The response included:

- Overall average selected revenue per order: $3,491.00.
- Reseller channel average: $21,193.52.
- Internet channel average: $1,061.45.

The two channel averages were independently recalculated in SQLite and matched the explanation's rounded values. This does not establish a benchmark for calling the ticket "high" or prove a cause. The explanation described the channel pattern rather than claiming causal proof.

Final automated suite: 67 tests discovered, 64 passed, three optional PostgreSQL tests skipped. Added transport checks for schema submission, planning checks that enforce the same Pydantic schema, and regression coverage that invalid/oversized plans remain rejected. The quota implementation was not changed.

Diagnostics consumed the provider's free-tier allowance but did not reserve demo questions. A read-only Neon check showed three used questions, no per-account override; the four-question default therefore leaves one remaining. No counters were reset.

## Reproduce and resume

Restart the local server to load both code and `.env`:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.run_demo
```

Open `http://127.0.0.1:8000/#assistant`, refresh the page, and check that the selected public model comes from the updated provider catalog. A real browser question consumes the account allowance, unlike the diagnostic below.

To deliberately run another live API check:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.check_live_analysis --live
```

This sends demo filters and aggregates to the configured provider and consumes provider quota. It is not part of the standard test suite and does not send real email.

If the user still reports failure, capture the HTTP status and safe validation categories from that exact attempt. Do not replace their report with the successful diagnostic. Google service availability and model output remain external sources of failure. Vercel deployment is still pending.

Google's pricing page listed a free tier for Gemini 2.5 Flash at the time of selection: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing). Usage remains subject to the account's provider limits.

## Follow-up: selectable providers

The user reported another invalid plan after restarting; the earlier successful live check did not resolve their browser failure. Gemini remains unresolved.

The demo now exposes a primary and an optional alternate provider/model pair, configured through `DEMO_PROVIDER` / `DEMO_MODEL` and `DEMO_ALTERNATE_PROVIDER` / `DEMO_ALTERNATE_MODEL`. The API rejects other pairs before quota reservation. Both choices use the same verified account and global quota. The provider/model selectors are visible in demo mode.

Locally, the existing `deepseek` configuration points to `api.groq.com` and a Qwen model. Its visible label is now Groq; the internal identifier and existing credentials remain compatible. It is the primary local choice, with Gemini 2.5 Flash as the alternate. No automatic fallback calls were added. Switching providers does not replenish questions. No additional live Groq request has been made in this follow-up.

Automated validation: 68 tests, 65 passed and three optional PostgreSQL checks skipped, including alternate allowlisting and shared account reservation.
