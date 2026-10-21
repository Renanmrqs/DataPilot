"""Exercise the full browser -> FastAPI -> simulated Neon callback flow.

Uses real browser cookies and signed JWTs. No real email, Neon or AI calls.
Requires optional Playwright and an installed Google Chrome.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import json
import os
import socket
import time
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
import jwt
from playwright.sync_api import sync_playwright
import uvicorn

from src.api.main import create_app


def main():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    issued_at = int(time.time())
    token = jwt.encode({
        "sub": "browser-test-user", "email": "visitor@example.test", "emailVerified": True,
        "iat": issued_at, "exp": issued_at + 300,
        "iss": "https://auth.example.test", "aud": "https://auth.example.test",
    }, private_key, algorithm="RS256")
    challenge_name = "__Secure-neon-auth.session_challenge"
    session_name = "__Secure-neon-auth.session_token"
    state = {"callback": None, "exchanged": False, "signed_out": False}
    paths = []

    def neon(request):
        path = request.url.path
        paths.append(path)
        if path.endswith("/sign-in/magic-link"):
            body = json.loads(request.content)
            assert body["email"] == "visitor@example.test"
            assert body["callbackURL"].endswith("/api/auth/callback")
            state["callback"] = body["callbackURL"]
            return httpx.Response(200, json={"status": True}, headers={
                "set-cookie": f"{challenge_name}=signed-challenge; Secure; HttpOnly; Path=/; SameSite=None; Partitioned",
            })
        if path.endswith("/get-session"):
            if state["exchanged"] or request.url.params.get("neon_auth_session_verifier") != "single-use-verifier" or f"{challenge_name}=signed-challenge" not in request.headers["cookie"]:
                return httpx.Response(401, json={"code": "INVALID_SESSION_VERIFIER"})
            state["exchanged"] = True
            return httpx.Response(200, json={"session": {"id": "test-session"}, "user": {"id": "browser-test-user"}}, headers=[
                ("set-cookie", f"{session_name}=signed-session; Secure; HttpOnly; Path=/; SameSite=None; Partitioned"),
                ("set-cookie", f"{challenge_name}=; Max-Age=0; Secure; HttpOnly; Path=/; SameSite=None; Partitioned"),
            ])
        if path.endswith("/token"):
            if f"{session_name}=signed-session" not in request.headers["cookie"] or state["signed_out"]:
                return httpx.Response(401, json={"code": "UNAUTHORIZED"})
            return httpx.Response(200, json={"token": token})
        if path.endswith("/sign-out"):
            state["signed_out"] = True
            return httpx.Response(200, json={"success": True})
        raise AssertionError("Unexpected upstream request")

    environment = {
        "VERCEL": "0", "DEMO_MODE": "true", "DEMO_AI_ENABLED": "false",
        "DEMO_PROVIDER": "gemini", "DEMO_MODEL": "demo-model",
        "GEMINI_API_KEY": "not-real", "GEMINI_MODELS": "demo-model",
        "NEON_AUTH_BASE_URL": "https://auth.example.test/auth", "NEON_DATABASE_URL": "postgresql://unused",
        "DEMO_QUESTIONS_PER_USER": "2",  # Exercise a small allowance independently of defaults.
    }
    allowance = {"limit": 2, "used": 0, "remaining": 2, "daily_available": True, "retry_after_seconds": 0}
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, environment))
        stack.enter_context(patch("src.api.auth.upstream_client", side_effect=lambda: httpx.Client(transport=httpx.MockTransport(neon))))
        key_client = stack.enter_context(patch("src.demo.auth.key_client"))
        key_client.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key=private_key.public_key())
        quota = stack.enter_context(patch("src.api.demo.QuotaStore.snapshot", return_value=allowance))
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        app = create_app()
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        executor = ThreadPoolExecutor(max_workers=1)
        running = executor.submit(server.run, sockets=[listener])
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                if running.done():
                    running.result()
                time.sleep(0.05)
            assert server.started, "Local test server did not start"
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="chrome")
                page = browser.new_page()
                errors = []
                external_requests = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: external_requests.append(request.url) if not request.url.startswith(f"http://127.0.0.1:{port}/") else None)
                page.goto(f"http://127.0.0.1:{port}/#assistant")
                page.locator("#demo-login").wait_for(state="visible")
                page.locator("#demo-email").fill("visitor@example.test")
                page.locator("#demo-email-submit").click()
                page.wait_for_function("document.getElementById('demo-email-status').textContent.includes('Confira')")
                cookies = page.context.cookies()
                assert any(cookie["name"].startswith("datapilot_auth_") and cookie["httpOnly"] and cookie["sameSite"] == "Lax" for cookie in cookies)
                # Simulate opening the received email link after Neon's redirect.
                callback = state["callback"] + "?" + urlencode({"neon_auth_session_verifier": "single-use-verifier"})
                page.goto(callback)
                page.wait_for_function("document.getElementById('demo-description').textContent.includes('Acesso confirmado')")
                assert "2 de 2" in page.locator("#demo-quota").inner_text()
                assert "neon_auth_session_verifier" not in page.url
                assert page.locator("#ask").is_disabled()  # AI is intentionally paused.
                page.reload()
                page.wait_for_function("document.getElementById('demo-description').textContent.includes('Acesso confirmado')")
                assert "2 de 2" in page.locator("#demo-quota").inner_text()
                quota.assert_called_with("browser-test-user")
                assert not external_requests, "Browser auth requests must stay on the app origin"
                page.locator("#demo-logout").click()
                page.locator("#demo-login").wait_for(state="visible")
                assert not any(cookie["name"].startswith("datapilot_auth_") for cookie in page.context.cookies())
                page.goto(callback)
                page.wait_for_function("document.getElementById('demo-email-status').textContent.includes('Solicite um novo link')")
                assert "auth_error" not in page.url
                assert page.locator("#ask").is_disabled()
                assert not errors, errors
                browser.close()
        finally:
            server.should_exit = True
            running.result(timeout=10)
            executor.shutdown()
            listener.close()
    assert "/auth/get-session" in paths
    print("Auth flow passed: first-party challenge, callback exchange, signed identity, quota, reload, logout and replay rejection.")
    print("No browser calls to Neon, no real emails, no real AI calls.")


if __name__ == "__main__":
    main()
