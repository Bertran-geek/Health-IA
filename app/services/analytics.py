"""Analytics helpers: chart generation and trend interpretation.

- build_chart: inspects the result set and, when it is a simple
  label/value (or label/series) shape, produces a chart spec plus a base64
  PNG rendered with matplotlib (Agg backend, no display needed).
- describe_trend: produces a short textual trend interpretation (direction,
  min/max, average) in French or English.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt  # noqa: E402

logger = logging.getLogger(__name__)


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _numeric_columns(columns: List[str], rows: List[Dict[str, Any]]) -> List[str]:
    numeric: List[str] = []
    for col in columns:
        vals = [r.get(col) for r in rows if r.get(col) is not None]
        if vals and all(_is_number(v) for v in vals):
            numeric.append(col)
    return numeric


def build_chart(
    columns: List[str], rows: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Return a chart spec (dict matching ChartSpec) or None when unsuitable."""
    if not rows or len(rows) < 1 or len(columns) < 2:
        return None
    if len(rows) > 50:  # too many points to chart meaningfully
        return None

    numeric_cols = _numeric_columns(columns, rows)
    if not numeric_cols:
        return None

    # Label column = first non-numeric column, else first column.
    label_col = next((c for c in columns if c not in numeric_cols), columns[0])
    value_cols = [c for c in numeric_cols if c != label_col][:3]
    if not value_cols:
        return None

    labels = [str(r.get(label_col, "")) for r in rows]
    series = []
    for vc in value_cols:
        series.append(
            {
                "name": vc,
                "data": [float(r.get(vc) or 0) for r in rows],
            }
        )

    # Choose chart type heuristically.
    if len(rows) <= 6 and len(value_cols) == 1:
        chart_type = "pie"
    elif any(k in label_col.lower() for k in ("date", "annee", "year", "month", "mois")):
        chart_type = "line"
    else:
        chart_type = "bar"

    image_b64 = _render_png(chart_type, labels, series, label_col)

    return {
        "type": chart_type,
        "title": f"{', '.join(value_cols)} by {label_col}",
        "x": labels,
        "series": series,
        "image_base64": image_b64,
    }


def _render_png(
    chart_type: str,
    labels: List[str],
    series: List[Dict[str, Any]],
    label_col: str,
) -> Optional[str]:
    try:
        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=100)

        if chart_type == "pie" and series:
            ax.pie(series[0]["data"], labels=labels, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
        elif chart_type == "line":
            for s in series:
                ax.plot(labels, s["data"], marker="o", label=s["name"])
            ax.set_xlabel(label_col)
            ax.legend()
            plt.xticks(rotation=45, ha="right")
        else:  # bar
            import numpy as np

            x = np.arange(len(labels))
            width = 0.8 / max(len(series), 1)
            for i, s in enumerate(series):
                ax.bar(x + i * width, s["data"], width, label=s["name"])
            ax.set_xticks(x + width * (len(series) - 1) / 2)
            ax.set_xticklabels(labels, rotation=45, ha="right")
            ax.set_xlabel(label_col)
            ax.legend()

        ax.set_title(f"{', '.join(s['name'] for s in series)} by {label_col}")
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chart rendering failed: %s", exc)
        plt.close("all")
        return None


def describe_trend(
    columns: List[str], rows: List[Dict[str, Any]], language: str
) -> Optional[str]:
    """Produce a short textual trend interpretation for a numeric series."""
    if not rows or len(rows) < 2:
        return None
    numeric_cols = _numeric_columns(columns, rows)
    if not numeric_cols:
        return None

    col = numeric_cols[0]
    values = [float(r.get(col) or 0) for r in rows]
    first, last = values[0], values[-1]
    vmin, vmax = min(values), max(values)
    avg = sum(values) / len(values)

    if last > first:
        direction_fr, direction_en = "à la hausse", "increasing"
    elif last < first:
        direction_fr, direction_en = "à la baisse", "decreasing"
    else:
        direction_fr, direction_en = "stable", "stable"

    if language == "fr":
        return (
            f"Tendance {direction_fr} pour « {col} » : "
            f"de {first:g} à {last:g} (min {vmin:g}, max {vmax:g}, "
            f"moyenne {avg:.1f})."
        )
    return (
        f"Trend is {direction_en} for '{col}': "
        f"from {first:g} to {last:g} (min {vmin:g}, max {vmax:g}, "
        f"avg {avg:.1f})."
    )
