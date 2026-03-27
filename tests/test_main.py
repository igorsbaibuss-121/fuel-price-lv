import argparse
from pathlib import Path
import sys

import pandas as pd
import pytest

from fuel_price_lv.cli import positive_int
from fuel_price_lv.main import main


def test_positive_int_returns_int_for_positive_value() -> None:
    assert positive_int("3") == 3


def test_positive_int_raises_for_zero() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int("0")


def test_positive_int_raises_for_negative_value() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int("-5")


def test_main_prints_message_for_missing_csv_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--csv-path", "missing.csv", "--fuel-type", "diesel"],
    )

    main()

    captured = capsys.readouterr()
    assert "CSV fails nav atrasts" in captured.out


def test_main_prints_message_for_missing_required_csv_columns(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "--csv-path", "data/sample_missing_column.csv", "--fuel-type", "diesel"],
    )

    main()

    captured = capsys.readouterr()
    assert "CSV failā trūkst obligātās kolonnas" in captured.out
    assert "address" in captured.out


def test_main_works_with_source_id_demo_raw_v1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-id",
            "demo_raw_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 2 diesel cenas" in captured.out
    assert "station_name" in captured.out


def test_main_works_with_source_id_demo_excel_v1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-id",
            "demo_excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 2 diesel cenas" in captured.out
    assert "station_name" in captured.out


