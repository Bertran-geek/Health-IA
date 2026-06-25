"""Automatic schema discovery using SQLAlchemy inspection.

The reader introspects the live database, builds a structured representation of
every table (columns, types, foreign keys) and produces a compact textual
description that is injected into the LLM prompt as grounding context.

Results are cached in memory to avoid repeated introspection on every request.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from sqlalchemy import inspect, text

from app.config import settings
from app.database.connection import get_engine
from app.models.schemas import (
    ColumnInfo,
    ForeignKeyInfo,
    SchemaResponse,
    TableInfo,
)

logger = logging.getLogger(__name__)

# In-memory cache
_CACHE: Dict[str, object] = {}
_CACHE_TS: float = 0.0
_CACHE_TTL = 600  # seconds


def _database_name() -> str:
    url = settings.db_url
    return url.rsplit("/", 1)[-1].split("?")[0]


def discover_schema(refresh: bool = False) -> SchemaResponse:
    """Introspect the database and return a structured schema description."""
    global _CACHE_TS
    now = time.time()
    if not refresh and "schema" in _CACHE and (now - _CACHE_TS) < _CACHE_TTL:
        return _CACHE["schema"]  # type: ignore[return-value]

    engine = get_engine()
    inspector = inspect(engine)
    tables: List[TableInfo] = []

    for table_name in sorted(inspector.get_table_names()):
        columns: List[ColumnInfo] = []
        pk_cols = set(inspector.get_pk_constraint(table_name).get("constrained_columns", []))
        for col in inspector.get_columns(table_name):
            columns.append(
                ColumnInfo(
                    name=col["name"],
                    type=str(col["type"]),
                    nullable=bool(col.get("nullable", True)),
                    primary_key=col["name"] in pk_cols,
                )
            )

        fks: List[ForeignKeyInfo] = []
        for fk in inspector.get_foreign_keys(table_name):
            ref_table = fk.get("referred_table")
            constrained = fk.get("constrained_columns") or []
            referred = fk.get("referred_columns") or []
            for local_col, ref_col in zip(constrained, referred):
                fks.append(
                    ForeignKeyInfo(
                        column=local_col,
                        references_table=ref_table,
                        references_column=ref_col,
                    )
                )

        tables.append(TableInfo(name=table_name, columns=columns, foreign_keys=fks))

    schema = SchemaResponse(
        database=_database_name(),
        table_count=len(tables),
        tables=tables,
    )

    _CACHE["schema"] = schema
    _CACHE_TS = now
    logger.info("Discovered schema: %d tables", len(tables))
    return schema


def with_row_counts(schema: SchemaResponse) -> SchemaResponse:
    """Augment the schema with approximate row counts (best effort)."""
    engine = get_engine()
    with engine.connect() as conn:
        for tbl in schema.tables:
            try:
                count = conn.execute(
                    text(f"SELECT COUNT(*) FROM `{tbl.name}`")
                ).scalar()
                tbl.row_count = int(count) if count is not None else None
            except Exception:  # noqa: BLE001
                tbl.row_count = None
    return schema


# Curated domain hints that help the LLM reason about this specific schema.
DOMAIN_HINTS = """
DOMAIN KNOWLEDGE (Health Campaign Manager):
- Geographic hierarchy: region (id_region) -> departement (id_dpt, FK id_region)
  -> phc (id_phc, FK id_dpt) -> chw (id_chw, FK id_phc) -> target (FK chw_id).
- `chw` = Community Health Worker (ASBC). `phc` = Primary Health Center (CSPS).
- `target` rows are the individuals/cibles. Column `vaccinate` (BOOLEAN, 1/0)
  marks a vaccinated person. Column `beneficiaire` (BOOLEAN) marks a beneficiary.
- A target belongs to a campaign through `target.id_campain` -> campaign.id_campaign.
- A target belongs to a CHW through `target.chw_id` -> chw.id_chw.
- Region name column is `region.nom_region`. Department name is `departement.nom_dpt`.
- CHW name columns are `chw.nom` and `chw.prenom`.
- Vaccination coverage % = SUM(target.vaccinate) / COUNT(target.id_target) * 100.
- To filter targets by region you must JOIN target->chw->phc->departement->region.
- campaign.type_campagne ENUM: VACCINATION, DEPISTAGE, SUPPLEMENTATION,
  SENSIBILISATION, TRAITEMENT. campaign.actif (BOOLEAN) marks active campaigns.
- Age groups: 0-4, 5-14, 15-59, 60+ using target.age.
"""


def build_schema_context(schema: Optional[SchemaResponse] = None) -> str:
    """Render a compact text block describing the schema for the LLM prompt."""
    schema = schema or discover_schema()
    lines: List[str] = ["DATABASE SCHEMA:"]
    for tbl in schema.tables:
        cols = ", ".join(
            f"{c.name} {c.type}{' PK' if c.primary_key else ''}"
            for c in tbl.columns
        )
        lines.append(f"- {tbl.name}({cols})")
        for fk in tbl.foreign_keys:
            lines.append(
                f"    FK {tbl.name}.{fk.column} -> "
                f"{fk.references_table}.{fk.references_column}"
            )
    lines.append(DOMAIN_HINTS)
    return "\n".join(lines)
