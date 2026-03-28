from pathlib import Path
import sys

import pytest

from fuel_price_lv.main import main


def test_main_report_creates_expected_files_in_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "3",
            "--report",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Avots:" in captured.out
    assert "Saglabāti faili:" in captured.out
    assert (tmp_path / "output" / "diesel_top3.csv").exists()
    assert (tmp_path / "output" / "diesel_top3.json").exists()
    assert (tmp_path / "output" / "diesel_summary_by_city.csv").exists()


def test_main_save_history_creates_timestamped_snapshot(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()

    class FixedDateTime:
        @classmethod
        def now(cls):
            return __import__("datetime").datetime(2026, 3, 27, 10, 15, 0)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("fuel_price_lv.services.datetime", FixedDateTime)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
            "--save-history",
        ],
    )

    main()

    captured = capsys.readouterr()
    history_path = tmp_path / "output" / "history" / "2026-03-27_101500_standard_diesel.csv"
    assert history_path.exists()
    assert "Top 2 diesel cenas" in captured.out


def test_main_report_with_save_history_prints_history_snapshot_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()

    class FixedDateTime:
        @classmethod
        def now(cls):
            return __import__("datetime").datetime(2026, 3, 27, 10, 15, 0)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("fuel_price_lv.services.datetime", FixedDateTime)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
            "--report",
            "--save-history",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "History snapshot: output/history/2026-03-27_101500_standard_diesel.csv" in captured.out
    assert (tmp_path / "output" / "history" / "2026-03-27_101500_standard_diesel.csv").exists()


def test_main_report_prints_concise_summary_with_source_id(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    source_catalog_path = Path("data/source_catalog.json").resolve()
    csv_path = Path("data/sample_excel_prices_v1.xlsx").resolve()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-id",
            "demo_excel_v1",
            "--source-catalog",
            str(source_catalog_path),
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
            "--report",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Avots: demo_excel_v1" in captured.out
    assert "Fuel type: diesel" in captured.out
    assert "Atrasti ieraksti: 2" in captured.out
    assert "- output/diesel_top2.csv" in captured.out
    assert "- output/diesel_top2.json" in captured.out
    assert "- output/diesel_summary_by_city.csv" in captured.out


def test_main_report_with_filters_and_no_rows_does_not_create_report_files(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--city",
            "Valmiera",
            "--report",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Nav atrasti dati izv" in captured.out
    assert not (tmp_path / "output").exists()


def test_main_save_history_does_not_create_snapshot_for_empty_results(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--city",
            "Valmiera",
            "--save-history",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Nav atrasti dati izv" in captured.out
    assert not (tmp_path / "output" / "history").exists()


def test_main_non_report_behavior_remains_unchanged_when_output_file_is_used(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()
    output_file = tmp_path / "normal.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--output",
            "json",
            "--output-file",
            str(output_file),
        ],
    )

    main()

    captured = capsys.readouterr()
    assert f"Rezult" in captured.out
    assert str(output_file) in captured.out
    assert output_file.exists()
    assert not (tmp_path / "output").exists()


def test_main_report_json_output_includes_google_maps_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--report",
        ],
    )

    main()

    json_output = (tmp_path / "output" / "diesel_top1.json").read_text(encoding="utf-8")
    assert '"google_maps_url"' in json_output
    assert "Top 1 diesel cenas" not in json_output


def test_main_report_csv_outputs_include_google_maps_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--report",
        ],
    )

    main()

    top_n_csv = (tmp_path / "output" / "diesel_top1.csv").read_text(encoding="utf-8")
    summary_csv = (tmp_path / "output" / "diesel_summary_by_city.csv").read_text(encoding="utf-8")
    assert "google_maps_url" in top_n_csv
    assert "google_maps_url" in summary_csv


def test_main_report_ignores_output_and_output_file_for_main_result_printing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()
    custom_output = tmp_path / "custom.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            str(csv_path),
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
            "--output",
            "json",
            "--output-file",
            str(custom_output),
            "--report",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Saglabāti faili:" in captured.out
    assert not custom_output.exists()
    assert (tmp_path / "output" / "diesel_top2.json").exists()


def test_main_report_with_dedup_prints_provenance_stats(
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
            "10",
            "--report",
            "--dedup",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Deduplicēti ieraksti:" in captured.out
    assert "Ar vairākiem avotiem apstiprināti:" in captured.out


def test_main_report_with_detect_price_conflicts_prints_conflict_stats(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "fuel_price_lv.main.load_aggregated_source_data",
        lambda _source_ids, _source_catalog_path: __import__("pandas").DataFrame(
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
            "--report",
            "--detect-price-conflicts",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Cenu konflikti:" in captured.out
    assert "Maksimālā cenu starpība:" in captured.out


def test_main_report_with_live_multi_source_ids_prints_clean_source_label(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "fuel_price_lv.main.load_aggregated_source_data",
        lambda _source_ids, _source_catalog_path: __import__("pandas").DataFrame(
            [
                {
                    "station_name": "Circle K Brīvības",
                    "address": "Brīvības iela 1, Rīga",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.574,
                    "source_id": "circlek_live",
                },
                {
                    "station_name": "Neste Brīvības",
                    "address": "Brīvības iela 1, Rīga",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.579,
                    "source_id": "neste_live",
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
            "circlek_live,neste_live",
            "--fuel-type",
            "diesel",
            "--top-n",
            "10",
            "--report",
            "--dedup",
            "--detect-price-conflicts",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Avots: circlek_live,neste_live" in captured.out
    assert "Deduplicēti ieraksti:" in captured.out
    assert "Ar vairākiem avotiem apstiprināti:" in captured.out
    assert "Cenu konflikti:" in captured.out
    assert "Maksimālā cenu starpība:" in captured.out
