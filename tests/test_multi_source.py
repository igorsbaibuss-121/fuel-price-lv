from pathlib import Path
import sys

import pandas as pd
import pytest

from fuel_price_lv.main import load_aggregated_source_data, main


def test_main_supports_multiple_sources_via_source_ids_json_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
            "--output",
            "json",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert '"source_id"' in captured.out
    assert '"demo_standard"' in captured.out or '"demo_excel_v1"' in captured.out
    assert '"google_maps_url"' in captured.out


def test_load_aggregated_source_data_supports_live_catalog_source_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_load_single_input_source(
        csv_path: Path,
        input_format: str,
        source_url: str | None = None,
        ca_bundle: str | None = None,
    ) -> pd.DataFrame:
        station_name = "Circle K" if input_format == "circlek_lv_v1" else "Neste"
        return pd.DataFrame(
            [
                {
                    "station_name": station_name,
                    "address": "Brīvības iela 1, Rīga",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.599,
                }
            ]
        )

    monkeypatch.setattr("fuel_price_lv.main.load_single_input_source", fake_load_single_input_source)

    result = load_aggregated_source_data(
        ["circlek_live", "neste_live"],
        Path("data/source_catalog.json"),
    )

    assert list(result["source_id"]) == ["circlek_live", "neste_live"]
    assert list(result["station_name"]) == ["Circle K", "Neste"]


def test_main_supports_multiple_sources_via_source_ids_csv_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
            "--output",
            "csv",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "source_id" in captured.out
    assert "google_maps_url" in captured.out
    assert "demo_standard" in captured.out or "demo_excel_v1" in captured.out


def test_main_without_dedup_keeps_current_multi_source_behavior(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "10",
            "--output",
            "csv",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert captured.out.count("Kārļa Ulmaņa gatve 88") >= 2
    assert "has_price_conflict" not in captured.out


def test_main_source_ids_with_dedup_reduces_duplicate_rows_and_keeps_first_source_id(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "10",
            "--output",
            "json",
            "--dedup",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert '"source_id":"demo_standard"' in captured.out
    assert '"source_id":"demo_excel_v1"' in captured.out
    assert '"source_ids":[' in captured.out
    assert '"demo_standard",' in captured.out
    assert '"demo_excel_v1"' in captured.out
    assert '"source_count":2' in captured.out
    assert captured.out.count("Kārļa Ulmaņa gatve 88") == 1


def test_main_source_ids_with_dedup_csv_output_includes_provenance_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "10",
            "--output",
            "csv",
            "--dedup",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "source_ids" in captured.out
    assert "source_count" in captured.out
    assert "demo_standard|demo_excel_v1" in captured.out


def test_main_source_ids_with_detect_price_conflicts_json_output_includes_conflict_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.main.load_aggregated_source_data",
        lambda _source_ids, _source_catalog_path: pd.DataFrame(
            [
                {
                    "station_name": "Neste",
                    "address": "Kārļa Ulmaņa gatve 88 Rīga",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.574,
                    "source_id": "demo_standard",
                },
                {
                    "station_name": "Neste",
                    "address": "Kārļa Ulmaņa gatve 88",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.579,
                    "source_id": "demo_excel_v1",
                },
            ]
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "10",
            "--output",
            "json",
            "--detect-price-conflicts",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert '"has_price_conflict":true' in captured.out
    assert '"min_price":1.574' in captured.out
    assert '"max_price":1.579' in captured.out
    assert '"price_range":0.005' in captured.out
    assert '"price_values":[' in captured.out


def test_main_source_ids_with_dedup_and_detect_price_conflicts_preserves_provenance_and_conflict_metadata(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.main.load_aggregated_source_data",
        lambda _source_ids, _source_catalog_path: pd.DataFrame(
            [
                {
                    "station_name": "Neste",
                    "address": "Kārļa Ulmaņa gatve 88 Rīga",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.574,
                    "source_id": "demo_standard",
                },
                {
                    "station_name": "Neste",
                    "address": "Kārļa Ulmaņa gatve 88",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.574,
                    "source_id": "demo_excel_v1",
                },
                {
                    "station_name": "Neste",
                    "address": "Kārļa Ulmaņa gatve 88",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.579,
                    "source_id": "demo_circlek",
                },
            ]
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1,demo_circlek",
            "--fuel-type",
            "diesel",
            "--top-n",
            "10",
            "--output",
            "json",
            "--dedup",
            "--detect-price-conflicts",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert '"source_id":"demo_standard"' in captured.out
    assert '"source_ids":[' in captured.out
    assert '"demo_standard",' in captured.out
    assert '"demo_excel_v1",' in captured.out
    assert '"demo_circlek"' in captured.out
    assert '"source_count":3' in captured.out
    assert '"has_price_conflict":true' in captured.out
    assert '"price_range":0.005' in captured.out


def test_main_source_ids_with_detect_price_conflicts_csv_output_includes_conflict_fields(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.main.load_aggregated_source_data",
        lambda _source_ids, _source_catalog_path: pd.DataFrame(
            [
                {
                    "station_name": "Neste",
                    "address": "Kārļa Ulmaņa gatve 88 Rīga",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.574,
                    "source_id": "demo_standard",
                },
                {
                    "station_name": "Neste",
                    "address": "Kārļa Ulmaņa gatve 88",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.579,
                    "source_id": "demo_excel_v1",
                },
            ]
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "10",
            "--output",
            "csv",
            "--detect-price-conflicts",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "has_price_conflict" in captured.out
    assert "price_values" in captured.out
    assert "1.574|1.579" in captured.out


def test_main_table_output_still_works_with_source_ids(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
            "--output",
            "table",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert captured.out.startswith("Top 2 diesel cenas\n\n")
    assert "station_name" in captured.out


def test_main_report_works_with_source_ids(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    source_catalog_path = Path("data/source_catalog.json").resolve()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,demo_excel_v1",
            "--source-catalog",
            str(source_catalog_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
            "--report",
            "--dedup",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Avots: demo_standard,demo_excel_v1" in captured.out
    assert "Saglabāti faili:" in captured.out
    assert (tmp_path / "output" / "diesel_top2.csv").exists()
    assert (tmp_path / "output" / "diesel_top2.json").exists()


def test_main_rejects_source_id_and_source_ids_together(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-id",
            "demo_standard",
            "--source-ids",
            "demo_excel_v1",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Nevar vienlaikus lietot --source-id un --source-ids" in captured.out


def test_main_rejects_empty_source_ids(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            " , ",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "source-ids jānorāda vismaz viens source ID" in captured.out


def test_main_rejects_unknown_source_id_in_source_ids(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-ids",
            "demo_standard,missing_source",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Nav atrasts source_id katalogā: missing_source" in captured.out
