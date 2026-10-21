# Checkpoint: public demo access, October 20, 2026

## Current outcome

**Work in progress. The user still cannot complete a real AI analysis in the demo. Do not treat this checkpoint as a working public release.**

The user confirmed real magic-link email delivery and, after the callback correction, shared a screen showing a verified account and its server-provided allowance. The unresolved problem is now the live analysis request. An earlier visible error was: "O modelo não retornou um plano de análise válido. Tente reformular a pergunta ou trocar de modelo." The last user report was that it still does not work; no new error text was captured after the most recent change.

The user asked to save and commit the session and resume another day. Stop implementation here; do not deploy or publish this unfinished flow.

## Implemented

- Vercel entrypoint and build configuration; sales data remains read-only SQLite generated from tracked CSVs.
- Demo profile with email access UI, provider label, remaining questions, logout and paused/exhausted/unavailable states.
- Neon PostgreSQL quota schema, separate from managed authentication tables. The schema was created in the configured Neon project.
- Verified JWT identity and atomic per-account/daily question reservations. Both analysis endpoints share the quota guard.
- First-party authentication endpoints in FastAPI. They request a magic link, exchange Neon's return verifier with the original challenge, map auth cookies onto the app origin and restore/logout the session.
- Callback credentials are omitted from standard Uvicorn access logs. Raw questions, model outputs, keys and JWTs are not added to diagnostic logs.
- Local demo launcher and browser checks, plus Portuguese and English implementation guides.
- Safe plan-rejection diagnostics: provider, model, truncation flag and Pydantic error categories.

## Configuration at the end of the session

- Public demo provider: `gemini`.
- Locally configured model: `gemini-3.8-flash`. This was already selected when the invalid-plan screenshot was reported; changing providers was not the fix.
- Default account allowance: **four lifetime questions**, increased from two at the user's request. Existing consumption is preserved.
- Shared daily allowance: twenty question reservations per UTC day.
- Per-account cooldown: fifteen seconds.
- Local `.env`: `DEMO_AI_ENABLED=true` for user testing. The committed example remains false by default.
- SMTP was configured in Neon using the user's email setup. Real delivery was confirmed.
- No Vercel deployment has been validated or published.

Secrets remain in the ignored local `.env` and the Neon console. They are intentionally absent from this commit. Existing managed users, SMTP configuration and quota rows are external state in Neon; they are not backed up by Git. Do not reset counters, recreate accounts or alter managed auth tables to resume debugging.

## Validation and limits

- Final standard suite: 64 tests discovered; 61 passed and three opt-in PostgreSQL tests skipped.
- The three PostgreSQL tests passed separately earlier in the session, in disposable schemas, including concurrency for the last question. Subsequent changes did not modify quota reservation logic.
- Full browser/API authentication check passed with actual browser cookies and signed JWTs against a simulated Neon service. It covers the required callback exchange, reload, logout and verifier replay rejection.
- UI checks passed with simulated identity/AI in desktop, mobile and dark theme.
- A live Gemini planning diagnostic returned a valid `ticket` plan. The first attempt received HTTP 503; the existing adapter retried and succeeded. This diagnostic did not call the explanation stage and does not establish a working end-to-end analysis.
- The user's invalid-plan failure was not reproduced or fixed conclusively. Mocked tests and one successful plan do not override the user's latest failure report.
- Reserved questions currently count even when provider output fails validation or explanation fails. A question can involve planning, explanation and provider retries; the allowance is not a token count.

## First task when resuming

1. Read this checkpoint before earlier historical plans. The immediate goal is a working, understandable demo, not QVD abstraction or new features.
2. Start the protected local profile and confirm the exact process loads the intended `.env`, provider, model and four-question limit. Never print keys or connection strings.
3. Reproduce the user's actual question through the browser and `/api/analysis`. Record the HTTP status, UI error, safe plan-validation categories and truncation indicator from the same attempt.
4. Determine whether the remaining failure is invalid JSON/schema, generation truncation, provider availability, filter validation or the explanation stage. Do not assume an intermittent provider failure explains a schema rejection.
5. Add a targeted regression from the actual response shape, with any private content removed, then implement a small fix. Preserve allowlists and deterministic calculations; do not weaken validation just to accept output.
6. Validate a complete real question and the visible answer/panel, with the user's awareness of provider quota use. Verify allowance changes and failure behavior before preparing Vercel deployment.

Keep explanations concise and in Portuguese. The user wants to understand meaningful changes and is frustrated by repeated instructions that do not solve the underlying failure. Avoid broad rewrites and repeated generic troubleshooting.

## Resume commands

```powershell
.\.venv\Scripts\python.exe -B -m scripts.run_demo
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B -m scripts.check_auth_flow
```

The last command needs optional Playwright and an installed Google Chrome; it does not send real email or call real AI. Stop the current server before starting another on port 8000.

Detailed walkthrough: [Portuguese](demo-access.pt-BR.md), [English](demo-access.md).
