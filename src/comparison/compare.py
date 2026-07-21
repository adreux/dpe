"""Moteur de comparaison : sélection de logements comparables et estimation du
gain de rénovation en blocs de chanvre.

Les hypothèses de gain énergétique et le prix du kWh ne sont JAMAIS en dur
dans ce module : elles sont chargées au runtime depuis `config/hypotheses.yaml`
(cf. `load_hypotheses`).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from config.settings import HYPOTHESES_FILE, SURFACE_BRACKET_TOLERANCE
from src.cleaning.clean_dpe import surface_bracket

logger = logging.getLogger(__name__)

_ZIP_CODE_RE = re.compile(r"\b(\d{5})\b")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalize_for_match(value: str) -> str:
    """Normalise une adresse pour comparaison approximative (ponctuation ignorée)."""
    return _NON_ALNUM_RE.sub(" ", value.lower()).strip()


class ComparisonError(Exception):
    """Erreur métier du moteur de comparaison (zone/adresse non résolvable)."""


def load_hypotheses(path: Path = HYPOTHESES_FILE) -> dict[str, Any]:
    """Charge les hypothèses de gain et de prix depuis le fichier YAML.

    Ne jamais hardcoder ces valeurs ailleurs dans le code métier — toujours
    passer par cette fonction pour permettre leur révision sans redéploiement.
    """
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_zip_code(address_or_zone: str) -> str:
    """Extrait un code postal français (5 chiffres) d'une adresse ou zone."""
    match = _ZIP_CODE_RE.search(address_or_zone)
    if not match:
        raise ComparisonError(
            f"Impossible d'extraire un code postal de : {address_or_zone!r}"
        )
    return match.group(1)


def resolve_target(
    address_or_zone: str, data: pd.DataFrame, surface_m2: float | None = None
) -> dict[str, Any]:
    """Résout une adresse/zone en `(zone, surface_m2)` exploitables par `find_comparables`.

    Si `surface_m2` n'est pas fourni, tente de retrouver l'adresse exacte dans
    le jeu de données nettoyé (cas fréquent : le logement a déjà eu un DPE).
    Sinon, lève `ComparisonError` — il faut alors fournir `surface_m2`
    explicitement (cf. option --surface du CLI de présentation, ticket 4).
    """
    zone = extract_zip_code(address_or_zone)

    if surface_m2 is not None:
        return {"zone": zone, "surface_m2": surface_m2, "matched_address": None}

    normalized = _normalize_for_match(address_or_zone)
    # L'adresse recherchée inclut souvent la ville/code postal ("12 Rue X, 60300
    # Senlis") alors que `adresse` en base est juste "12 Rue X" : on matche par
    # inclusion (ponctuation ignorée) plutôt que par égalité stricte.
    matches = data[
        data["adresse"]
        .apply(_normalize_for_match)
        .apply(lambda addr: addr in normalized)
    ]
    if not matches.empty:
        row = matches.iloc[0]
        return {
            "zone": zone,
            "surface_m2": float(row["surface_m2"]),
            "matched_address": row["adresse"],
        }

    raise ComparisonError(
        f"Adresse {address_or_zone!r} introuvable dans les données DPE et "
        "aucune surface fournie explicitement. Fournir `surface_m2`."
    )


def find_comparables(
    zone: str,
    surface_m2: float,
    data: pd.DataFrame,
    tolerance: float = SURFACE_BRACKET_TOLERANCE,
    exclude_address: str | None = None,
) -> pd.DataFrame:
    """Sélectionne les logements de `data` comparables : même zone (code postal)
    et surface dans la tranche ± `tolerance` autour de `surface_m2`.
    """
    low, high = surface_bracket(surface_m2, tolerance=tolerance)
    comparables = data[
        (data["zone"] == zone)
        & (data["surface_m2"] >= low)
        & (data["surface_m2"] <= high)
    ]
    if exclude_address is not None:
        comparables = comparables[
            comparables["adresse"].str.lower() != exclude_address.strip().lower()
        ]
    return comparables.reset_index(drop=True)


