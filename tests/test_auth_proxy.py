"""Verify callback exchange, cookie boundaries and origin checks without email."""
import logging
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from src.api.auth import AuthAccessLogFilter, local_cookie_name
from src.api.main import create_app


ENV = {"DEMO_MODE": "true", "VERCEL": "0", "NEON_AUTH_BASE_URL": "https://auth.example.test/auth"}
CHALLENGE = "__Secure-neon-auth.session_challenge"
SESSION = "__Secure-neon-auth.session_token"


class AuthProxyTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, ENV)
        self.environment.start()
        self.client = TestClient(create_app(), base_url="http://127.0.0.1:8000")
        self.calls = []
        self.used = False
        self.patch = patch("src.api.auth.upstream_client", side_effect=lambda: httpx.Client(transport=httpx.MockTransport(self.handle)))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.client.close()
        self.environment.stop()

    def handle(self, request):
        self.calls.append(request)
        self.assertEqual(request.headers["origin"], "http://127.0.0.1:8000")
        self.assertEqual(request.headers["x-neon-auth-middleware"], "true")
        if request.url.path.endswith("/sign-in/magic-link"):
            import json
            self.assertEqual(json.loads(request.content)["callbackURL"], "http://127.0.0.1:8000/api/auth/callback")
            return httpx.Response(200, json={"status": True}, headers={
                "set-cookie": f"{CHALLENGE}=challenge; Domain=auth.example.test; Path=/; HttpOnly; Secure; SameSite=None; Partitioned",
            })
        if request.url.path.endswith("/get-session"):
            if request.url.params.get("neon_auth_session_verifier") != "one-use-code" or self.used or f"{CHALLENGE}=challenge" not in request.headers["cookie"]:
                return httpx.Response(401, json={"message": "invalid"})
            self.used = True
            return httpx.Response(200, json={"session": {"id": "s"}, "user": {"id": "u"}}, headers=[
                ("set-cookie", f"{SESSION}=session; Path=/; HttpOnly; Secure; SameSite=None; Partitioned"),
                ("set-cookie", f"{CHALLENGE}=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=None; Partitioned"),
            ])
        if request.url.path.endswith("/token"):
            if f"{SESSION}=session" in request.headers["cookie"]:
                return httpx.Response(200, json={"token": "signed-jwt"})
            return httpx.Response(401, json={"message": "no session"})
        if request.url.path.endswith("/sign-out"):
            return httpx.Response(200, json={"success": True})
        raise AssertionError("Unexpected auth request")

    def test_login_callback_reload_and_logout_keep_cookie_on_app_domain(self):
        response = self.client.post("/api/auth/sign-in/magic-link", json={"email": "test@example.test"},
                                    headers={"origin": "http://127.0.0.1:8000"})
        self.assertEqual(response.status_code, 200)
        header = response.headers["set-cookie"]
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=lax", header)
        self.assertNotIn("Domain=", header)
        self.assertNotIn("Partitioned", header)
        self.assertNotIn("Secure;", header)  # Only local HTTP; HTTPS is tested separately.
        result = self.client.get("/api/auth/callback?neon_auth_session_verifier=one-use-code", follow_redirects=False)
        self.assertEqual(result.status_code, 303)
        self.assertEqual(result.headers["location"], "/#assistant")
        self.assertNotIn("one-use-code", result.headers["location"])
        self.assertEqual(result.headers["referrer-policy"], "no-referrer")
        for _ in range(2):
            token = self.client.get("/api/auth/token")
            self.assertEqual(token.json(), {"token": "signed-jwt"})
            self.assertEqual(token.headers["cache-control"], "no-store")
        # An unrelated application cookie must never be forwarded to Neon.
        self.client.cookies.set("private_app_cookie", "not-for-neon")
        self.client.get("/api/auth/token")
        self.assertNotIn("private_app_cookie", self.calls[-1].headers["cookie"])
        replay = self.client.get("/api/auth/callback?neon_auth_session_verifier=one-use-code", follow_redirects=False)
        self.assertIn("auth_error=invalid_link", replay.headers["location"])
        self.assertEqual(self.client.post("/api/auth/sign-out", json={}, headers={"origin": "http://127.0.0.1:8000"}).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/token").status_code, 401)

    def test_missing_verifier_and_cross_origin_posts_do_not_call_neon(self):
        response = self.client.get("/api/auth/callback", follow_redirects=False)
        self.assertIn("auth_error=invalid_link", response.headers["location"])
        for origin in ("https://attacker.test", "null", ""):
            response = self.client.post("/api/auth/sign-in/magic-link", json={"email": "test@example.test"}, headers={"origin": origin})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.calls, [])

    def test_arbitrary_redirect_payload_is_rejected(self):
        response = self.client.post("/api/auth/sign-in/magic-link", json={"email": "test@example.test", "callbackURL": "https://attacker.test"},
                                    headers={"origin": "http://127.0.0.1:8000"})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.calls, [])

    def test_https_cookie_is_secure_and_http_only(self):
        with TestClient(create_app(), base_url="https://demo.example.test") as client:
            # A minimal upstream avoids imposing this test fixture's localhost origin.
            upstream = httpx.Response(200, json={"status": True}, headers={"set-cookie": f"{CHALLENGE}=value; Secure; HttpOnly; SameSite=None; Partitioned"})
            with patch("src.api.auth.call_auth", return_value=upstream):
                response = client.post("/api/auth/sign-in/magic-link", json={"email": "test@example.test"}, headers={"origin": "https://demo.example.test"})
            self.assertIn("Secure", response.headers["set-cookie"])
            self.assertIn("HttpOnly", response.headers["set-cookie"])

    def test_callback_credential_is_redacted_in_access_log(self):
        record = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                                   ("client", "GET", "/api/auth/callback?neon_auth_session_verifier=secret", "1.1", 303), None)
        AuthAccessLogFilter().filter(record)
        self.assertNotIn("secret", record.getMessage())
        self.assertIn("[auth-callback]", record.getMessage())
