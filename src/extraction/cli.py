"""CLI d'extraction des DPE bruts depuis l'API ADEME.

Usage:
    python -m src.extraction.cli --zip-codes 60300,60100 --output data/raw/
"""

from __future__ import annotations

import logging
from pathlib import Path

import click

from config.settings import DATA_RAW_DIR
from src.extraction.ademe_client import AdemeApiError, fetch_dpe_for_zip_code
from src.extraction.storage import save_raw_records
from src.logger import setup_logging

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--zip-codes",
    required=True,
    help="Liste de codes postaux séparés par des virgules, ex: 60300,60100",
)
@click.option(
    "--output",
    "output_dir",
    default=str(DATA_RAW_DIR),
    show_default=True,
    help="Dossier de sortie des fichiers JSON bruts",
)
def cli(zip_codes: str, output_dir: str) -> None:
    setup_logging()
    codes = [code.strip() for code in zip_codes.split(",") if code.strip()]
    output_path = Path(output_dir)

    for code in codes:
        try:
            records = fetch_dpe_for_zip_code(code)
        except AdemeApiError:
            logger.exception("Échec de l'extraction pour le code postal %s", code)
            continue
        save_raw_records(code, records, output_path)


if __name__ == "__main__":
    cli()
