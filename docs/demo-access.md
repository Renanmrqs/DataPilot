# Public demo access and quotas

**October 21 update:** the full API returned a complete real analysis with Gemini 2.5 Flash after the planning contract changes. User-browser verification and deployment remain pending. See the [latest checkpoint](checkpoint-2026-10-21.md). This is not a validated public release.

The demo provides email magic-link sign-in, a server-owned question allowance, and a Portuguese UI showing remaining questions. Real email delivery and hosted login still require manual validation. Public AI stays paused by default.

The detailed Portuguese implementation walkthrough, verification results, and email configuration steps are in [demo-access.pt-BR.md](demo-access.pt-BR.md).

## Components

- `src/demo/config.py`: validates server configuration; Vercel always requires demo protection.
- `src/demo/auth.py`: validates Neon JWT signature, expiry, issuer, audience, subject and verified email, using cached public JWKS keys.
- `src/demo/quota.py`: reserves per-account and shared daily allowances atomically in PostgreSQL. The transaction ends before calling AI.
- `src/api/deployment.py`: guards both AI routes, enforces the selected public model, and fails closed on quota storage errors.
- `src/api/demo.py`: returns safe configuration and the caller's allowance with `Cache-Control: no-store`.
- `src/api/auth.py`: same-origin auth endpoints, fixed magic-link callback, verifier/challenge exchange, first-party HttpOnly cookies, origin checks, logout and callback log redaction.
- `src/web/demo-access.js`: manages the magic-link form, session token retrieval, remaining questions, logout and allowance refresh after success or failure. JWTs remain in memory.
- `sql/demo_schema.sql`: creates dedicated quota tables without changing Neon's managed auth tables. Tables have RLS enabled and no client-facing policies.

Sales data remains in read-only SQLite. Neon PostgreSQL stores quota counters; managed Neon Auth stores identities and sessions.

## Defaults and accounting

The default is four lifetime questions per account, twenty shared questions per UTC day and a fifteen-second per-account cooldown. These are demo settings, not assumptions about provider quotas. The optional `accounts.question_limit` overrides the default for a specific account; `NULL` restores the default and zero blocks new questions.

The API validates filters and reserves one question before the first AI call. Attempts that reach AI remain charged even if planning, explanation or the provider fails. A process crash after reservation may also consume a question. Resetting browser conversation or signing in again does not reset the account allowance.

Both `/api/analysis` and the legacy `/api/copilot` use the same counters. A fixed public provider/model prevents requests from choosing another privately configured model. The normal local profile retains provider comparison.

PostgreSQL row locks serialize reservations for the day and account, in that order. Counter updates commit together or roll back. Neon pooled connections require transaction-local `SET LOCAL` configuration rather than a `search_path` startup option.

## Setup and local review

Install `requirements.txt`. Configure `NEON_AUTH_BASE_URL`, the pooled `NEON_DATABASE_URL`, and the `DEMO_*` settings listed in `.env.example`. Keep `DEMO_AI_ENABLED=false` until real authentication and deployment checks pass.

Create the quota schema once per database:

```powershell
.\.venv\Scripts\python.exe -B -m src.demo.setup_database
```

Start the protected local profile without changing `.env`:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.run_demo
```

Open `http://127.0.0.1:8000/#assistant`. The existing Uvicorn command runs the previous local profile unless `DEMO_MODE=true` is configured. Vercel forces demo mode.

## Verification and pending work

- Standard unittest suite: simulated AI, cryptographically signed identity tests, access states and both protected routes.
- Opt-in `test_demo_postgres.py`: creates and removes isolated schemas to test actual persistence, limits, rollback and concurrent reservations. Set `DATAPILOT_TEST_NEON=1` explicitly.
- `scripts/check_demo_ui.py`: optional Playwright/installed Chrome check against a local server; simulates auth, email and AI and checks mobile layout and allowance states.
- `scripts/check_auth_flow.py`: self-contained browser/API integration with real first-party cookies, a simulated Neon service requiring callback exchange, signed JWT verification, reload, logout and replay rejection.

No real email or AI requests are made by these automated tests. The user confirmed real email delivery. Before publishing, validate the corrected real login, trusted origins, session restoration and the Vercel build. Browser auth requests now stay on the application origin: the API completes Neon's `neon_auth_session_verifier` exchange using the original challenge cookie, stores mapped first-party cookies, and redirects to a clean URL. Cookies are HttpOnly and SameSite=Lax, with Secure on HTTPS. This replaces the incomplete direct `/token` flow that ignored the callback verifier. Old links need replacement because they use the previous callback destination.

Multiple email accounts can belong to one person. No custom IP limiter or CAPTCHA is implemented. Email resend UI throttling is not server-side abuse protection. Provider/Auth/SMTP limits and platform traffic protections still need review before broad sharing. The global cap bounds demo question reservations, not tokens, provider retries or all uses of the same provider credentials.

## Sources

- [Neon Magic Link](https://neon.com/docs/auth/guides/plugins/magic-link)
- [Neon JWT verification and cross-domain limitations](https://neon.com/docs/auth/guides/plugins/jwt)
- [Neon production email configuration](https://neon.com/docs/auth/production-checklist)
