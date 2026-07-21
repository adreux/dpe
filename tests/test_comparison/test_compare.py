from __future__ import annotations

import pandas as pd
import pytest

from src.comparison.compare import (
    ComparisonError,
    build_comparison_report,
    compute_group_stats,
    estimate_renovation_gain,
    extract_zip_code,
    find_comparables,
    load_hypotheses,
    resolve_target,
)


def _row(
    numero_dpe,
    adresse,
    zone,
    surface_m2,
    conso_kwh_m2_an,
    etiquette_dpe="D",
    date_diagnostic="2025-01-01",
):
    return {
        "numero_dpe": numero_dpe,
        "adresse": adresse,
        "code_postal": zone,
        "commune": "Senlis",
        "etiquette_dpe": etiquette_dpe,
        "etiquette_ges": "C",
        "surface_m2": surface_m2,
        "conso_kwh_m2_an": conso_kwh_m2_an,
        "annee_construction": 1990,
        "date_diagnostic": pd.Timestamp(date_diagnostic),
        "zone": zone,
    }


@pytest.fixture
def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _row("A1", "1 Rue A", "60300", 100, 250, "D"),
            _row("A2", "2 Rue A", "60300", 105, 300, "E"),
            _row("A3", "3 Rue A", "60300", 90, 200, "C"),
            # hors tranche de surface (100 * 1.15 = 115 max)
            _row("A4", "4 Rue A", "60300", 200, 400, "F"),
            # hors zone
            _row("A5", "5 Rue B", "60100", 100, 260, "D"),
        ]
    )


@pytest.fixture
def hypotheses() -> dict:
    return {
        "renovation": {"reduction_pourcentage_estime": 0.30},
        "energie": {"prix_moyen_kwh_eur": 0.20},
    }


def test_find_comparables_filters_by_zone_and_surface_bracket(sample_data):
    comparables = find_comparables("60300", 100, sample_data)

    assert set(comparables["numero_dpe"]) == {"A1", "A2", "A3"}


def test_find_comparables_excludes_given_address(sample_data):
    comparables = find_comparables("60300", 100, sample_data, exclude_address="1 Rue A")

    assert "A1" not in set(comparables["numero_dpe"])
    assert set(comparables["numero_dpe"]) == {"A2", "A3"}


def test_find_comparables_returns_empty_when_no_match(sample_data):
    comparables = find_comparables("75000", 100, sample_data)
    assert comparables.empty


def test_compute_group_stats_mean_median_and_label_distribution(sample_data):
    comparables = find_comparables("60300", 100, sample_data)

    stats = compute_group_stats(comparables)

    assert stats["nombre_logements"] == 3
    assert stats["conso_moyenne_kwh_m2_an"] == pytest.approx((250 + 300 + 200) / 3)
    assert stats["conso_mediane_kwh_m2_an"] == pytest.approx(250)
    assert stats["distribution_etiquettes"] == {"D": 1, "E": 1, "C": 1}


def test_compute_group_stats_handles_empty_group():
    stats = compute_group_stats(
        pd.DataFrame(columns=["conso_kwh_m2_an", "etiquette_dpe"])
    )
    assert stats["nombre_logements"] == 0
    assert stats["conso_moyenne_kwh_m2_an"] is None


def test_estimate_renovation_gain_exact_calculation(hypotheses):
    gain = estimate_renovation_gain(
        conso_kwh_m2_an=250, surface_m2=100, hypothesis=hypotheses
    )

    assert gain["conso_actuelle_kwh_an"] == pytest.approx(25000)
    assert gain["conso_estimee_kwh_an"] == pytest.approx(17500)
    assert gain["economie_kwh_an"] == pytest.approx(7500)
    assert gain["economie_eur_an"] == pytest.approx(1500)


def test_extract_zip_code_from_full_address():
    assert extract_zip_code("12 rue Example, 60300 Senlis") == "60300"


def test_extract_zip_code_raises_when_absent():
    with pytest.raises(ComparisonError):
        extract_zip_code("adresse sans code postal")


def test_resolve_target_finds_surface_from_existing_address(sample_data):
    target = resolve_target("1 Rue A, 60300 Senlis", sample_data)

    assert target["zone"] == "60300"
    assert target["surface_m2"] == 100
    assert target["matched_address"] == "1 Rue A"


def test_resolve_target_uses_explicit_surface_when_address_unknown(sample_data):
    target = resolve_target(
        "99 Rue Inconnue, 60300 Senlis", sample_data, surface_m2=120
    )

    assert target["zone"] == "60300"
    assert target["surface_m2"] == 120
    assert target["matched_address"] is None


def test_resolve_target_raises_when_address_unknown_and_no_surface(sample_data):
    with pytest.raises(ComparisonError):
        resolve_target("99 Rue Inconnue, 60300 Senlis", sample_data)


@pytest.mark.parametrize(
    "address",
    ["1 Rue A, 60300 Senlis", "2 Rue A, 60300 Senlis", "3 Rue A, 60300 Senlis"],
)
def test_build_comparison_report_on_multiple_addresses(
    sample_data, hypotheses, address
):
    report = build_comparison_report(address, sample_data, hypotheses)

    assert report["zone"] == "60300"
    assert report["estimation_gain_renovation"] is not None
    assert report["statistiques_groupe"]["nombre_logements"] >= 1


def test_load_hypotheses_is_read_from_config_file_not_hardcoded(tmp_path):
    config_a = tmp_path / "hypotheses_a.yaml"
    config_a.write_text(
        "renovation:\n  reduction_pourcentage_estime: 0.10\n"
        "energie:\n  prix_moyen_kwh_eur: 0.15\n"
    )
    config_b = tmp_path / "hypotheses_b.yaml"
    config_b.write_text(
        "renovation:\n  reduction_pourcentage_estime: 0.50\n"
        "energie:\n  prix_moyen_kwh_eur: 0.30\n"
    )

    hyp_a = load_hypotheses(config_a)
    hyp_b = load_hypotheses(config_b)

    gain_a = estimate_renovation_gain(250, 100, hyp_a)
    gain_b = estimate_renovation_gain(250, 100, hyp_b)

    assert hyp_a["renovation"]["reduction_pourcentage_estime"] == 0.10
    assert hyp_b["renovation"]["reduction_pourcentage_estime"] == 0.50
    assert gain_a["economie_eur_an"] != gain_b["economie_eur_an"]
