import json
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.ai.copilot import explain, list_providers
from src.api.main import app


class CopilotTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test-secret", "DEEPSEEK_MODELS": "test-model,second-model",
            "GEMINI_API_KEY": "test-secret", "GEMINI_MODELS": "test-model",
            "OPENAI_API_KEY": "test-secret", "OPENAI_MODELS": "test-model",
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.snapshot = {"summary": {"revenue_cents": 123456, "orders": 2},
                         "filters": {"category": "Bikes"}, "monthly": [], "categories": []}

    def test_all_built_in_providers_use_same_validated_context(self):
        context_ids = []
        def handle(request):
            payload = json.loads(request.content)
            context = json.loads(payload["messages"][1]["content"])
            self.assertEqual(context["validated_metrics"]["summary"]["revenue"], "1234.56")
            self.assertEqual(context["validated_metrics"]["summary"]["orders"], 2)
            self.assertEqual(request.headers["Authorization"], "Bearer test-secret")
            return httpx.Response(200, json={"choices":[{"message":{"content":"Recorded revenue is $1,234.56."},"finish_reason":"stop"}]})
        for provider in ("deepseek", "gemini", "openai"):
            with self.subTest(provider=provider):
                result = explain(provider,"test-model","Explain",self.snapshot,httpx.MockTransport(handle))
                self.assertEqual(result["model"],"test-model")
                self.assertIn("$1,234.56",result["answer"])
                context_ids.append(result["context_id"])
        self.assertEqual(len(set(context_ids)),1)

    def test_missing_configuration_and_unknown_models_do_not_call_provider(self):
        for provider, model, status in (("compatible","test-model",503),("deepseek","unknown",422),("unknown","test-model",422)):
            with self.subTest(provider=provider), self.assertRaises(HTTPException) as caught:
                explain(provider,model,"Explain",self.snapshot)
            self.assertEqual(caught.exception.status_code,status)

    def test_provider_failures_are_sanitized(self):
        for status in (401,429,500):
            transport = httpx.MockTransport(lambda request: httpx.Response(status,text="test-secret"))
            with self.subTest(status=status), self.assertRaises(HTTPException) as caught:
                explain("deepseek","test-model","Explain",self.snapshot,transport)
            self.assertEqual(caught.exception.status_code,503 if status >= 500 else 502)
            self.assertNotIn("test-secret",caught.exception.detail)


    def test_rate_limit_message_explains_type_and_retry_without_leaking_details(self):
        from src.ai.copilot import rate_limit_message

        response = httpx.Response(429, headers={"retry-after": "2.5"}, json={
            "error": {"message": "tokens per minute (TPM); organization private-id; test-secret"}
        })
        message = rate_limit_message(response)
        self.assertIn("tokens por minuto", message)
        self.assertIn("3 segundos", message)
        self.assertNotIn("private-id", message)
        self.assertNotIn("test-secret", message)

        response = httpx.Response(429, json={"error": {"message": "requests per day (RPD)"}})
        message = rate_limit_message(response)
        self.assertIn("requisições por dia", message)
        self.assertIn("não informou", message)

        message = rate_limit_message(httpx.Response(429, text="upstream error"))
        self.assertIn("limite de uso", message)

    def test_timeout_and_malformed_response(self):
        def timeout(request):
            raise httpx.ReadTimeout("timeout",request=request)
        with self.assertRaises(HTTPException) as caught:
            explain("deepseek","test-model","Explain",self.snapshot,httpx.MockTransport(timeout))
        self.assertEqual(caught.exception.status_code,504)
        with self.assertRaises(HTTPException) as caught:
            explain("deepseek","test-model","Explain",self.snapshot,httpx.MockTransport(lambda request:httpx.Response(200,json={})))
        self.assertEqual(caught.exception.status_code,502)

    def test_provider_catalog_never_contains_keys(self):
        catalog = list_providers()
        self.assertNotIn("test-secret",json.dumps(catalog))
        self.assertEqual(catalog[0]["models"],["test-model","second-model"])
        self.assertTrue(catalog[0]["configured"])

    def test_endpoint_rebuilds_metrics_instead_of_trusting_client_totals(self):
        with patch("src.api.main.explain",return_value={"answer":"test"}) as mocked, TestClient(app) as client:
            response=client.post("/api/copilot",json={
                "provider":"deepseek","model":"test-model","question":"Explain",
                "start_date":"2030-01-01","end_date":"2030-01-02",
                "summary":{"revenue_cents":999999},
            })
            self.assertEqual(response.status_code,422)
            self.assertFalse(mocked.called)

    def test_blank_questions_are_rejected(self):
        with TestClient(app) as client:
            response=client.post("/api/copilot",json={"provider":"deepseek","model":"test-model","question":"   "})
            self.assertEqual(response.status_code,422)

    def test_gemini_reserves_output_budget_and_uses_low_reasoning(self):
        from src.ai.copilot import request_completion

        def handle(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["reasoning_effort"], "low")
            self.assertEqual(payload["max_tokens"], 4096)
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "Resposta completa."}, "finish_reason": "stop"}]
            })

        with patch.dict(os.environ, {"GEMINI_MODELS": "gemini-3.8-flash"}):
            result = request_completion(
                "gemini", "gemini-3.8-flash", [{"role": "user", "content": "Teste"}],
                transport=httpx.MockTransport(handle),
            )
        self.assertFalse(result["truncated"])

    def test_transient_failure_retries_once_then_returns_success(self):
        from src.ai.copilot import request_completion

        attempts = []
        def handle(request):
            attempts.append(request)
            if len(attempts) == 1:
                return httpx.Response(503, text="temporary failure")
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "Resposta completa."}, "finish_reason": "stop"}]
            })

        with patch("src.ai.copilot.time.sleep") as sleep:
            result = request_completion(
                "gemini", "test-model", [], transport=httpx.MockTransport(handle)
            )
        self.assertEqual(len(attempts), 2)
        sleep.assert_called_once_with(1)
        self.assertEqual(result["answer"], "Resposta completa.")

    def test_persistent_service_failure_is_not_reported_as_bad_configuration(self):
        from src.ai.copilot import request_completion

        attempts = []
        def handle(request):
            attempts.append(request)
            return httpx.Response(503, text="test-secret")

        with patch("src.ai.copilot.time.sleep"), self.assertRaises(HTTPException) as caught:
            request_completion("gemini", "test-model", [], transport=httpx.MockTransport(handle))
        self.assertEqual(len(attempts), 2)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("temporariamente indisponível", caught.exception.detail)
        self.assertNotIn("test-secret", caught.exception.detail)

    def test_quota_and_bad_requests_are_not_retried(self):
        from src.ai.copilot import request_completion

        for status in (400, 401, 403, 404, 413, 429):
            attempts = []
            def handle(request):
                attempts.append(request)
                return httpx.Response(status, json={"error": {"message": "test-secret"}})
            with self.subTest(status=status), self.assertRaises(HTTPException):
                request_completion("gemini", "test-model", [], transport=httpx.MockTransport(handle))
            self.assertEqual(len(attempts), 1)

    def test_long_retry_after_does_not_trigger_an_early_retry(self):
        from src.ai.copilot import request_completion

        transport = httpx.MockTransport(
            lambda request: httpx.Response(503, headers={"retry-after": "120"})
        )
        with patch("src.ai.copilot.time.sleep") as sleep, self.assertRaises(HTTPException):
            request_completion("gemini", "test-model", [], transport=transport)
        sleep.assert_not_called()

    def test_cut_off_explanation_is_not_displayed_as_complete(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json={
            "choices": [{"message": {"content": "Uma frase cortada"}, "finish_reason": "length"}]
        }))
        with self.assertRaises(HTTPException) as caught:
            explain("gemini", "test-model", "Explique", self.snapshot, transport)
        self.assertIn("incompleta", caught.exception.detail)
