from __future__ import annotations

import pytest

from src.cleaning.clean_dpe import (
    build_dataframe,
    clean,
    deduplicate_by_address,
    normalize_address,
    normalize_surface,
    normalize_year,
    normalize_zip,
    surface_bracket,
    tag_zone_and_surface_bracket,
)


def _valid_record(**overrides):
    record = {
        "numero_dpe": "A1",
        "adresse_ban": "12 Rue Example",
        "code_postal_ban": "60300",
        "nom_commune_ban": "Senlis",
        "etiquette_dpe": "D",
        "etiquette_ges": "C",
        "surface_habitable_logement": 80.0,
        "conso_5_usages_par_m2_ep": 250.0,
        "annee_construction": 1998,
        "date_etablissement_dpe": "2025-01-10",
    }
    record.update(overrides)
    return record


def test_deduplicate_keeps_most_recent_dpe_per_address():
    records = [
        _valid_record(numero_dpe="OLD", date_etablissement_dpe="2020-01-01"),
        _valid_record(numero_dpe="NEW", date_etablissement_dpe="2025-06-01"),
    ]

    clean_df, excluded_df = build_dataframe(records)
    deduped = deduplicate_by_address(clean_df)

    assert len(deduped) == 1
    assert deduped.iloc[0]["numero_dpe"] == "NEW"
    assert excluded_df.empty


def test_build_dataframe_excludes_non_positive_surface():
    records = [_valid_record(numero_dpe="BAD", surface_habitable_logement=0)]

    clean_df, excluded_df = build_dataframe(records)

    assert clean_df.empty
    assert len(excluded_df) == 1
    assert "surface" in excluded_df.iloc[0]["exclusion_reason"]


def test_build_dataframe_excludes_negative_consumption():
    records = [_valid_record(numero_dpe="BAD", conso_5_usages_par_m2_ep=-10)]

    clean_df, excluded_df = build_dataframe(records)

    assert clean_df.empty
    assert len(excluded_df) == 1
    assert "consommation" in excluded_df.iloc[0]["exclusion_reason"]


def test_build_dataframe_excludes_missing_required_field():
    record = _valid_record(numero_dpe="BAD")
    del record["code_postal_ban"]

    clean_df, excluded_df = build_dataframe([record])

    assert clean_df.empty
    assert "champ requis manquant" in excluded_df.iloc[0]["exclusion_reason"]


def test_build_dataframe_keeps_valid_rows_and_normalizes_types():
    records = [_valid_record(code_postal_ban=60300)]  # int au lieu de string

    clean_df, excluded_df = build_dataframe(records)

    assert excluded_df.empty
    assert len(clean_df) == 1
    row = clean_df.iloc[0]
    assert row["code_postal"] == "60300"
    assert isinstance(row["surface_m2"], float)
    assert row["annee_construction"] == 1998


def test_surface_bracket_default_tolerance():
    low, high = surface_bracket(100)
    assert low == pytest.approx(85.0)
    assert high == pytest.approx(115.0)


def test_surface_bracket_custom_tolerance():
    low, high = surface_bracket(200, tolerance=0.10)
    assert low == pytest.approx(180.0)
    assert high == pytest.approx(220.0)


def test_tag_zone_and_surface_bracket_adds_expected_columns():
    records = [_valid_record(surface_habitable_logement=100)]
    clean_df, _ = build_dataframe(records)

    tagged = tag_zone_and_surface_bracket(clean_df)

    assert tagged.iloc[0]["zone"] == "60300"
    assert tagged.iloc[0]["surface_bracket_min"] == pytest.approx(85.0)
    assert tagged.iloc[0]["surface_bracket_max"] == pytest.approx(115.0)


def test_clean_end_to_end_produces_expected_schema():
    records = [
        _valid_record(numero_dpe="OLD", date_etablissement_dpe="2020-01-01"),
        _valid_record(numero_dpe="NEW", date_etablissement_dpe="2025-06-01"),
        _valid_record(numero_dpe="BAD", surface_habitable_logement=-1),
    ]

    clean_df, excluded_df = clean(records)

    assert len(clean_df) == 1
    assert len(excluded_df) == 1
    assert set(clean_df.columns) == {
        "numero_dpe",
        "adresse",
        "code_postal",
        "commune",
        "etiquette_dpe",
        "etiquette_ges",
        "surface_m2",
        "conso_kwh_m2_an",
        "annee_construction",
        "date_diagnostic",
        "zone",
        "surface_bracket_min",
        "surface_bracket_max",
    }


def test_normalize_zip_keeps_leading_zeros():
    assert normalize_zip("01000") == "01000"
    assert normalize_zip(1000) == "01000"


def test_normalize_address_trims_and_collapses_whitespace():
    assert normalize_address("  12   Rue Example  ") == "12 Rue Example"


def test_normalize_surface_rejects_non_numeric():
    assert normalize_surface("not a number") is None
    assert normalize_surface(80.5) == 80.5


def test_normalize_year_converts_to_int():
    assert normalize_year(1998.0) == 1998
    assert normalize_year(None) is None
