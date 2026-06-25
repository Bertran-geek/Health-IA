"""API route definitions."""
import logging
import time

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app import __version__
from app.ai.graph import run_pipeline
from app.ai.language import detect_language
from app.ai.llm import llm_available
from app.config import settings
from app.database.connection import check_database
from app.database.schema_reader import discover_schema, with_row_counts
from app.models.schemas import (
    ChartSpec,
    HealthResponse,
    LoginRequest,
    QueryRequest,
    QueryResponse,
    SchemaResponse,
    TokenResponse,
)
from app.security.auth import create_access_token, require_auth, verify_credentials
from app.security.rate_limit import limiter
from app.services.cache import cache_status, get_cached, set_cached

logger = logging.getLogger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest) -> TokenResponse:
    """Exchange admin credentials for a JWT (demo issuer)."""
    if not verify_credentials(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token, expires_in = create_access_token(body.username)
    return TokenResponse(access_token=token, expires_in=expires_in)


# --------------------------------------------------------------------------- #
# AI query
# --------------------------------------------------------------------------- #
@router.post("/ai/query", response_model=QueryResponse, tags=["ai"])
@limiter.limit(settings.rate_limit)
def ai_query(
    request: Request,
    body: QueryRequest = Body(...),
    principal: str = Depends(require_auth),
) -> QueryResponse:
    """Convert a natural-language question into a safe SQL query and answer."""
    start = time.perf_counter()
    language = body.language or detect_language(body.question)

    # Cache lookup
    cached = get_cached(body.question, language)
    if cached:
        cached["cached"] = True
        cached["elapsed_ms"] = int((time.perf_counter() - start) * 1000)
        return QueryResponse(**cached)

    try:
        result = run_pipeline(
            question=body.question,
            language=language,
            include_chart=body.include_chart,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI pipeline error: {exc}",
        ) from exc

    chart_obj = result.get("chart")
    response = QueryResponse(
        answer=result.get("answer", ""),
        sql=result.get("sql", ""),
        columns=result.get("columns", []),
        rows=result.get("rows", []),
        row_count=len(result.get("rows", [])),
        chart=ChartSpec(**chart_obj) if chart_obj else None,
        trend=result.get("trend"),
        language=language,
        cached=False,
        elapsed_ms=int((time.perf_counter() - start) * 1000),
    )

    # Cache successful answers only.
    if not result.get("error"):
        set_cached(body.question, language, response.model_dump())

    return response


# --------------------------------------------------------------------------- #
# Schema metadata
# --------------------------------------------------------------------------- #
@router.get("/ai/schema", response_model=SchemaResponse, tags=["ai"])
def get_schema(
    counts: bool = False,
    principal: str = Depends(require_auth),
) -> SchemaResponse:
    """Return the auto-discovered database schema."""
    schema = discover_schema(refresh=False)
    if counts:
        schema = with_row_counts(schema)
    return schema


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Public health probe (no auth)."""
    db_ok = check_database()
    llm_ok = llm_available()
    overall = "ok" if (db_ok and llm_ok) else "degraded"
    return HealthResponse(
        status=overall,
        database="up" if db_ok else "down",
        llm="up" if llm_ok else "down",
        cache=cache_status(),
        version=__version__,
    )
