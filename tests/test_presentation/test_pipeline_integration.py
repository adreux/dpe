"""Test d'intégration bout-en-bout (tickets 1 -> 4) sur des données factices.

Aucun appel réseau réel : `fetch_dpe_for_zip_code` est mocké directement.
"""

from __future__ import annotations

from click.testing import CliRunner

import src.presentation.cli as presentation_cli


def _fake_records(zip_code: str) -> list[dict]:
    return [
        {
            "numero_dpe": f"{zip_code}-1",
            "adresse_ban": f"1 Rue Test {zip_code} Ville",
            "code_postal_ban": zip_code,
            "nom_commune_ban": "Ville",
            "etiquette_dpe": "D",
            "etiquette_ges": "C",
            "surface_habitable_logement": 80.0,
            "conso_5_usages_par_m2_ep": 260.0,
            "annee_construction": 1995,
            "date_etablissement_dpe": "2025-01-10",
        },
        {
            "numero_dpe": f"{zip_code}-2",
            "adresse_ban": f"2 Rue Test {zip_code} Ville",
            "code_postal_ban": zip_code,
            "nom_commune_ban": "Ville",
            "etiquette_dpe": "E",
            "etiquette_ges": "D",
            "surface_habitable_logement": 85.0,
            "conso_5_usages_par_m2_ep": 320.0,
            "annee_construction": 1988,
            "date_etablissement_dpe": "2025-02-15",
        },
        {
            "numero_dpe": f"{zip_code}-3",
            "adresse_ban": f"3 Rue Test {zip_code} Ville",
            "code_postal_ban": zip_code,
            "nom_commune_ban": "Ville",
            "etiquette_dpe": "C",
            "etiquette_ges": "B",
            "surface_habitable_logement": 75.0,
            "conso_5_usages_par_m2_ep": 200.0,
            "annee_construction": 2001,
            "date_etablissement_dpe": "2025-03-20",
        },
    ]


def test_full_pipeline_from_address_to_html_report(tmp_path, monkeypatch):
    zip_code = "60300"
    address = f"1 Rue Test, {zip_code} Ville"

    monkeypatch.setattr(
        presentation_cli,
        "fetch_dpe_for_zip_code",
        lambda zc, **kwargs: _fake_records(zc),
    )

    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    output_dir = tmp_path / "output"

    runner = CliRunner()
    result = runner.invoke(
        presentation_cli.cli,
        [
            "--address",
            address,
            "--raw-dir",
            str(raw_dir),
            "--processed-dir",
            str(processed_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output

    raw_file = raw_dir / f"dpe_raw_{zip_code}.json"
    assert raw_file.exists()

    processed_file = processed_dir / "dpe_clean.parquet"
    assert processed_file.exists()

    html_files = list(output_dir.glob("argumentaire_*.html"))
    assert len(html_files) == 1
    content = html_files[0].read_text(encoding="utf-8")
    assert zip_code in content
    assert "hypothèse" in content.lower()


def test_full_pipeline_reuses_existing_raw_data(tmp_path, monkeypatch):
    """Si les données brutes existent déjà, l'extraction n'est pas relancée."""
    zip_code = "60300"
    address = f"1 Rue Test, {zip_code} Ville"

    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    output_dir = tmp_path / "output"
    raw_dir.mkdir(parents=True)

    import json

    (raw_dir / f"dpe_raw_{zip_code}.json").write_text(
        json.dumps(_fake_records(zip_code)), encoding="utf-8"
    )

    calls = []
    monkeypatch.setattr(
        presentation_cli,
        "fetch_dpe_for_zip_code",
        lambda zc, **kwargs: calls.append(zc) or _fake_records(zc),
    )

    runner = CliRunner()
    result = runner.invoke(
        presentation_cli.cli,
        [
            "--address",
            address,
            "--raw-dir",
            str(raw_dir),
            "--processed-dir",
            str(processed_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == []  # l'API n'a pas été appelée
