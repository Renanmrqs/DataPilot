"""Verify that hosting cannot bypass the temporary AI gate."""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request

from src.api.deployment import require_ai_access
from src.api.main import create_app


class DeploymentTests(unittest.TestCase):
    def test_local_ai_access_is_preserved(self):
        with patch.dict(os.environ, {"VERCEL": "0"}):
            require_ai_access(Request({"type": "http", "headers": []}))

    def test_both_hosted_ai_routes_block_before_database_or_provider_access(self):
        payload = {"provider": "example", "model": "example", "question": "Receita?"}
        with patch.dict(os.environ, {"VERCEL": "1", "DEMO_AI_ENABLED": "false"}), \
                patch("src.api.main.connect") as connect, \
                patch("src.api.analysis.select_analysis") as plan, \
                patch("src.api.analysis.explain") as analysis_explain, \
                patch("src.api.main.explain") as copilot_explain, \
                TestClient(create_app()) as client:
            for route in ("/api/analysis", "/api/copilot"):
                with self.subTest(route=route):
                    response = client.post(route, json=payload)
                    self.assertEqual(response.status_code, 503)
                    self.assertIn("temporariamente", response.json()["detail"])
            connect.assert_not_called()
            plan.assert_not_called()
            analysis_explain.assert_not_called()
            copilot_explain.assert_not_called()
            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/static/app.js").status_code, 200)
