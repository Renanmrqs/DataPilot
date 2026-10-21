"""Verify Neon-issued identity tokens without trusting browser-supplied IDs."""
from dataclasses import dataclass
from functools import lru_cache
import logging

import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoUser:
    id: str
    email: str


@lru_cache(maxsize=4)
def key_client(auth_url):
    return PyJWKClient(auth_url + "/.well-known/jwks.json", cache_jwk_set=True, lifespan=300, timeout=10)


def verified_user(request: Request, settings):
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer ") or len(authorization) > 16000:
        raise HTTPException(401, "Confirme seu e-mail para experimentar a IA.")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = key_client(settings.auth_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key,
            algorithms=["EdDSA", "ES256", "RS256"],
            issuer=settings.auth_origin, audience=settings.auth_origin,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(503, "A confirmação de acesso está indisponível. Tente novamente mais tarde.") from exc
    except jwt.PyJWTError as exc:
        # Diagnostic category only: never log credentials, claims or email.
        logger.warning("Demo identity rejected: %s", type(exc).__name__)
        raise HTTPException(401, "Seu acesso expirou ou é inválido. Entre novamente pelo e-mail.") from exc
    if claims.get("emailVerified") is not True or claims.get("banned"):
        raise HTTPException(403, "Confirme seu e-mail antes de usar a IA.")
    if not isinstance(claims["sub"], str) or not claims["sub"] or not isinstance(claims.get("email"), str):
        raise HTTPException(401, "Não foi possível confirmar seu acesso.")
    return DemoUser(id=claims["sub"], email=claims["email"])
