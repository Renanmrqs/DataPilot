"""Check demo UI in Chromium using simulated auth/AI; never send email or call AI.

Requires the optional Playwright package and an installed Google Chrome.
Run with the API already serving locally, or pass another local URL.
"""
import argparse
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    if urlsplit(args.url).hostname not in ("localhost", "127.0.0.1"):
        raise SystemExit("Use a local server for simulated UI checks.")
    screenshot_dir = Path(tempfile.gettempdir()) / "datapilot-demo-preview"
    screenshot_dir.mkdir(exist_ok=True)
    state = {"authenticated": False, "used": 0, "daily_available": True, "paused": False, "unavailable": False}
    counts = {"email": 0, "analysis": 0}
    errors = []

    def access():
        remaining = 2 - state["used"]
        status = "ready" if state["authenticated"] else "login_required"
        if not remaining:
            status = "exhausted"
        if not state["daily_available"]:
            status = "daily_limit"
        if state["paused"]:
            status = "paused"
        if state["unavailable"]:
            status = "unavailable"
        return {
            "mode": "demo", "auth_url": "/api/auth", "authenticated": state["authenticated"],
            "can_ask": status == "ready", "status": status, "default_limit": 2,
            "provider": "gemini", "model": "demo-model", "email": "visitante@exemplo.com",
            "message": {"ready": "Acesso confirmado.", "login_required": "Confirme seu e-mail para experimentar a IA.",
                        "exhausted": "Você usou suas perguntas da demonstração.", "daily_limit": "A cota de IA terminou por hoje.",
                        "paused": "O chat está em preparação.", "unavailable": "Não foi possível consultar seu saldo."}[status],
            "quota": {"limit": 2, "used": state["used"], "remaining": remaining,
                      "daily_available": state["daily_available"], "retry_after_seconds": 0} if state["authenticated"] else None,
        }

    def fulfill(route, value, status=200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(value))

    def auth_route(route):
        path = urlsplit(route.request.url).path
        if path.endswith("/token"):
            fulfill(route, {"token": "simulated-token"} if state["authenticated"] else {}, 200 if state["authenticated"] else 401)
        elif path.endswith("/sign-in/magic-link"):
            data = route.request.post_data_json
            assert data["email"] == "visitante@exemplo.com"
            counts["email"] += 1
            fulfill(route, {"status": True})
        elif path.endswith("/sign-out"):
            state["authenticated"] = False
            fulfill(route, {"success": True})
        else:
            route.abort()

    def analysis_route(route):
        assert route.request.headers.get("authorization") == "Bearer simulated-token"
        counts["analysis"] += 1
        state["used"] += 1
        if state["used"] == 2:
            # A failed provider attempt still consumes a reserved question.
            fulfill(route, {"detail": "O provedor está temporariamente indisponível."}, 503)
        else:
            fulfill(route, {"provider": "gemini", "model": "demo-model", "answer": "Receita conferida nos indicadores.",
                            "notice": "Resposta simulada para verificar a interface.", "elapsed_ms": 100,
                            "context_id": "", "truncated": False, "panel": None, "status": "complete"})

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1365, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/api/demo/access", lambda route: fulfill(route, access()))
        page.route("**/api/providers", lambda route: fulfill(route, {"providers": [
            {"id": "gemini", "label": "Gemini", "configured": True, "models": ["demo-model"]}]}))
        page.route("**/api/auth/**", auth_route)
        page.route("**/api/analysis", analysis_route)
        page.goto(args.url)
        page.locator("#results").wait_for(state="visible")
        page.locator("#demo-login").wait_for(state="visible")
        assert page.locator("#ask").is_disabled()
        assert "2 perguntas" in page.locator("#demo-quota").inner_text()
        page.locator("#demo-refresh").click()
        page.wait_for_function("document.getElementById('demo-message').textContent.includes('não foi encontrado')")
        page.locator("#assistant").scroll_into_view_if_needed()
        page.screenshot(path=str(screenshot_dir / "desktop-login.png"), full_page=True)
        page.locator("#demo-email").fill("visitante@exemplo.com")
        page.locator("#demo-email-submit").click()
        page.wait_for_function("document.getElementById('demo-email-status').textContent.includes('Confira')")
        assert counts["email"] == 1
        assert page.locator("#demo-email-submit").is_disabled()
        state["authenticated"] = True
        # Returning from the email tab should restore access without a click.
        page.wait_for_timeout(2100)
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        page.wait_for_function("!document.getElementById('ask').disabled")
        assert "2 de 2" in page.locator("#demo-quota").inner_text()
        page.locator("#ask").click()
        page.wait_for_function("document.getElementById('demo-quota').textContent.includes('1 de 2')")
        page.locator("#new-conversation").click()
        assert "1 de 2" in page.locator("#demo-quota").inner_text()
        page.locator("#question").fill("Qual a margem?")
        page.locator("#ask").click()
        page.wait_for_function("document.getElementById('demo-quota').textContent.includes('0 de 2')")
        assert page.locator("#ask").is_disabled()
        assert counts["analysis"] == 2
        page.reload()
        page.wait_for_function("document.getElementById('demo-quota').textContent.includes('0 de 2')")
        assert page.locator("#ask").is_disabled()
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#assistant").scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(screenshot_dir / "mobile-exhausted.png"), full_page=True)
        page.locator("#theme-toggle").click()
        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(screenshot_dir / "mobile-dark-exhausted.png"), full_page=True)
        state.update(used=0, daily_available=False)
        page.locator("#demo-refresh").click()
        page.wait_for_function("document.getElementById('demo-message').textContent.includes('por hoje')")
        assert page.locator("#ask").is_disabled()
        state.update(daily_available=True, paused=True)
        page.locator("#demo-refresh").click()
        page.wait_for_function("document.getElementById('demo-message').textContent.includes('pausado')")
        assert page.locator("#ask").is_disabled()
        state.update(paused=False, unavailable=True)
        page.locator("#demo-refresh").click()
        page.wait_for_function("document.getElementById('demo-message').textContent.includes('consultar')")
        assert page.locator("#ask").is_disabled()
        page.locator("#demo-logout").click()
        page.locator("#demo-login").wait_for(state="visible")
        assert page.locator("#ask").is_disabled()
        assert not errors, errors
        browser.close()
    print("Demo UI checks passed: login, quota, failed attempt, reload, reset, daily cap, pause, outage, logout, mobile, dark theme.")
    print(f"Simulated screenshots: {screenshot_dir}")


if __name__ == "__main__":
    main()
