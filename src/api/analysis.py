"""Orchestrate question -> validated plan -> calculated panel -> interpretation."""
from contextlib import closing
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.ai.analysis_plan import select_analysis
from src.ai.copilot import explain
from src.analytics.analysis import available_values, build_analysis, filter_sql


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    provider: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=150)
    question: str = Field(min_length=1, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None
    channel: str | None = None
    category: str | None = None


def create_analysis_router(open_connection):
    router = APIRouter()

    @router.post("/api/analysis")
    def analyze(request: AnalysisRequest):
        filters = request.model_dump(
            mode="json", exclude={"provider", "model", "question"}
        )
        if request.start_date and request.end_date and request.start_date > request.end_date:
            raise HTTPException(422, "A data inicial não pode ser posterior à data final.")

        with closing(open_connection()) as connection:
            options = available_values(connection)
            filter_sql(filters, options)
        plan, planning_ms = select_analysis(
            request.provider, request.model, request.question, filters, options
        )
        result = {
            "provider": request.provider,
            "model": request.model,
            "elapsed_ms": planning_ms,
            "context_id": "",
            "truncated": False,
            "notice": "Confira a interpretação da IA com os indicadores calculados.",
            "panel": None,
        }
        if plan.topic in ("unsupported", "clarification"):
            result.update(
                status=plan.topic,
                answer=plan.message or "Preciso de mais detalhes sobre a pergunta ou de dados que não estão nesta base.",
            )
            return result

        with closing(open_connection()) as connection:
            panel, context = build_analysis(connection, plan, filters)
        result["panel"] = panel
        if panel["empty"]:
            result.update(
                status="empty",
                answer="Não há vendas para o período e os filtros desta análise. Ajuste a seleção e tente novamente.",
            )
            return result

        try:
            interpretation = explain(
                request.provider, request.model, request.question, context
            )
            result.update(interpretation)
            result["elapsed_ms"] += planning_ms
            result["status"] = "complete"
        except HTTPException as exc:
            # Keep useful, calculated results when the second provider call fails.
            result.update(
                status="partial",
                answer="O painel foi calculado, mas a interpretação da IA não ficou disponível. " + str(exc.detail),
                notice="Os indicadores e gráficos foram calculados pelo sistema. Nenhuma explicação completa da IA foi obtida.",
            )
        return result

    return router
