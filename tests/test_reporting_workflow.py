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
