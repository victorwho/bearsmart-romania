from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles

from .auth import (
    Session,
    Role,
    SESSION_COOKIE,
    attach_session,
    clear_session,
    current_session,
    install_redirect_handler,
    require_role,
)
from .bearsmart_mvp import (
    MVP_DIR,
    bearsmart_community_index,
    bearsmart_dashboard_index,
    bearsmart_index,
    bearsmart_localities_index,
    bearsmart_map_index,
    bearsmart_ops_index,
    bearsmart_report_index,
    router as bearsmart_router,
)
from .flags import current_flags
from .telemetry import recent_events, track
from .models import (
    HealthResponse,
    RetailerListResponse,
    RetailerLinkListResponse,
    RetailerLinkResponse,
    ProductSearchRequest,
    ProductSearchResponse,
    RoutineRequest,
    RoutineResponse,
    ProductResponse,
)
from .engine import RevoxEngine

ENABLE_DOCS = os.getenv("ENABLE_DOCS", "false").strip().lower() in {"1", "true", "yes", "on"}
APP_VERSION = "1.3.0-public"
PRIVACY_PATH = Path(__file__).resolve().parents[1] / "data" / "privacy_policy.md"
GPT_ACTION_PATHS = {
    "/retailer-links/{retailer}",
    "/products/{product_id}",
    "/routine/recommend",
}

app = FastAPI(
    title="Revox Routine API",
    version=APP_VERSION,
    description=(
        "Public Revox routine recommendation API for GPT Actions. "
        "Deterministic product filtering built from the provided catalog and links.txt."
    ),
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/bearsmart-static", StaticFiles(directory=MVP_DIR), name="bearsmart-static")
app.mount("/logo", StaticFiles(directory=Path(__file__).resolve().parents[1] / "logo"), name="bearsmart-logo")
app.include_router(bearsmart_router)
install_redirect_handler(app)

engine = RevoxEngine()


def _collect_schema_refs(node: Any, refs: set[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            refs.add(ref.rsplit("/", 1)[-1])
        for value in node.values():
            _collect_schema_refs(value, refs)
        return
    if isinstance(node, list):
        for item in node:
            _collect_schema_refs(item, refs)


def _collect_nested_schema_refs(name: str, schemas: dict[str, Any], collected: set[str]) -> None:
    if name in collected or name not in schemas:
        return
    collected.add(name)
    nested_refs: set[str] = set()
    _collect_schema_refs(schemas[name], nested_refs)
    for nested_name in nested_refs:
        _collect_nested_schema_refs(nested_name, schemas, collected)


def get_public_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",", 1)[0].strip()
    scheme = forwarded_proto or request.url.scheme
    host = forwarded_host or request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}".rstrip("/")


def build_gpt_openapi_schema(base_url: str) -> dict[str, Any]:
    schema = deepcopy(app.openapi())
    schema["paths"] = {path: value for path, value in schema.get("paths", {}).items() if path in GPT_ACTION_PATHS}
    schema["paths"]["/routine/recommend"]["post"]["x-openai-isConsequential"] = False

    all_schemas = schema.get("components", {}).get("schemas", {})
    direct_refs: set[str] = set()
    _collect_schema_refs(schema["paths"], direct_refs)

    required_schemas: set[str] = set()
    for name in direct_refs:
        _collect_nested_schema_refs(name, all_schemas, required_schemas)

    schema["components"] = {
        "schemas": {name: all_schemas[name] for name in sorted(required_schemas) if name in all_schemas}
    }
    schema["servers"] = [{"url": base_url.rstrip("/")}]
    schema["info"]["description"] = (
        "Public Revox routine recommendation API schema for GPT Actions. "
        "This contract is intentionally limited to the endpoints the GPT should call."
    )
    return schema


@app.get("/", tags=["meta"], include_in_schema=False)
def root() -> dict:
    return {
        "name": app.title,
        "version": app.version,
        "status": "ok",
        "openapi": "/openapi.json",
        "openapi_gpt": "/openapi-gpt.json",
        "privacy_policy": "/privacy-policy",
        "bearsmart_mvp": "/bearsmart",
    }


@app.get("/home", response_class=HTMLResponse, include_in_schema=False)
def home() -> HTMLResponse:
    # Clean URL for the public map; mirrors /bearsmart without breaking the
    # JSON contract used by the GPT Action at `/`.
    return bearsmart_index()


@app.get("/bearsmart", response_class=HTMLResponse, include_in_schema=False)
def bearsmart_demo():
    return bearsmart_index()


@app.get("/bearsmart/map", response_class=HTMLResponse, include_in_schema=False)
def bearsmart_map_demo():
    return bearsmart_map_index()


@app.get("/bearsmart/localities", response_class=HTMLResponse, include_in_schema=False)
def bearsmart_localities_demo():
    return bearsmart_localities_index()


@app.get("/bearsmart/dashboard", response_class=HTMLResponse, include_in_schema=False)
def bearsmart_dashboard_demo():
    return bearsmart_dashboard_index()


@app.get("/bearsmart/report", response_class=HTMLResponse, include_in_schema=False)
def bearsmart_report_demo():
    return bearsmart_report_index()


@app.get("/bearsmart/community", response_class=HTMLResponse, include_in_schema=False)
def bearsmart_community_demo():
    return RedirectResponse(url="/bearsmart", status_code=307)


@app.get("/bearsmart/community-hidden", response_class=HTMLResponse, include_in_schema=False)
def bearsmart_community_hidden_demo():
    return bearsmart_community_index()


@app.get("/bearsmart/ops", response_class=HTMLResponse, include_in_schema=False)
def bearsmart_ops_demo(request: Request) -> Response:
    # Ops console moved behind the authenticated workspace per H1.1.
    target = "/workspace/ops"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@app.get("/health", response_model=HealthResponse, tags=["meta"], operation_id="getHealth")
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        product_count=engine.product_count,
        retailer_count=len(engine.retailers),
        retailer_link_count=len(engine.retailer_links),
        version=app.version,
    )


