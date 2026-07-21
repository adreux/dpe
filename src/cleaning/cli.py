"""CLI de nettoyage des DPE bruts (ticket 1) vers un jeu de données propre.

Usage:
    python -m src.cleaning.cli --input data/raw/ --output data/processed/dpe_clean.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path

import click

from config.settings import DATA_PROCESSED_DIR, DATA_RAW_DIR
from src.cleaning.clean_dpe import clean, load_raw_records, save_processed
from src.logger import setup_logging

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--input",
    "input_dir",
    default=str(DATA_RAW_DIR),
    show_default=True,
    help="Dossier contenant les fichiers dpe_raw_*.json du ticket 1",
)
@click.option(
    "--output",
    "output_path",
    default=str(DATA_PROCESSED_DIR / "dpe_clean.parquet"),
    show_default=True,
    help="Fichier de sortie consolidé (.parquet ou .csv)",
)
def cli(input_dir: str, output_path: str) -> None:
    setup_logging()
    raw_paths = sorted(Path(input_dir).glob("dpe_raw_*.json"))
    if not raw_paths:
        logger.error("Aucun fichier dpe_raw_*.json trouvé dans %s", input_dir)
        raise SystemExit(1)

    records = load_raw_records(raw_paths)
    logger.info(
        "%d DPE bruts chargés depuis %d fichier(s)", len(records), len(raw_paths)
    )

    clean_df, excluded_df = clean(records)
    logger.info(
        "%d logements propres, %d lignes exclues", len(clean_df), len(excluded_df)
    )

    output = Path(output_path)
    save_processed(clean_df, output)

    if not excluded_df.empty:
        excluded_path = output.parent / f"{output.stem}_excluded.csv"
        excluded_df.to_csv(excluded_path, index=False)
        logger.info("Lignes exclues loguées dans %s", excluded_path)


if __name__ == "__main__":
    cli()
