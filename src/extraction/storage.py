"""Sauvegarde des données brutes extraites de l'API ADEME."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def raw_output_path(zip_code: str, output_dir: Path) -> Path:
    return output_dir / f"dpe_raw_{zip_code}.json"


def save_raw_records(
    zip_code: str, records: list[dict[str, Any]], output_dir: Path
) -> Path:
    """Écrit les DPE bruts d'un code postal en JSON dans `output_dir`."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = raw_output_path(zip_code, output_dir)
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info(
        "Sauvegardé %d DPE pour le code postal %s dans %s", len(records), zip_code, path
    )
    return path
