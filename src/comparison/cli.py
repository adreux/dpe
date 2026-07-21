"""CLI du moteur de comparaison (ticket 3).

Usage:
    python -m src.comparison.cli --address "12 rue Example, 60300 Senlis" \
        --data data/processed/dpe_clean.parquet --output data/processed/
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import click
import pandas as pd

from config.settings import DATA_PROCESSED_DIR
from src.comparison.compare import build_comparison_report, load_hypotheses
from src.comparison.export import save_comparison_report
from src.logger import setup_logging

logger = logging.getLogger(__name__)


def _slugify(address: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", address.lower()).strip("_")


@click.command()
@click.option("--address", required=True, help="Adresse ou zone du prospect")
@click.option(
    "--data",
    "data_path",
    default=str(DATA_PROCESSED_DIR / "dpe_clean.parquet"),
    show_default=True,
    help="Jeu de données DPE nettoyé (ticket 2)",
)
@click.option(
    "--surface",
    "surface_m2",
    type=float,
    default=None,
    help="Surface (m²) du logement, si l'adresse n'a pas de DPE existant",
)
@click.option(
    "--output",
    "output_dir",
    default=str(DATA_PROCESSED_DIR),
    show_default=True,
    help="Dossier de sortie du rapport JSON",
)
def cli(
    address: str, data_path: str, surface_m2: float | None, output_dir: str
) -> None:
    setup_logging()
    data = pd.read_parquet(data_path)
    hypotheses = load_hypotheses()

    report = build_comparison_report(address, data, hypotheses, surface_m2=surface_m2)

    output_path = Path(output_dir) / f"comparison_{_slugify(address)}.json"
    save_comparison_report(report, output_path)

    stats = report["statistiques_groupe"]
    logger.info(
        "%d logement(s) comparable(s) trouvé(s) pour %r (zone %s)",
        stats["nombre_logements"],
        address,
        report["zone"],
    )


if __name__ == "__main__":
    cli()
