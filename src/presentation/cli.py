"""CLI unique du pipeline complet (ticket 1 -> 2 -> 3 -> 4), à partir d'une adresse.

Usage:
    python -m src.presentation.cli --address "12 rue Example, 60300 Senlis"
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import click

from config.settings import DATA_PROCESSED_DIR, DATA_RAW_DIR, OUTPUT_DIR
from src.cleaning.clean_dpe import clean, load_raw_records, save_processed
from src.comparison.compare import (
    ComparisonError,
    build_comparison_report,
    extract_zip_code,
    load_hypotheses,
)
from src.extraction.ademe_client import AdemeApiError, fetch_dpe_for_zip_code
from src.extraction.storage import raw_output_path, save_raw_records
from src.logger import setup_logging
from src.presentation.generate_report import generate_html_report

logger = logging.getLogger(__name__)


def _slugify(address: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", address.lower()).strip("_")


def _ensure_raw_data(zip_code: str, raw_dir: Path) -> None:
    if raw_output_path(zip_code, raw_dir).exists():
        logger.info("Données brutes déjà présentes pour le code postal %s", zip_code)
        return

    logger.info("Aucune donnée brute pour %s, extraction depuis l'API ADEME", zip_code)
    try:
        records = fetch_dpe_for_zip_code(zip_code)
    except AdemeApiError as exc:
        raise SystemExit(
            f"Échec de l'extraction ADEME pour le code postal {zip_code} : {exc}"
        ) from exc
    save_raw_records(zip_code, records, raw_dir)


@click.command()
@click.option("--address", required=True, help="Adresse complète du prospect")
@click.option(
    "--surface",
    "surface_m2",
    type=float,
    default=None,
    help="Surface (m²) du logement, si l'adresse n'a pas de DPE existant",
)
@click.option(
    "--raw-dir", default=str(DATA_RAW_DIR), show_default=True, help="Dossier data/raw"
)
@click.option(
    "--processed-dir",
    default=str(DATA_PROCESSED_DIR),
    show_default=True,
    help="Dossier data/processed",
)
@click.option(
    "--output-dir", default=str(OUTPUT_DIR), show_default=True, help="Dossier output"
)
def cli(
    address: str,
    surface_m2: float | None,
    raw_dir: str,
    processed_dir: str,
    output_dir: str,
) -> None:
    setup_logging()
    raw_dir_path = Path(raw_dir)
    processed_dir_path = Path(processed_dir)

    zip_code = extract_zip_code(address)

    # Ticket 1 : extraction (seulement si les données brutes n'existent pas déjà)
    _ensure_raw_data(zip_code, raw_dir_path)

    # Ticket 2 : nettoyage
    raw_paths = sorted(raw_dir_path.glob("dpe_raw_*.json"))
    records = load_raw_records(raw_paths)
    clean_df, excluded_df = clean(records)
    logger.info("%d logements propres après nettoyage", len(clean_df))
    processed_path = save_processed(clean_df, processed_dir_path / "dpe_clean.parquet")
    if not excluded_df.empty:
        excluded_df.to_csv(
            processed_path.parent / "dpe_clean_excluded.csv", index=False
        )

    # Ticket 3 : comparaison
    hypotheses = load_hypotheses()
    try:
        report = build_comparison_report(
            address, clean_df, hypotheses, surface_m2=surface_m2
        )
    except ComparisonError as exc:
        raise SystemExit(
            f"{exc}\nAstuce : relancez avec --surface <m2> pour une adresse "
            "sans DPE existant dans les données."
        ) from exc

    # Ticket 4 : génération du document commercial
    output_path = Path(output_dir) / f"argumentaire_{_slugify(address)}.html"
    generate_html_report(report, output_path)

    logger.info("Pipeline terminé. Document commercial : %s", output_path)


if __name__ == "__main__":
    cli()
