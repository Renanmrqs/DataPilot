"""Server-owned settings for the public demonstration."""
import os
from dataclasses import dataclass
from urllib.parse import urlsplit


def positive_integer(name, default):
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class DemoSettings:
    enabled: bool
    ai_enabled: bool
    questions_per_user: int
    daily_questions: int
    cooldown_seconds: int
    provider: str
    model: str
    auth_url: str
    database_url: str

    alternate_provider: str = ""
    alternate_model: str = ""

    @property
    def allowed_models(self):
        pairs = [(self.provider, self.model)]
        if self.alternate_provider and self.alternate_model:
            pairs.append((self.alternate_provider, self.alternate_model))
        return list(dict.fromkeys(pairs))

    @property
    def ready(self):
        return bool(self.auth_url and self.database_url and self.provider and self.model)

    @property
    def auth_origin(self):
        parts = urlsplit(self.auth_url)
        return f"{parts.scheme}://{parts.netloc}"


def demo_settings():
    auth_url = os.getenv("NEON_AUTH_BASE_URL", "").strip().rstrip("/")
    if auth_url:
        parts = urlsplit(auth_url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("NEON_AUTH_BASE_URL must be an HTTPS service URL")
    return DemoSettings(
        # A deployed demo cannot bypass protection by setting DEMO_MODE=false.
        enabled=os.getenv("VERCEL") == "1" or os.getenv("DEMO_MODE", "").lower() == "true",
        ai_enabled=os.getenv("DEMO_AI_ENABLED", "false").lower() == "true",
        questions_per_user=positive_integer("DEMO_QUESTIONS_PER_USER", 4),
        daily_questions=positive_integer("DEMO_DAILY_QUESTIONS", 20),
        cooldown_seconds=positive_integer("DEMO_COOLDOWN_SECONDS", 15),
        provider=os.getenv("DEMO_PROVIDER", "").strip(),
        model=os.getenv("DEMO_MODEL", "").strip(),
        alternate_provider=os.getenv("DEMO_ALTERNATE_PROVIDER", "").strip(),
        alternate_model=os.getenv("DEMO_ALTERNATE_MODEL", "").strip(),
        auth_url=auth_url,
        database_url=os.getenv("NEON_DATABASE_URL", "").strip(),
    )
