"""Pydantic request/response models for the API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    username: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["admin123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# --------------------------------------------------------------------------- #
# AI query
# --------------------------------------------------------------------------- #
class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        examples=["Combien d'enfants ont été vaccinés dans la région du Centre ?"],
    )
    language: Optional[str] = Field(
        default=None,
        description="Force the answer language: 'fr' or 'en'. Auto-detected if omitted.",
    )
    include_chart: bool = Field(
        default=True,
        description="Return a chart spec + base64 PNG when the result is tabular.",
    )


class ChartSpec(BaseModel):
    type: str = Field(description="bar | line | pie")
    title: str
    x: List[str] = []
    series: List[Dict[str, Any]] = []
    image_base64: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sql: str
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []
    row_count: int = 0
    chart: Optional[ChartSpec] = None
    trend: Optional[str] = None
    language: str = "en"
    cached: bool = False
    elapsed_ms: int = 0


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #
class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool = False


class ForeignKeyInfo(BaseModel):
    column: str
    references_table: str
    references_column: str


class TableInfo(BaseModel):
    name: str
    columns: List[ColumnInfo]
    foreign_keys: List[ForeignKeyInfo] = []
    row_count: Optional[int] = None


class SchemaResponse(BaseModel):
    database: str
    table_count: int
    tables: List[TableInfo]


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
class HealthResponse(BaseModel):
    status: str
    database: str
    llm: str
    cache: str
    version: str


class ErrorResponse(BaseModel):
    detail: str
