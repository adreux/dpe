"""Sérialisation JSON des résultats du moteur de comparaison."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat() if not pd.isna(value) else None
    if isinstance(value, float) and pd.isna(value):
        return None
    if pd.api.types.is_scalar(value) and pd.isna(value):
        return None
    return value


def to_json_safe(report: dict[str, Any]) -> dict[str, Any]:
    """Convertit un rapport de comparaison (issu de `build_comparison_report`)
    en structure sérialisable en JSON (Timestamp -> isoformat, NaN -> None,
    Categorical -> str).
    """
    safe_records = [
        {key: _json_safe(value) for key, value in record.items()}
        for record in report["logements_comparables"]
    ]
    return {**report, "logements_comparables": safe_records}


def save_comparison_report(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(to_json_safe(report), f, ensure_ascii=False, indent=2, default=str)
    logger.info("Rapport de comparaison sauvegardé dans %s", output_path)
    return output_path
