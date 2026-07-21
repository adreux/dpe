from __future__ import annotations

from src.presentation.generate_report import generate_html_report


def _sample_report(with_gain: bool = True) -> dict:
    report = {
        "adresse_recherchee": "8 Rue de Villevert, 60300 Senlis",
        "zone": "60300",
        "surface_m2": 80.0,
        "etiquette_dpe_actuelle": "E",
        "logements_comparables": [
            {
                "adresse": "10 Rue de Villevert 60300 Senlis",
                "surface_m2": 82.0,
                "etiquette_dpe": "E",
                "conso_kwh_m2_an": 310.0,
            },
            {
                "adresse": "12 Rue de Villevert 60300 Senlis",
                "surface_m2": 78.0,
                "etiquette_dpe": "D",
                "conso_kwh_m2_an": 240.0,
            },
        ],
        "statistiques_groupe": {
            "nombre_logements": 2,
            "conso_moyenne_kwh_m2_an": 275.0,
            "conso_mediane_kwh_m2_an": 275.0,
            "distribution_etiquettes": {"D": 1, "E": 1},
            "conso_moyenne_par_etiquette": {"D": 240.0, "E": 310.0},
        },
        "estimation_gain_renovation": (
            {
                "reduction_pourcentage_estime": 0.30,
                "prix_moyen_kwh_eur": 0.2516,
                "conso_actuelle_kwh_m2_an": 275.0,
                "conso_actuelle_kwh_an": 22000.0,
                "conso_estimee_kwh_m2_an": 192.5,
                "conso_estimee_kwh_an": 15400.0,
                "economie_kwh_an": 6600.0,
                "economie_eur_an": 1660.56,
            }
            if with_gain
            else None
        ),
    }
    return report


def test_generate_html_report_creates_file_with_key_figures(tmp_path):
    report = _sample_report()
    output_path = tmp_path / "argumentaire.html"

    result_path = generate_html_report(report, output_path)

    assert result_path == output_path
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "8 Rue de Villevert, 60300 Senlis" in content
    assert "60300" in content
    assert "10 Rue de Villevert 60300 Senlis" in content
    assert "1 661" in content or "1 660" in content  # économie €/an arrondie
    assert "hypothèses" in content.lower() or "hypothèse" in content.lower()
    assert "240 kWh/m²/an" in content  # conso moyenne étiquette D
    assert "310 kWh/m²/an" in content  # conso moyenne étiquette E
    # équivalent €/an pour la surface cible (80 m², 0,2516 €/kWh)
    assert "4 831 €/an" in content  # D : 240 * 80 * 0,2516
    assert "6 240 €/an" in content  # E : 310 * 80 * 0,2516
    # le comparatif par étiquette DPE doit apparaître avant la liste des adresses
    assert content.index("Comparatif par étiquette DPE") < content.index(
        "Logements comparables"
    )
    assert "DPE actuel" in content
    assert "label-e'>E</span>" in content or 'label-e">E</span>' in content


def test_generate_html_report_handles_missing_gain_estimation(tmp_path):
    report = _sample_report(with_gain=False)
    output_path = tmp_path / "argumentaire.html"

    generate_html_report(report, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "Pas assez de logements comparables" in content


def test_generate_html_report_shows_unknown_when_no_current_dpe(tmp_path):
    report = _sample_report()
    report["etiquette_dpe_actuelle"] = None
    output_path = tmp_path / "argumentaire.html"

    generate_html_report(report, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "inconnu" in content.lower()
