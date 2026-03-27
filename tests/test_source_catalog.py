from pathlib import Path

import json
import pytest

from fuel_price_lv.source_catalog import get_source_config, load_source_catalog


def test_get_source_config_returns_matching_source_definition(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            [
                {"source_id": "demo_standard", "input_format": "standard", "csv_path": "data/sample_prices.csv"},
                {"source_id": "demo_raw_v1", "input_format": "raw_v1", "csv_path": "data/sample_raw_prices_v1.csv"},
            ]
        ),
        encoding="utf-8",
    )

    result = get_source_config("demo_raw_v1", catalog_path)

    assert result["input_format"] == "raw_v1"
    assert result["csv_path"] == "data/sample_raw_prices_v1.csv"


def test_get_source_config_raises_for_unknown_source_id(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps([{"source_id": "demo_standard"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="Nav atrasts source_id katalogā: missing_source"):
        get_source_config("missing_source", catalog_path)


def test_load_source_catalog_raises_for_invalid_structure(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({"source_id": "demo_standard"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Source catalog formāts nav derīgs"):
        load_source_catalog(catalog_path)


def test_load_source_catalog_raises_for_missing_catalog_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_catalog.json"

    with pytest.raises(ValueError) as error:
        load_source_catalog(missing_path)

    assert str(error.value) == f"Source catalog fails nav atrasts: {missing_path}"