def test_main_explicit_cli_args_override_source_catalog_values(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--source-id",
            "demo_raw_v1",
            "--input-format",
            "standard",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 1 diesel cenas" in captured.out
    assert "station_name" in captured.out


def test_main_supports_raw_v1_input_format(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_raw_prices_v1.csv",
            "--input-format",
            "raw_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 2 diesel cenas" in captured.out
    assert "station_name" in captured.out
    assert "diesel" in captured.out


def test_main_prints_clear_message_for_invalid_raw_v1_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_raw_missing_column_v1.csv",
            "--input-format",
            "raw_v1",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Raw CSV failā trūkst obligātās kolonnas" in captured.out
    assert "price_eur" in captured.out


def test_main_supports_excel_v1_input_format(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_excel_prices_v1.xlsx",
            "--input-format",
            "excel_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 2 diesel cenas" in captured.out
    assert "station_name" in captured.out
    assert "diesel" in captured.out


def test_main_prints_clear_message_for_excel_v1_missing_column(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_excel_missing_column_v1.xlsx",
            "--input-format",
            "excel_v1",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Excel failā trūkst obligātās kolonnas" in captured.out
    assert "Price" in captured.out


def test_main_prints_clear_message_for_excel_v1_bad_price(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_excel_bad_price_v1.xlsx",
            "--input-format",
            "excel_v1",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Nederīga Price vērtība ievades failā" in captured.out
    assert "not_a_price" in captured.out


def test_main_rejects_remote_csv_v1_without_source_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "remote_csv_v1",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "source-url is required for remote_csv_v1" in captured.out


def test_main_rejects_remote_csv_v1_with_invalid_url_scheme(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "remote_csv_v1",
            "--source-url",
            "ftp://example.com/fuel_prices.csv",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Atbalstīti tikai http/https source-url" in captured.out


def test_main_supports_remote_csv_v1_input_format(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_read_csv(source: str) -> pd.DataFrame:
        assert source == "https://example.com/fuel_prices.csv"
        return pd.DataFrame(
            [
                {
                    "station_name": "Virši",
                    "address": "Brīvības iela 100",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.579,
                },
                {
                    "station_name": "Neste",
                    "address": "Kārļa Ulmaņa gatve 88",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                    "price": 1.574,
                },
                {
                    "station_name": "Circle K",
                    "address": "Jūras iela 21",
                    "city": "Liepāja",
                    "fuel_type": "petrol_95",
                    "price": 1.679,
                },
            ]
        )

    monkeypatch.setattr("fuel_price_lv.importers.remote_csv_v1.pd.read_csv", fake_read_csv)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "remote_csv_v1",
            "--source-url",
            "https://example.com/fuel_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 2 diesel cenas" in captured.out
    assert "station_name" in captured.out
    assert "Virši" in captured.out
    assert "Neste" in captured.out


def test_main_prints_clear_message_for_remote_csv_v1_missing_required_columns(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_read_csv(source: str) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "station_name": "Virši",
                    "address": "Brīvības iela 100",
                    "city": "Rīga",
                    "fuel_type": "diesel",
                }
            ]
        )

    monkeypatch.setattr("fuel_price_lv.importers.remote_csv_v1.pd.read_csv", fake_read_csv)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "remote_csv_v1",
            "--source-url",
            "https://example.com/fuel_prices.csv",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Attālinātajā CSV failā trūkst obligātās kolonnas" in captured.out
    assert "price" in captured.out


def test_main_supports_dirty_raw_v1_input_format(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_raw_dirty_prices_v1.csv",
            "--input-format",
            "raw_v1",
            "--fuel-type",
            "diesel",
            "--top-n",
            "2",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 2 diesel cenas" in captured.out
    assert "Neste" in captured.out
    assert "Rīgas iela 10" in captured.out
    assert "Circle K" not in captured.out


def test_main_prints_clear_message_for_bad_raw_v1_price(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_raw_bad_price_v1.csv",
            "--input-format",
            "raw_v1",
            "--fuel-type",
            "diesel",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Nederīga price_eur vērtība ievades failā" in captured.out
    assert "not_a_price" in captured.out


def test_main_csv_output_includes_google_maps_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--output",
            "csv",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "station_name,address,city,fuel_type,price,google_maps_url" in captured.out
    assert "Top 1 diesel cenas" not in captured.out
    assert "google_maps_url" in captured.out


def test_main_csv_output_written_to_file_includes_google_maps_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    output_file = tmp_path / "result.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--output",
            "csv",
            "--output-file",
            str(output_file),
        ],
    )

    main()

    captured = capsys.readouterr()
    assert f"Rezultāts saglabāts failā: {output_file}" in captured.out
    assert "station_name,address,city,fuel_type,price,google_maps_url" in output_file.read_text(encoding="utf-8")


def test_main_table_console_output_includes_title(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert captured.out.startswith("Top 1 diesel cenas\n\n")
    assert "station_name" in captured.out


def test_main_json_output_includes_google_maps_url_and_does_not_include_title(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--output",
            "json",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert '"station_name"' in captured.out
    assert '"price"' in captured.out
    assert '"google_maps_url"' in captured.out
    assert "Top 1 diesel cenas" not in captured.out


def test_main_table_output_written_to_file_does_not_include_title(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    output_file = tmp_path / "result.txt"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--output-file",
            str(output_file),
        ],
    )

    main()

    captured = capsys.readouterr()
    assert f"Rezultāts saglabāts failā: {output_file}" in captured.out
    file_content = output_file.read_text(encoding="utf-8")
    assert "station_name" in file_content
    assert "Top 1 diesel cenas" not in file_content


def test_main_table_output_does_not_include_google_maps_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--output",
            "table",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "google_maps_url" not in captured.out


def test_main_table_output_keeps_human_readable_columns_without_google_maps_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--output",
            "table",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "google_maps_url" not in captured.out
    assert "station_name" in captured.out
    assert "address" in captured.out
    assert "city" in captured.out
    assert "fuel_type" in captured.out
    assert "price" in captured.out


def test_main_summary_by_city_json_output_includes_google_maps_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--summary-by-city",
            "--output",
            "json",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert '"city"' in captured.out
    assert '"google_maps_url"' in captured.out


def test_main_summary_by_city_csv_output_includes_google_maps_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--summary-by-city",
            "--output",
            "csv",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "city,station_name,address,fuel_type,price,google_maps_url" in captured.out


def test_main_save_with_json_creates_file_in_output_with_generated_filename(
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
            "1",
            "--output",
            "json",
            "--save",
        ],
    )

    main()

    output_file = tmp_path / "output" / "diesel_top1.json"
    captured = capsys.readouterr()
    assert "Rezultāts saglabāts failā: output\\diesel_top1.json" in captured.out
    assert output_file.exists()
    assert '"google_maps_url"' in output_file.read_text(encoding="utf-8")


def test_main_save_with_csv_creates_file_in_output_with_generated_filename(
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
            "1",
            "--output",
            "csv",
            "--save",
        ],
    )

    main()

    output_file = tmp_path / "output" / "diesel_top1.csv"
    captured = capsys.readouterr()
    assert "Rezultāts saglabāts failā: output\\diesel_top1.csv" in captured.out
    assert output_file.exists()
    assert "google_maps_url" in output_file.read_text(encoding="utf-8")


def test_main_summary_by_city_save_uses_summary_filename(
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
            "--summary-by-city",
            "--output",
            "csv",
            "--save",
        ],
    )

    main()

    output_file = tmp_path / "output" / "diesel_summary_by_city.csv"
    captured = capsys.readouterr()
    assert "Rezultāts saglabāts failā: output\\diesel_summary_by_city.csv" in captured.out
    assert output_file.exists()


def test_main_output_file_takes_priority_over_save(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    csv_path = Path("data/sample_prices.csv").resolve()
    output_file = tmp_path / "custom.json"
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
            "--save",
            "--output-file",
            str(output_file),
        ],
    )

    main()

    captured = capsys.readouterr()
    assert f"Rezultāts saglabāts failā: {output_file}" in captured.out
    assert output_file.exists()
    assert not (tmp_path / "output" / "diesel_top1.json").exists()


def test_main_console_behavior_still_works_without_save(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--csv-path",
            "data/sample_prices.csv",
            "--fuel-type",
            "diesel",
            "--top-n",
            "1",
            "--output",
            "table",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert captured.out.startswith("Top 1 diesel cenas\n\n")
    assert "Rezultāts saglabāts failā:" not in captured.out
