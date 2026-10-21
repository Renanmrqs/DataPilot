"""Exercise signed identities, fail-closed access, and quota orchestration."""
import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import psycopg
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from src.api.deployment import DemoAccess
from src.api.main import create_app
from src.demo.auth import DemoUser, verified_user
from src.demo.config import demo_settings
import test_prototype


DEMO_ENV = {
    "VERCEL": "0", "DEMO_MODE": "true", "DEMO_AI_ENABLED": "true",
    "DEMO_PROVIDER": "gemini", "DEMO_MODEL": "demo-model",
    "DEMO_ALTERNATE_PROVIDER": "", "DEMO_ALTERNATE_MODEL": "",
    "GEMINI_API_KEY": "not-a-real-key", "GEMINI_MODELS": "demo-model,private-model",
    "NEON_AUTH_BASE_URL": "https://auth.example.test/auth",
    "NEON_DATABASE_URL": "postgresql://unused",
    "DEMO_QUESTIONS_PER_USER": "2", "DEMO_DAILY_QUESTIONS": "20",
    "DEMO_COOLDOWN_SECONDS": "15",
}
QUOTA = {"limit": 2, "used": 0, "remaining": 2, "daily_available": True, "retry_after_seconds": 0}
USER = DemoUser("verified-id", "visitor@example.test")


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def test_signature_expiry_issuer_audience_and_email_verification(self):
        with patch.dict(os.environ, DEMO_ENV):
            config = demo_settings()
        now = int(time.time())
        claims = {
            "sub": USER.id, "email": USER.email, "emailVerified": True,
            "iat": now, "exp": now + 60, "iss": config.auth_origin, "aud": config.auth_origin,
        }
        cases = [({}, 200), ({"exp": now - 60}, 401), ({"iss": "https://attacker.test"}, 401),
                 ({"aud": "other"}, 401), ({"emailVerified": False}, 403), ({"banned": True}, 403)]
        key = SimpleNamespace(key=self.private_key.public_key())
        with patch("src.demo.auth.key_client") as client:
            client.return_value.get_signing_key_from_jwt.return_value = key
            for changes, expected in cases:
                token = jwt.encode({**claims, **changes}, self.private_key, algorithm="RS256")
                request = Request({"type": "http", "headers": [(b"authorization", f"Bearer {token}".encode())]})
                with self.subTest(changes=changes):
                    if expected == 200:
                        self.assertEqual(verified_user(request, config), USER)
                    else:
                        with self.assertRaises(HTTPException) as caught:
                            verified_user(request, config)
                        self.assertEqual(caught.exception.status_code, expected)
            bad_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            token = jwt.encode(claims, bad_key, algorithm="RS256")
            request = Request({"type": "http", "headers": [(b"authorization", f"Bearer {token}".encode())]})
            with self.assertRaises(HTTPException) as caught:
                verified_user(request, config)
            self.assertEqual(caught.exception.status_code, 401)


class DemoApiTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, DEMO_ENV)
        self.environment.start()
        self.client = TestClient(create_app())

    def tearDown(self):
        self.client.close()
        self.environment.stop()

    def test_anonymous_access_has_safe_config_but_cannot_ask(self):
        with patch("src.api.demo.QuotaStore") as store:
            response = self.client.get("/api/demo/access")
        self.assertEqual(response.headers["cache-control"], "no-store")
        data = response.json()
        self.assertEqual(data["default_limit"], 2)
        self.assertFalse(data["can_ask"])
        self.assertNotIn("database_url", data)
        self.assertNotIn("key", data)
        store.assert_not_called()
        for route in ("/api/analysis", "/api/copilot"):
            result = self.client.post(route, json={"provider": "gemini", "model": "demo-model", "question": "Receita?"})
            self.assertEqual(result.status_code, 401)

    def test_catalog_only_exposes_the_selected_public_model(self):
        data = self.client.get("/api/providers").json()["providers"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["models"], ["demo-model"])

    def test_alternate_model_is_allowlisted_and_uses_the_same_account(self):
        with patch.dict(os.environ, {
            "DEMO_ALTERNATE_PROVIDER": "deepseek", "DEMO_ALTERNATE_MODEL": "alternate-model",
            "DEEPSEEK_API_KEY": "fake", "DEEPSEEK_MODELS": "alternate-model,private-model",
        }):
            catalog = self.client.get("/api/providers").json()["providers"]
            self.assertEqual([item["id"] for item in catalog], ["gemini", "deepseek"])
            self.assertEqual(catalog[1]["models"], ["alternate-model"])
            access = DemoAccess(demo_settings(), USER)
            with patch("src.api.deployment.QuotaStore") as store:
                access.reserve("deepseek", "alternate-model")
                store.return_value.reserve.assert_called_once_with(USER.id)
                with self.assertRaises(HTTPException):
                    access.reserve("deepseek", "private-model")
                self.assertEqual(store.return_value.reserve.call_count, 1)

    def test_quota_states_and_database_failure(self):
        cases = [({}, "ready", True), ({"remaining": 0, "used": 2}, "exhausted", False),
                 ({"daily_available": False}, "daily_limit", False),
                 ({"retry_after_seconds": 5}, "cooldown", False)]
        with patch("src.api.demo.verified_user", return_value=USER), patch("src.api.demo.QuotaStore") as store:
            for changes, status, can_ask in cases:
                store.return_value.snapshot.return_value = {**QUOTA, **changes}
                data = self.client.get("/api/demo/access", headers={"Authorization": "Bearer signed"}).json()
                self.assertEqual((data["status"], data["can_ask"]), (status, can_ask))
            store.return_value.snapshot.side_effect = psycopg.OperationalError("secret connection details")
            response = self.client.get("/api/demo/access", headers={"Authorization": "Bearer signed"})
            self.assertEqual(response.json()["status"], "unavailable")
            self.assertNotIn("secret", response.text)

    def test_quota_reservation_uses_verified_identity_and_fixed_model(self):
        config = demo_settings()
        access = DemoAccess(config, USER)
        with patch("src.api.deployment.QuotaStore") as store:
            with self.assertRaises(HTTPException) as caught:
                access.reserve("gemini", "private-model")
            self.assertEqual(caught.exception.status_code, 422)
            store.assert_not_called()
            access.reserve("gemini", "demo-model")
            store.return_value.reserve.assert_called_once_with(USER.id)
            store.return_value.reserve.side_effect = psycopg.OperationalError("secret")
            with self.assertRaises(HTTPException) as caught:
                access.reserve("gemini", "demo-model")
            self.assertEqual(caught.exception.status_code, 503)

    def test_paused_demo_does_not_read_identity_or_reserve(self):
        with patch.dict(os.environ, {"DEMO_AI_ENABLED": "false"}), patch("src.api.deployment.verified_user") as identity:
            self.assertEqual(self.client.get("/api/demo/access").json()["status"], "paused")
            for route in ("/api/analysis", "/api/copilot"):
                result = self.client.post(route, json={"provider": "gemini", "model": "demo-model", "question": "Receita?"})
                self.assertEqual(result.status_code, 503)
            identity.assert_not_called()

    def test_vercel_cannot_disable_demo_protection_and_invalid_config_fails_closed(self):
        with patch.dict(os.environ, {"VERCEL": "1", "DEMO_MODE": "false"}):
            self.assertTrue(demo_settings().enabled)
        with patch.dict(os.environ, {"DEMO_QUESTIONS_PER_USER": "-1"}):
            self.assertEqual(self.client.get("/api/demo/access").status_code, 503)

    def test_default_four_question_allowance_preserves_existing_consumption(self):
        with patch.dict(os.environ, DEMO_ENV):
            del os.environ["DEMO_QUESTIONS_PER_USER"]
            from src.demo.quota import QuotaStore
            from datetime import datetime, timezone
            config = demo_settings()
            quota = QuotaStore(config).describe(
                {"used_questions": 1, "question_limit": None, "last_question_at": None},
                {"used_questions": 1}, datetime.now(timezone.utc),
            )
            self.assertEqual(quota["limit"], 4)
            self.assertEqual(quota["remaining"], 3)

    def test_both_routes_reserve_before_provider_and_reject_exhausted_users(self):
        fixture = test_prototype.DashboardTests()
        fixture.setUp()
        try:
            payload = {"provider": "gemini", "model": "demo-model", "question": "Receita?"}
            with patch("src.api.deployment.verified_user", return_value=USER), \
                    patch("src.api.deployment.QuotaStore") as store, \
                    patch("src.api.analysis.select_analysis") as planner, \
                    patch("src.api.main.explain") as legacy_explain:
                store.return_value.reserve.side_effect = HTTPException(429, "Cota encerrada.")
                for route in ("/api/analysis", "/api/copilot"):
                    result = fixture.client.post(route, json=payload, headers={"Authorization": "Bearer signed"})
                    self.assertEqual(result.status_code, 429)
                planner.assert_not_called()
                legacy_explain.assert_not_called()
                self.assertEqual(store.return_value.reserve.call_count, 2)
                for call in store.return_value.reserve.call_args_list:
                    self.assertEqual(call.args, (USER.id,))
                store.return_value.reserve.reset_mock()
                invalid = fixture.client.post("/api/analysis", json={**payload, "category": "Unknown"})
                self.assertEqual(invalid.status_code, 422)
                store.return_value.reserve.assert_not_called()
        finally:
            fixture.tearDown()
