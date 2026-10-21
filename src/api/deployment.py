"""Guard both AI routes with verified identity and persistent demo quotas."""
from dataclasses import dataclass

import psycopg
from fastapi import HTTPException, Request

from src.ai.copilot import settings as provider_settings
from src.demo.auth import DemoUser, verified_user
from src.demo.config import DemoSettings, demo_settings
from src.demo.quota import QuotaStore


def public_settings():
    try:
        return demo_settings()
    except (ValueError, TypeError) as exc:
        raise HTTPException(503, "A demonstração está temporariamente indisponível por configuração.") from exc


def provider_ready(config):
    if not config.ready:
        return False
    try:
        provider = provider_settings(config.provider)
    except HTTPException:
        return False
    return bool(provider["key"] and provider["base_url"] and config.model in provider["models"])


@dataclass
class DemoAccess:
    settings: DemoSettings
    user: DemoUser

    def reserve(self, provider, model):
        if (provider, model) != (self.settings.provider, self.settings.model):
            raise HTTPException(422, "Use o modelo disponível nesta demonstração.")
        try:
            return QuotaStore(self.settings).reserve(self.user.id)
        except psycopg.Error as exc:
            raise HTTPException(503, "Não foi possível confirmar seu saldo. Nenhuma pergunta foi enviada à IA.") from exc


def require_ai_access(request: Request):
    config = public_settings()
    if not config.enabled:
        return None
    if not config.ai_enabled or not provider_ready(config):
        raise HTTPException(
            503, "O chat da demonstração está temporariamente indisponível. "
            "Você pode continuar explorando o painel e os filtros.",
        )
    user = verified_user(request, config)
    return DemoAccess(config, user)
