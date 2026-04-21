"""Signed-cookie session layer and role guards for BearSmart.

Replaces the demo `X-Demo-Role` header hack with a real session model while
remaining backwards compatible during the H0/H1 rollout: requests that do not
carry a session cookie fall back to the legacy header so existing tests and
demo flows keep working until Horizon 2 migrates callers.

References: IMPLEMENTATION_PLAN.md §0.1.
"""

from __future__ import annotations

import hmac
import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Callable, Iterable, Literal

from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse

Role = Literal[
    "public",
    "resident",
    "tourist",
    "town_admin",
    "moderator",
    "reviewer",
    "super_admin",
]

ALL_ROLES: tuple[Role, ...] = (
    "public",
    "resident",
    "tourist",
    "town_admin",
    "moderator",
    "reviewer",
    "super_admin",
)

# Backwards-compatible subset still accepted by the demo header path.
LEGACY_HEADER_ROLES: frozenset[Role] = frozenset(
    {"public", "resident", "town_admin", "moderator", "reviewer"}
)

SESSION_COOKIE = "bearsmart_session"
SESSION_SECRET_ENV = "BEARSMART_SESSION_SECRET"
# Dev-only default. Production must set BEARSMART_SESSION_SECRET.
_DEV_SECRET = "bearsmart-dev-secret-change-me"


@dataclass(frozen=True)
class Session:
    role: Role
    email: str | None = None
    town_slug: str | None = None


def _secret() -> bytes:
    return os.environ.get(SESSION_SECRET_ENV, _DEV_SECRET).encode("utf-8")


def _sign(payload: bytes) -> str:
    mac = hmac.new(_secret(), payload, sha256).digest()
    return urlsafe_b64encode(mac).rstrip(b"=").decode("ascii")


def encode_session(session: Session) -> str:
    body = json.dumps(
        {"role": session.role, "email": session.email, "town_slug": session.town_slug},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    token = urlsafe_b64encode(body).rstrip(b"=").decode("ascii")
    return f"{token}.{_sign(body)}"


def decode_session(raw: str) -> Session | None:
    try:
        token, signature = raw.split(".", 1)
    except ValueError:
        return None
    padded = token + "=" * (-len(token) % 4)
    try:
        body = urlsafe_b64decode(padded.encode("ascii"))
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(_sign(body), signature):
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    role = data.get("role")
    if role not in ALL_ROLES:
        return None
    return Session(role=role, email=data.get("email"), town_slug=data.get("town_slug"))


def attach_session(response: Response, session: Session) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        encode_session(session),
        httponly=True,
        samesite="lax",
        secure=False,  # flip to True behind HTTPS proxy in prod.
        max_age=60 * 60 * 12,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def current_session(request: Request) -> Session:
    """Resolve the effective session for a request.

    Precedence:
      1. Valid signed session cookie.
      2. Legacy `X-Demo-Role` header (kept during H0/H1 compatibility window).
      3. Anonymous public role.
    """
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        decoded = decode_session(raw)
        if decoded is not None:
            return decoded

    header_role = (request.headers.get("x-demo-role") or "").strip().lower()
    if header_role:
        if header_role not in LEGACY_HEADER_ROLES:
            raise HTTPException(status_code=400, detail="Invalid demo role.")
        return Session(role=header_role)  # type: ignore[arg-type]

    return Session(role="public")


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return True
    path = request.url.path
    return path.startswith("/api/") or path.startswith("/workspace/api/")


def require_role(*allowed: Role) -> Callable[[Request], Session]:
    """FastAPI dependency that enforces role membership.

    For API requests returns 403 JSON; for HTML requests redirects to /login
    with a `next` parameter so the user can resume after signing in.
    """
    allowed_set: frozenset[Role] = frozenset(allowed)

    def _dep(request: Request) -> Session:
        session = current_session(request)
        if session.role in allowed_set:
            return session
        if _wants_json(request):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{session.role}' is not permitted for this action.",
            )
        target = request.url.path
        if request.url.query:
            target = f"{target}?{request.url.query}"
        raise _RedirectSignal(
            RedirectResponse(url=f"/login?next={target}", status_code=303)
        )

    return _dep


class _RedirectSignal(Exception):
    def __init__(self, response: RedirectResponse) -> None:
        super().__init__("redirect")
        self.response = response


def install_redirect_handler(app) -> None:
    """Register the signal so HTML redirects surface as proper responses."""

    @app.exception_handler(_RedirectSignal)
    async def _handle(_: Request, exc: _RedirectSignal) -> RedirectResponse:  # noqa: D401
        return exc.response


def upgrade_session_town(session: Session, town_slug: str) -> Session:
    """Return a copy of the session with its town slug set."""
    return replace(session, town_slug=town_slug)


def is_role_allowed(role: Role, allowed: Iterable[Role]) -> bool:
    return role in set(allowed)
