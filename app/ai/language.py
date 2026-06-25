"""Tiny heuristic language detector (French vs English).

Keeps the service dependency-light: no external NLP model required.
"""
from __future__ import annotations

import re

FRENCH_MARKERS = {
    "combien", "quel", "quelle", "quels", "quelles", "dans", "région",
    "region", "vaccinés", "vaccinés", "vaccine", "enfants", "campagne",
    "couverture", "montre", "moi", "le", "la", "les", "des", "du", "par",
    "plus", "qui", "où", "comment", "pourquoi", "personnes", "nombre",
    "département", "departement", "ont", "été", "pour", "avec",
}


def detect_language(text: str) -> str:
    """Return 'fr' or 'en'. Defaults to 'en' when ambiguous."""
    tokens = set(re.findall(r"[a-zà-ÿ]+", text.lower()))
    score = len(tokens & FRENCH_MARKERS)
    # Accented chars strongly suggest French.
    if re.search(r"[àâçéèêëîïôûùüÿœ]", text.lower()):
        score += 2
    return "fr" if score >= 1 else "en"
