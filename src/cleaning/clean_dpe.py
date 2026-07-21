"""Nettoyage et structuration des DPE bruts extraits par le ticket 1.

Pipeline : normalisation des types/unités -> exclusion des valeurs aberrantes
(loguées, jamais supprimées silencieusement) -> déduplication (1 DPE le plus
récent par logement/adresse) -> tagging zone + tranche de surface.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import (
    ENERGY_LABEL_ORDER,
    MAX_CONSO_KWH_M2_AN,
    MAX_SURFACE_M2,
    MIN_CONSO_KWH_M2_AN,
    MIN_SURFACE_M2,
    REQUIRED_FIELDS,
    SURFACE_BRACKET_TOLERANCE,
)

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_surface(value: Any) -> float | None:
    try:
        surface = float(value)
    except (TypeError, ValueError):
        return None
    return surface


def normalize_conso(value: Any) -> float | None:
    try:
        conso = float(value)
    except (TypeError, ValueError):
        return None
    return conso


def normalize_year(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_zip(value: Any) -> str | None:
    if value is None:
        return None
    digits = str(value).strip()
    if not digits:
        return None
    return digits.zfill(5)


def normalize_address(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = _WHITESPACE_RE.sub(" ", str(value)).strip()
    return cleaned or None


def normalize_label(value: Any) -> str | None:
    if value is None:
        return None
    label = str(value).strip().upper()
    return label if label in ENERGY_LABEL_ORDER else None


def surface_bracket(
    surface: float, tolerance: float = SURFACE_BRACKET_TOLERANCE
) -> tuple[float, float]:
    """Bornes ± `tolerance` (défaut 15%) autour d'une surface donnée.

    Fonction réutilisée telle quelle par le ticket 3 pour sélectionner les
    logements comparables à une surface cible.
    """
    return (surface * (1 - tolerance), surface * (1 + tolerance))


def load_raw_records(paths: list[Path]) -> list[dict[str, Any]]:
    import json

    records: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as f:
            records.extend(json.load(f))
    return records


def _missing_required_field(record: dict[str, Any]) -> str | None:
    for field in REQUIRED_FIELDS:
        if record.get(field) is None:
            return field
    return None


def build_dataframe(
    records: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalise les enregistrements bruts.

    Retourne `(clean_df, excluded_df)` — `excluded_df` contient les lignes
    exclues avec une colonne `exclusion_reason` expliquant pourquoi.
    """
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for record in records:
        missing = _missing_required_field(record)
        if missing:
            excluded.append(
                {**record, "exclusion_reason": f"champ requis manquant: {missing}"}
            )
            continue

        surface = normalize_surface(record.get("surface_habitable_logement"))
        conso = normalize_conso(record.get("conso_5_usages_par_m2_ep"))
        label = normalize_label(record.get("etiquette_dpe"))
        zip_code = normalize_zip(record.get("code_postal_ban"))
        address = normalize_address(record.get("adresse_ban"))

        if surface is None or not (MIN_SURFACE_M2 < surface <= MAX_SURFACE_M2):
            excluded.append(
                {
                    **record,
                    "exclusion_reason": f"surface invalide ou hors bornes: {surface}",
                }
            )
            continue

        if conso is None or not (MIN_CONSO_KWH_M2_AN < conso <= MAX_CONSO_KWH_M2_AN):
            excluded.append(
                {
                    **record,
                    "exclusion_reason": f"consommation invalide ou hors bornes: {conso}",
                }
            )
            continue

        if label is None:
            excluded.append(
                {
                    **record,
                    "exclusion_reason": f"étiquette DPE invalide: {record.get('etiquette_dpe')!r}",
                }
            )
            continue

        if zip_code is None or address is None:
            excluded.append(
                {**record, "exclusion_reason": "code postal ou adresse invalide"}
            )
            continue

        rows.append(
            {
                "numero_dpe": record["numero_dpe"],
                "adresse": address,
                "code_postal": zip_code,
                "commune": record.get("nom_commune_ban"),
                "etiquette_dpe": label,
                "etiquette_ges": normalize_label(record.get("etiquette_ges")),
                "surface_m2": surface,
                "conso_kwh_m2_an": conso,
                "annee_construction": normalize_year(record.get("annee_construction")),
                "date_diagnostic": record.get("date_etablissement_dpe"),
            }
        )

    clean_df = pd.DataFrame(rows)
    excluded_df = pd.DataFrame(excluded)

    if not clean_df.empty:
        clean_df["etiquette_dpe"] = pd.Categorical(
            clean_df["etiquette_dpe"], categories=ENERGY_LABEL_ORDER, ordered=True
        )
        clean_df["etiquette_ges"] = pd.Categorical(
            clean_df["etiquette_ges"], categories=ENERGY_LABEL_ORDER, ordered=True
        )
        clean_df["date_diagnostic"] = pd.to_datetime(
            clean_df["date_diagnostic"], errors="coerce"
        )

    if not excluded_df.empty:
        logger.warning(
            "%d ligne(s) exclue(s) lors du nettoyage (raisons loguées dans "
            "la colonne exclusion_reason)",
            len(excluded_df),
        )

    return clean_df, excluded_df


def deduplicate_by_address(df: pd.DataFrame) -> pd.DataFrame:
    """Garde uniquement le DPE le plus récent par logement/adresse.

    Limite connue : deux logements distincts d'un même immeuble collectif
    partagent la même adresse postale (pas d'identifiant d'appartement fiable
    dans les champs extraits) — ils sont donc traités comme un seul logement.
    Cf. README.
    """
    if df.empty:
        return df

    before = len(df)
    deduped = (
        df.sort_values("date_diagnostic", ascending=False)
        .drop_duplicates(subset=["adresse"], keep="first")
        .reset_index(drop=True)
    )
    dropped = before - len(deduped)
    if dropped:
        logger.info(
            "%d DPE dupliqué(s) par adresse supprimé(s) (le plus récent conservé)",
            dropped,
        )
    return deduped


def tag_zone_and_surface_bracket(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute `zone` (= code postal) et les bornes ± 15% de la tranche de surface."""
    if df.empty:
        return df

    df = df.copy()
    df["zone"] = df["code_postal"]
    bounds = df["surface_m2"].apply(surface_bracket)
    df["surface_bracket_min"] = bounds.apply(lambda b: b[0])
    df["surface_bracket_max"] = bounds.apply(lambda b: b[1])
    return df


def clean(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pipeline complet : normalisation -> déduplication -> tagging."""
    clean_df, excluded_df = build_dataframe(records)
    clean_df = deduplicate_by_address(clean_df)
    clean_df = tag_zone_and_surface_bracket(clean_df)
    return clean_df, excluded_df


def save_processed(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_parquet(output_path, index=False)
    logger.info("Sauvegardé %d logements nettoyés dans %s", len(df), output_path)
    return output_path
