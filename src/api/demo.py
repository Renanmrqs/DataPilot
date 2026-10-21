"""Expose safe demo configuration and the authenticated user's allowance."""
import psycopg
from fastapi import APIRouter, Request, Response

from src.api.deployment import provider_ready, public_settings
from src.demo.auth import verified_user
from src.demo.quota import QuotaStore


router = APIRouter()


@router.get("/api/demo/access")
def demo_access(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    config = public_settings()
    if not config.enabled:
        return {"mode": "local", "can_ask": True}
    result = {
        "mode": "demo", "auth_url": "/api/auth" if config.auth_url else "",
        "authenticated": False, "can_ask": False,
        "default_limit": config.questions_per_user,
        "provider": config.provider, "model": config.model,
        "quota": None, "status": "login_required",
        "message": "Confirme seu e-mail para experimentar a IA. Sem senha.",
    }
    if not config.ai_enabled or not provider_ready(config):
        result.update(status="paused", message="O chat está em preparação. O painel e os filtros estão disponíveis.")
    if not request.headers.get("authorization"):
        return result
    user = verified_user(request, config)
    result.update(authenticated=True, email=user.email)
    if not config.database_url:
        result.update(status="unavailable", message="Não foi possível consultar seu saldo. Tente novamente mais tarde.")
        return result
    try:
        quota = QuotaStore(config).snapshot(user.id)
    except psycopg.Error:
        result.update(status="unavailable", message="Não foi possível consultar seu saldo. Tente novamente mais tarde.")
        return result
    result["quota"] = quota
    if result["status"] == "paused":
        return result
    if quota["remaining"] == 0:
        result.update(status="exhausted", message="Você usou suas perguntas da demonstração. Continue explorando o painel.")
    elif not quota["daily_available"]:
        result.update(status="daily_limit", message="A cota de IA terminou por hoje. O painel continua disponível.")
    elif quota["retry_after_seconds"]:
        result.update(status="cooldown", message="Aguarde alguns segundos antes de enviar outra pergunta.")
    else:
        result.update(status="ready", can_ask=True, message="Acesso confirmado. Faça sua pergunta sobre os dados.")
    return result
