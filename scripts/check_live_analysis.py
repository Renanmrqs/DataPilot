"""Explicit live-provider diagnostic through the full analysis API, without user quota writes."""
import argparse
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.deployment import require_ai_access
from src.api.main import create_app
from src.ai.copilot import request_completion
from src.demo.config import demo_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow sending demo filters and aggregates to the configured AI provider.")
    parser.add_argument("--question", default="Por que o ticket médio está tão alto nesta seleção?")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live explicitly: this diagnostic consumes provider quota and sends demo data externally.")
    config = demo_settings()
    application = create_app()
    # This override exists only in this CLI's in-process test client. It never
    # changes the running server's authentication or persistent user counters.
    application.dependency_overrides[require_ai_access] = lambda: None

    def stage_completion(*positional, **keyword):
        stage = "planning" if keyword.get("response_schema") is not None else "explanation"
        result = request_completion(*positional, **keyword)
        print(json.dumps({"stage": stage, "elapsed_ms": result["elapsed_ms"], "truncated": result["truncated"]}), flush=True)
        return result

    print("Live diagnostic: demo data is sent to the configured provider. Provider quota is consumed; demo account counters are preserved.", flush=True)
    with patch("src.ai.analysis_plan.request_completion", side_effect=stage_completion), \
            patch("src.ai.copilot.request_completion", side_effect=stage_completion), \
            TestClient(application) as client:
        metadata = client.get("/api/metadata")
        if not metadata.is_success:
            raise SystemExit("The demo database is unavailable.")
        dates = metadata.json()
        response = client.post("/api/analysis", json={
            "provider": config.provider, "model": config.model, "question": args.question,
            "start_date": dates["start_date"], "end_date": dates["end_date"],
        })
    data = response.json()
    panel = data.get("panel") or {}
    print(json.dumps({
        "http_status": response.status_code, "status": data.get("status"),
        "provider": config.provider, "model": config.model,
        "error": data.get("detail"), "answer": data.get("answer"),
        "kpi_count": len(panel.get("kpis", [])), "chart_count": len(panel.get("charts", [])),
    }, ensure_ascii=True, indent=2))
    if not response.is_success or data.get("status") != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