@app.get("/privacy-policy", response_class=PlainTextResponse, tags=["meta"], include_in_schema=False)
def privacy_policy() -> str:
    if PRIVACY_PATH.exists():
        return PRIVACY_PATH.read_text(encoding="utf-8")
    return "Privacy policy placeholder. Replace this text before publishing the GPT in the Store."


@app.get("/privacy-policy.html", response_class=HTMLResponse, tags=["meta"], include_in_schema=False)
def privacy_policy_html() -> str:
    text = privacy_policy()
    html_body = "<br>".join(
        line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for line in text.splitlines()
    )
    return f"<html><body><pre style='white-space:pre-wrap;font-family:system-ui,sans-serif'>{html_body}</pre></body></html>"


@app.get("/openapi-gpt.json", response_class=JSONResponse, tags=["meta"], include_in_schema=False)
def openapi_gpt(request: Request) -> JSONResponse:
    return JSONResponse(build_gpt_openapi_schema(get_public_base_url(request)))


@app.get("/retailers", response_model=RetailerListResponse, tags=["meta"], operation_id="listRetailers")
def retailers() -> RetailerListResponse:
    return RetailerListResponse(retailers=engine.retailers)


@app.get("/retailer-links", response_model=RetailerLinkListResponse, tags=["meta"], operation_id="listRetailerLinks")
def retailer_links() -> RetailerLinkListResponse:
    return engine.list_retailer_links()


@app.get("/retailer-links/{retailer}", response_model=RetailerLinkResponse, tags=["meta"], operation_id="getRetailerLink")
def retailer_link(retailer: str) -> RetailerLinkResponse:
    return engine.get_retailer_link(retailer)


@app.get("/products/{product_id}", response_model=ProductResponse, tags=["catalog"], operation_id="getProductById")
def get_product(product_id: str) -> ProductResponse:
    return engine.get_product_response(product_id)


@app.post("/products/search", response_model=ProductSearchResponse, tags=["catalog"], operation_id="searchProducts")
def search_products(payload: ProductSearchRequest) -> ProductSearchResponse:
    return engine.search_products(payload)


@app.post("/routine/recommend", response_model=RoutineResponse, tags=["routine"], operation_id="recommendRoutine")
def recommend_routine(payload: RoutineRequest) -> RoutineResponse:
    return engine.recommend_routine(payload)


# ---------------------------------------------------------------------------
# H0 / H1 — session, workspace, flags, telemetry surfaces
# ---------------------------------------------------------------------------