def compute_group_stats(comparables: pd.DataFrame) -> dict[str, Any]:
    """Statistiques descriptives sur un groupe de logements comparables."""
    if comparables.empty:
        return {
            "nombre_logements": 0,
            "conso_moyenne_kwh_m2_an": None,
            "conso_mediane_kwh_m2_an": None,
            "distribution_etiquettes": {},
        }

    label_counts = comparables["etiquette_dpe"].value_counts().to_dict()
    return {
        "nombre_logements": len(comparables),
        "conso_moyenne_kwh_m2_an": float(comparables["conso_kwh_m2_an"].mean()),
        "conso_mediane_kwh_m2_an": float(comparables["conso_kwh_m2_an"].median()),
        "distribution_etiquettes": {
            str(label): int(count) for label, count in label_counts.items()
        },
    }


def estimate_renovation_gain(
    conso_kwh_m2_an: float, surface_m2: float, hypothesis: dict[str, Any]
) -> dict[str, Any]:
    """Applique le pourcentage de réduction de consommation post-rénovation.

    `hypothesis` doit être le dict chargé par `load_hypotheses()` (sections
    `renovation.reduction_pourcentage_estime` et `energie.prix_moyen_kwh_eur`).
    """
    reduction_pct = hypothesis["renovation"]["reduction_pourcentage_estime"]
    prix_kwh = hypothesis["energie"]["prix_moyen_kwh_eur"]

    conso_actuelle_kwh_an = conso_kwh_m2_an * surface_m2
    conso_estimee_kwh_m2_an = conso_kwh_m2_an * (1 - reduction_pct)
    conso_estimee_kwh_an = conso_actuelle_kwh_an * (1 - reduction_pct)
    economie_kwh_an = conso_actuelle_kwh_an - conso_estimee_kwh_an
    economie_eur_an = economie_kwh_an * prix_kwh

    return {
        "reduction_pourcentage_estime": reduction_pct,
        "prix_moyen_kwh_eur": prix_kwh,
        "conso_actuelle_kwh_m2_an": conso_kwh_m2_an,
        "conso_actuelle_kwh_an": conso_actuelle_kwh_an,
        "conso_estimee_kwh_m2_an": conso_estimee_kwh_m2_an,
        "conso_estimee_kwh_an": conso_estimee_kwh_an,
        "economie_kwh_an": economie_kwh_an,
        "economie_eur_an": economie_eur_an,
    }


def build_comparison_report(
    address_or_zone: str,
    data: pd.DataFrame,
    hypotheses: dict[str, Any] | None = None,
    surface_m2: float | None = None,
    tolerance: float = SURFACE_BRACKET_TOLERANCE,
) -> dict[str, Any]:
    """Pipeline complet pour une adresse/zone : comparables -> stats -> gain estimé."""
    hypotheses = hypotheses or load_hypotheses()
    target = resolve_target(address_or_zone, data, surface_m2=surface_m2)

    comparables = find_comparables(
        target["zone"],
        target["surface_m2"],
        data,
        tolerance=tolerance,
        exclude_address=target["matched_address"],
    )
    stats = compute_group_stats(comparables)

    gain = None
    if stats["conso_moyenne_kwh_m2_an"] is not None:
        gain = estimate_renovation_gain(
            stats["conso_moyenne_kwh_m2_an"], target["surface_m2"], hypotheses
        )
    else:
        logger.warning(
            "Aucun logement comparable trouvé pour %r (zone=%s, surface=%.1f m²) "
            "— aucune estimation de gain calculée",
            address_or_zone,
            target["zone"],
            target["surface_m2"],
        )

    return {
        "adresse_recherchee": address_or_zone,
        "zone": target["zone"],
        "surface_m2": target["surface_m2"],
        "logements_comparables": comparables.to_dict(orient="records"),
        "statistiques_groupe": stats,
        "estimation_gain_renovation": gain,
    }
