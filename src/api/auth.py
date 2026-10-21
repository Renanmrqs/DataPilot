"""Complete Neon's callback exchange and keep session cookies first-party."""
import base64
from http.cookies import SimpleCookie
import logging
import re
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from src.api.deployment import public_settings


router = APIRouter(prefix="/api/auth")
COOKIE_PREFIX = "datapilot_auth_"
VERIFIER = "neon_auth_session_verifier"
UPSTREAM_COOKIE = re.compile(r"^(?:__Secure-)?(?:neon-auth|neonauth)\.(?:session_token|session_challenge|session_challange)$")


class AuthAccessLogFilter(logging.Filter):
    """Keep one-time callback credentials out of Uvicorn's access log."""
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, target, version, status = record.args
            if isinstance(target, str) and (VERIFIER in target or target.split("?", 1)[0] == "/api/auth/callback"):
                record.args = (client, method, target.split("?", 1)[0] + "?[auth-callback]", version, status)
        return True


def configure_auth_logging():
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, AuthAccessLogFilter) for item in logger.filters):
        logger.addFilter(AuthAccessLogFilter())


class MagicLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def upstream_client():
    return httpx.Client(timeout=15, follow_redirects=False)


def app_origin(request):
    # The Host must already be accepted by the hosting platform. Neon also
    # checks this origin against the project's configured trusted domains.
    return str(request.base_url).rstrip("/")


def check_same_origin(request):
    if request.headers.get("origin") != app_origin(request) or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Solicite o acesso pela página do DataPilot.")


def upstream_cookie_name(local_name):
    if not local_name.startswith(COOKIE_PREFIX):
        return None
    encoded = local_name.removeprefix(COOKIE_PREFIX)
    try:
        name = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("ascii")
    except (ValueError, UnicodeError):
        return None
    return name if UPSTREAM_COOKIE.fullmatch(name) else None


def local_cookie_name(upstream_name):
    return COOKIE_PREFIX + base64.urlsafe_b64encode(upstream_name.encode("ascii")).decode("ascii").rstrip("=")


def auth_headers(request):
    cookies = []
    for name, value in request.cookies.items():
        upstream_name = upstream_cookie_name(name)
        if upstream_name and not any(char in value for char in (";", "\r", "\n")):
            cookies.append(f"{upstream_name}={value}")
    return {
        "Origin": app_origin(request),
        "Cookie": "; ".join(cookies),
        "x-neon-auth-middleware": "true",
    }


def copy_auth_cookies(upstream, response, request):
    for header in upstream.headers.get_list("set-cookie"):
        parsed = SimpleCookie()
        # Partitioned is deliberately removed for first-party cookies and is
        # not understood by SimpleCookie on older supported Python versions.
        parsed.load(re.sub(r";\s*Partitioned(?=;|$)", "", header, flags=re.IGNORECASE))
        for name, cookie in parsed.items():
            if not UPSTREAM_COOKIE.fullmatch(name):
                continue
            max_age = cookie["max-age"]
            response.set_cookie(
                local_cookie_name(name), cookie.value,
                max_age=int(max_age) if re.fullmatch(r"-?\d+", max_age) else None,
                expires=cookie["expires"] or None,
                path="/api/auth", httponly=True, samesite="lax",
                secure=request.url.scheme == "https",
            )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"


def call_auth(request, method, path, **kwargs):
    config = public_settings()
    if not config.enabled or not config.auth_url:
        raise HTTPException(503, "O acesso por e-mail não está disponível neste ambiente.")
    try:
        with upstream_client() as client:
            return client.request(method, config.auth_url + path, headers=auth_headers(request), **kwargs)
    except httpx.RequestError as exc:
        raise HTTPException(503, "Não foi possível conectar ao serviço de acesso. Tente novamente mais tarde.") from exc


@router.post("/sign-in/magic-link")
def send_magic_link(payload: MagicLinkRequest, request: Request):
    check_same_origin(request)
    upstream = call_auth(request, "POST", "/sign-in/magic-link", json={
        "email": payload.email,
        # The browser cannot supply an arbitrary redirect destination.
        "callbackURL": app_origin(request) + "/api/auth/callback",
    })
    if not upstream.is_success:
        raise HTTPException(429 if upstream.status_code == 429 else 503,
                            "Não foi possível solicitar o link. Aguarde e tente novamente.")
    response = JSONResponse({"status": True})
    copy_auth_cookies(upstream, response, request)
    return response


@router.get("/callback", include_in_schema=False)
def auth_callback(request: Request):
    verifier = request.query_params.get(VERIFIER, "")
    if not verifier or len(verifier) > 4096:
        return callback_error("invalid_link")
    try:
        upstream = call_auth(request, "GET", "/get-session", params={VERIFIER: verifier})
        data = upstream.json() if upstream.is_success else None
    except (HTTPException, ValueError):
        return callback_error("session_unavailable")
    if not isinstance(data, dict) or not data.get("session") or not data.get("user"):
        return callback_error("invalid_link")
    response = RedirectResponse("/#assistant", status_code=303)
    copy_auth_cookies(upstream, response, request)
    return response


def callback_error(code):
    response = RedirectResponse("/?" + urlencode({"auth_error": code}) + "#assistant", status_code=303)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/token")
def session_token(request: Request):
    upstream = call_auth(request, "GET", "/token")
    if upstream.status_code in (401, 403):
        response = JSONResponse({"message": "Entre pelo link enviado ao seu e-mail."}, status_code=401)
    elif not upstream.is_success:
        raise HTTPException(503, "Não foi possível recuperar seu acesso. Tente novamente.")
    else:
        try:
            token = upstream.json().get("token")
        except (ValueError, AttributeError):
            token = None
        if not isinstance(token, str) or not token:
            raise HTTPException(503, "O serviço de acesso não retornou uma credencial válida.")
        response = JSONResponse({"token": token})
    copy_auth_cookies(upstream, response, request)
    return response


@router.post("/sign-out")
def sign_out(request: Request):
    check_same_origin(request)
    upstream = call_auth(request, "POST", "/sign-out", json={})
    if not upstream.is_success and upstream.status_code != 401:
        raise HTTPException(503, "Não foi possível encerrar seu acesso. Tente novamente.")
    response = JSONResponse({"success": True})
    copy_auth_cookies(upstream, response, request)
    for name in request.cookies:
        if upstream_cookie_name(name):
            response.delete_cookie(name, path="/api/auth", secure=request.url.scheme == "https", httponly=True, samesite="lax")
    return response