def _login_page(next_path: str, error: str | None = None) -> str:
    safe_next = next_path.replace('"', "")
    error_block = (
        f'<p class="login-error" role="alert">{error}</p>' if error else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BearSmart Romania | Sign in</title>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@600;700;800&family=Public+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/bearsmart-static/styles.css">
</head>
<body>
  <main class="login-page">
    <section class="login-card">
      <img class="brand-logo" src="/logo/bearsmart-logo-light.svg" alt="BearSmart logo">
      <p class="eyebrow">Workspace access</p>
      <h1 class="hero-title">Sign in to BearSmart</h1>
      <p class="section-copy">Town administrators, moderators, and reviewers sign in here. Residents and visitors stay on the public map.</p>
      {error_block}
      <form method="post" action="/login" class="report-form-grid">
        <input type="hidden" name="next" value="{safe_next}">
        <label class="field-help" for="email">Email</label>
        <input id="email" name="email" type="email" placeholder="you@town.ro" required>
        <label class="field-help" for="role">Role</label>
        <select id="role" name="role">
          <option value="resident">Resident</option>
          <option value="town_admin">Town Admin</option>
          <option value="moderator">Moderator</option>
          <option value="reviewer">Reviewer</option>
          <option value="super_admin">Super Admin</option>
        </select>
        <button class="button button-primary" type="submit">Continue</button>
      </form>
      <p class="section-copy subtle"><a class="nav-link" href="/bearsmart">&larr; Back to the public map</a></p>
    </section>
  </main>
</body>
</html>
"""


_DEMO_LOGIN_ACCEPT_ROLES: set[str] = {
    "resident",
    "tourist",
    "town_admin",
    "moderator",
    "reviewer",
    "super_admin",
}


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_form(request: Request, next: str = "/workspace") -> HTMLResponse:  # noqa: A002
    return HTMLResponse(_login_page(next_path=next))


async def _read_form_fields(request: Request) -> dict[str, str]:
    """Parse ``application/x-www-form-urlencoded`` body without multipart.

    Using the raw body keeps the runtime dependency surface identical to the
    existing app (no ``python-multipart``).
    """
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        payload = await request.json()
        return {str(k): str(v) for k, v in (payload or {}).items()}
    body = (await request.body()).decode("utf-8")
    from urllib.parse import parse_qs

    parsed = parse_qs(body, keep_blank_values=True)
    return {k: (v[-1] if v else "") for k, v in parsed.items()}


@app.post("/login", include_in_schema=False)
async def login_submit(request: Request) -> Response:
    form = await _read_form_fields(request)
    email = form.get("email", "").strip()
    role = form.get("role", "").strip()
    next_path = form.get("next") or "/workspace"
    if not email or role not in _DEMO_LOGIN_ACCEPT_ROLES:
        return HTMLResponse(
            _login_page(next_path, error="Enter an email and pick a role."),
            status_code=400,
        )
    session = Session(role=role, email=email)  # type: ignore[arg-type]
    response = RedirectResponse(url=next_path, status_code=303)
    attach_session(response, session)
    track("session_started", role=role, email=email)
    return response


@app.post("/logout", include_in_schema=False)
def logout() -> Response:
    response = RedirectResponse(url="/bearsmart", status_code=303)
    clear_session(response)
    return response


@app.get("/workspace", response_class=HTMLResponse, include_in_schema=False)
def workspace_home(
    request: Request,
    session: Session = Depends(
        require_role("town_admin", "moderator", "reviewer", "super_admin")
    ),
) -> HTMLResponse:
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang=\"en\"><head><meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>BearSmart Workspace</title>
<link href=\"https://fonts.googleapis.com/css2?family=Manrope:wght@600;700;800&family=Public+Sans:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">
<link rel=\"stylesheet\" href=\"/bearsmart-static/styles.css\">
</head><body>
<header class=\"app-header\">
  <div class=\"brand-row\">
    <img class=\"brand-logo\" src=\"/logo/bearsmart-logo-light.svg\" alt=\"BearSmart logo\">
    <div class=\"brand-text\"><p class=\"eyebrow\">Workspace</p><h1 class=\"brand-title\">Signed in as {session.role}</h1></div>
  </div>
  <div class=\"header-right\">
    <a class=\"button button-secondary\" href=\"/bearsmart\">Public map</a>
    <form method=\"post\" action=\"/logout\" style=\"display:inline\"><button class=\"button button-ghost\" type=\"submit\">Sign out</button></form>
  </div>
</header>
<main class=\"page-content\">
  <section class=\"page-hero\"><p class=\"eyebrow\">Workspace home</p>
  <h2 class=\"hero-title\">Choose an operations surface</h2>
  <p class=\"section-copy\">Admin consoles moved off the public home screen. Pick a tool below.</p></section>
  <div class=\"ops-grid\">
    <a class=\"ops-card\" href=\"/workspace/ops\"><p class=\"eyebrow\">Operations</p><h3 class=\"section-title\">Moderation &amp; certification</h3><p class=\"section-copy\">Age-in-queue badges, SLA tracking, reviewer decisions.</p></a>
  </div>
</main>
</body></html>"""
    )


@app.get("/workspace/ops", response_class=HTMLResponse, include_in_schema=False)
def workspace_ops(
    _session: Session = Depends(
        require_role("town_admin", "moderator", "reviewer", "super_admin")
    ),
) -> FileResponse:
    return FileResponse(MVP_DIR / "ops.html")


@app.get("/api/flags", include_in_schema=False)
def get_flags() -> JSONResponse:
    return JSONResponse(current_flags().as_dict())


@app.get("/api/session", include_in_schema=False)
def get_session(request: Request) -> JSONResponse:
    session = current_session(request)
    return JSONResponse(
        {
            "role": session.role,
            "email": session.email,
            "town_slug": session.town_slug,
            "authenticated": session.role != "public"
            and request.cookies.get(SESSION_COOKIE) is not None,
        }
    )


@app.post("/api/telemetry", include_in_schema=False)
async def post_telemetry(request: Request) -> JSONResponse:
    payload = await request.json()
    name = str(payload.get("name", "")).strip()
    if not name:
        return JSONResponse({"detail": "event name is required"}, status_code=400)
    props = payload.get("props") or {}
    if not isinstance(props, dict):
        return JSONResponse({"detail": "props must be an object"}, status_code=400)
    event = track(name, **props)
    return JSONResponse({"recorded": True, "timestamp": event.timestamp})


@app.get("/api/telemetry/recent", include_in_schema=False)
def get_recent_telemetry(
    _session: Session = Depends(require_role("super_admin")),
    limit: int = 100,
) -> JSONResponse:
    events = recent_events(limit=limit)
    return JSONResponse(
        {"items": [{"name": e.name, "props": e.props, "timestamp": e.timestamp} for e in events]}
    )
