from __future__ import annotations

import json

from src.extraction.storage import raw_output_path, save_raw_records


def test_save_raw_records_writes_expected_filename_and_content(tmp_path):
    records = [{"numero_dpe": "A1", "code_postal_ban": "60300"}]

    path = save_raw_records("60300", records, tmp_path)

    assert path == tmp_path / "dpe_raw_60300.json"
    assert path.exists()
    with path.open(encoding="utf-8") as f:
        content = json.load(f)
    assert content == records


def test_raw_output_path_uses_zip_code_in_filename(tmp_path):
    assert raw_output_path("75001", tmp_path) == tmp_path / "dpe_raw_75001.json"
