from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.sax.saxutils as saxutils

import pandas as pd
import pytest

from fuel_price_lv.importers import load_input_data
from fuel_price_lv.importers.excel_v1 import load_excel_v1_data, normalize_excel_v1_prices
from fuel_price_lv.importers.raw_v1 import load_raw_v1_data, normalize_raw_v1_prices
from fuel_price_lv.importers.remote_csv_v1 import load_remote_csv_v1_data, normalize_remote_csv_v1_data


def write_test_xlsx(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    def column_name(index: int) -> str:
        name = ""
        number = index + 1
        while number > 0:
            number, remainder = divmod(number - 1, 26)
            name = chr(ord("A") + remainder) + name
        return name

    def build_cell(cell_reference: str, value: object) -> str:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{cell_reference}"><v>{value}</v></c>'
        escaped_value = saxutils.escape(str(value))
        return f'<c r="{cell_reference}" t="inlineStr"><is><t>{escaped_value}</t></is></c>'

    all_rows = [headers, *rows]
    row_xml_parts: list[str] = []
    for row_index, row in enumerate(all_rows, start=1):
        cell_xml = "".join(
            build_cell(f"{column_name(column_index)}{row_index}", value)
            for column_index, value in enumerate(row)
        )
        row_xml_parts.append(f'<row r="{row_index}">{cell_xml}</row>')

    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(row_xml_parts)}</sheetData>"
        "</worksheet>"
    )

    with ZipFile(path, "w", ZIP_DEFLATED) as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>',
        )
        workbook.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        workbook.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        workbook.writestr("xl/worksheets/sheet1.xml", worksheet_xml)


def test_load_input_data_returns_standard_schema_for_standard_input(tmp_path: Path) -> None:
    csv_path = tmp_path / "standard.csv"
    pd.DataFrame(
        [
            {
                "station_name": "Circle K",
                "address": "Brivibas iela 100",
                "city": "Riga",
                "fuel_type": "diesel",
                "price": 1.589,
            }
        ]
    ).to_csv(csv_path, index=False)

    result = load_input_data(csv_path=csv_path, input_format="standard")

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]


def test_load_input_data_returns_standard_schema_for_raw_v1_input(tmp_path: Path) -> None:
    csv_path = tmp_path / "raw.csv"
    pd.DataFrame(
        [
            {
                "station": "Circle K",
                "street_address": "Brivibas iela 100",
                "city_name": "Riga",
                "product": "diesel",
                "price_eur": "1,589",
            }
        ]
    ).to_csv(csv_path, index=False)

    result = load_input_data(csv_path=csv_path, input_format="raw_v1")

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert result.loc[0, "fuel_type"] == "diesel"
    assert result.loc[0, "price"] == 1.589


def test_load_input_data_returns_standard_schema_for_excel_v1_input(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "excel.xlsx"
    write_test_xlsx(
        xlsx_path,
        headers=["Station", "Address", "City", "Fuel", "Price"],
        rows=[["Circle K", "Brivibas iela 100", "Riga", "DIESEL", "1,589"]],
    )

    result = load_input_data(csv_path=xlsx_path, input_format="excel_v1")

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert result.loc[0, "fuel_type"] == "diesel"
    assert result.loc[0, "price"] == 1.589


def test_load_input_data_returns_standard_schema_for_remote_csv_v1_input(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_read_csv(source: str) -> pd.DataFrame:
        assert source == "https://example.com/fuel_prices.csv"
        return pd.DataFrame(
            [
                {
                    "station_name": "  Virši ",
                    "address": " Brīvības   iela 100 ",
                    "city": " Rīga ",
                    "fuel_type": " DIESEL ",
                    "price": "1,579",
                }
            ]
        )

    monkeypatch.setattr("fuel_price_lv.importers.remote_csv_v1.pd.read_csv", fake_read_csv)

    result = load_input_data(
        csv_path=tmp_path / "unused.csv",
        input_format="remote_csv_v1",
        source_url="https://example.com/fuel_prices.csv",
    )

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert result.loc[0, "station_name"] == "Virši"
    assert result.loc[0, "address"] == "Brīvības iela 100"
    assert result.loc[0, "city"] == "Rīga"
    assert result.loc[0, "fuel_type"] == "diesel"
    assert result.loc[0, "price"] == 1.579


def test_load_input_data_raises_for_unsupported_input_format(tmp_path: Path) -> None:
    csv_path = tmp_path / "input.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Neatbalstīts input format: legacy"):
        load_input_data(csv_path=csv_path, input_format="legacy")


def test_load_remote_csv_v1_data_rejects_invalid_url_scheme() -> None:
    with pytest.raises(ValueError, match="Atbalstīti tikai http/https source-url"):
        load_remote_csv_v1_data("ftp://example.com/fuel_prices.csv")


def test_load_remote_csv_v1_data_reports_fetch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_csv(source: str) -> pd.DataFrame:
        raise OSError("network down")

    monkeypatch.setattr("fuel_price_lv.importers.remote_csv_v1.pd.read_csv", fake_read_csv)

    with pytest.raises(ValueError, match="Neizdevās nolasīt attālināto CSV avotu: network down"):
        load_remote_csv_v1_data("https://example.com/fuel_prices.csv")


def test_normalize_remote_csv_v1_data_reports_missing_required_columns() -> None:
    df = pd.DataFrame(
        [
            {
                "station_name": "Virši",
                "address": "Brīvības iela 100",
                "city": "Rīga",
                "fuel_type": "diesel",
            }
        ]
    )

    with pytest.raises(ValueError, match="Attālinātajā CSV failā trūkst obligātās kolonnas: price"):
        normalize_remote_csv_v1_data(df)


def test_normalize_raw_v1_prices_strips_text_fields() -> None:
    df = pd.DataFrame(
        [
            {
                "station": "  Neste  ",
                "street_address": "  Rīgas iela 10  ",
                "city_name": "  Rīga  ",
                "product": "  DIESEL  ",
                "price_eur": "1.579",
            }
        ]
    )

    result = normalize_raw_v1_prices(df)

    assert result.loc[0, "station_name"] == "Neste"
    assert result.loc[0, "address"] == "Rīgas iela 10"
    assert result.loc[0, "city"] == "Rīga"
    assert result.loc[0, "fuel_type"] == "diesel"


def test_normalize_raw_v1_prices_collapses_repeated_internal_whitespace() -> None:
    df = pd.DataFrame(
        [
            {
                "station": "Circle   K",
                "street_address": "Rīgas   iela   10",
                "city_name": "Rīga",
                "product": "diesel",
                "price_eur": "1.579",
            }
        ]
    )

    result = normalize_raw_v1_prices(df)

    assert result.loc[0, "station_name"] == "Circle K"
    assert result.loc[0, "address"] == "Rīgas iela 10"


def test_normalize_raw_v1_prices_supports_comma_decimal_separator() -> None:
    df = pd.DataFrame(
        [
            {
                "station": "Neste",
                "street_address": "Rīgas iela 10",
                "city_name": "Rīga",
                "product": "diesel",
                "price_eur": " 1,579 ",
            }
        ]
    )

    result = normalize_raw_v1_prices(df)

    assert result.loc[0, "price"] == 1.579


def test_normalize_raw_v1_prices_returns_numeric_price_column() -> None:
    df = pd.DataFrame(
        [
            {
                "station": "Neste",
                "street_address": "Rīgas iela 10",
                "city_name": "Rīga",
                "product": "diesel",
                "price_eur": "1,579",
            }
        ]
    )

    result = normalize_raw_v1_prices(df)

    assert pd.api.types.is_float_dtype(result["price"])


def test_normalize_raw_v1_prices_raises_for_bad_price_value() -> None:
    df = pd.DataFrame(
        [
            {
                "station": "Circle K",
                "street_address": "Brivibas iela 100",
                "city_name": "Riga",
                "product": "diesel",
                "price_eur": "not_a_price",
            }
        ]
    )

    with pytest.raises(ValueError, match="Nederīga price_eur vērtība ievades failā: not_a_price"):
        normalize_raw_v1_prices(df)


def test_normalize_raw_v1_prices_raises_for_missing_required_columns() -> None:
    df = pd.DataFrame(
        [
            {
                "station": "Circle K",
                "street_address": "Brivibas iela 100",
                "city_name": "Riga",
                "product": "diesel",
            }
        ]
    )

    with pytest.raises(ValueError, match="Raw CSV failā trūkst obligātās kolonnas: price_eur"):
        normalize_raw_v1_prices(df)


def test_load_raw_v1_data_loads_csv_file(tmp_path: Path) -> None:
    csv_path = tmp_path / "raw.csv"
    pd.DataFrame(
        [
            {
                "station": "Circle K",
                "street_address": "Brivibas iela 100",
                "city_name": "Riga",
                "product": "diesel",
                "price_eur": 1.589,
            }
        ]
    ).to_csv(csv_path, index=False)

    result = load_raw_v1_data(csv_path)

    assert not result.empty
    assert list(result.columns) == ["station", "street_address", "city_name", "product", "price_eur"]


def test_excel_v1_adapter_maps_columns_and_returns_standard_order(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "excel.xlsx"
    write_test_xlsx(
        xlsx_path,
        headers=["Station", "Address", "City", "Fuel", "Price"],
        rows=[["Circle K", "Brivibas iela 100", "Riga", "diesel", 1.589]],
    )

    result = normalize_excel_v1_prices(load_excel_v1_data(xlsx_path))

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert result.loc[0, "station_name"] == "Circle K"


def test_excel_v1_adapter_normalizes_text_and_lowercases_fuel_type(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "excel.xlsx"
    write_test_xlsx(
        xlsx_path,
        headers=["Station", "Address", "City", "Fuel", "Price"],
        rows=[["  Circle   K ", " Rīgas   iela 10 ", "  Rīga ", " DIESEL ", "1.579"]],
    )

    result = normalize_excel_v1_prices(load_excel_v1_data(xlsx_path))

    assert result.loc[0, "station_name"] == "Circle K"
    assert result.loc[0, "address"] == "Rīgas iela 10"
    assert result.loc[0, "city"] == "Rīga"
    assert result.loc[0, "fuel_type"] == "diesel"


def test_excel_v1_adapter_parses_comma_decimal_price_as_float(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "excel.xlsx"
    write_test_xlsx(
        xlsx_path,
        headers=["Station", "Address", "City", "Fuel", "Price"],
        rows=[["Neste", "Rīgas iela 10", "Rīga", "diesel", " 1,579 "]],
    )

    result = normalize_excel_v1_prices(load_excel_v1_data(xlsx_path))

    assert result.loc[0, "price"] == 1.579
    assert pd.api.types.is_float_dtype(result["price"])


def test_excel_v1_adapter_raises_for_missing_required_column(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "excel.xlsx"
    write_test_xlsx(
        xlsx_path,
        headers=["Station", "Address", "City", "Fuel"],
        rows=[["Neste", "Rīgas iela 10", "Rīga", "diesel"]],
    )

    with pytest.raises(ValueError, match="Excel failā trūkst obligātās kolonnas: Price"):
        normalize_excel_v1_prices(load_excel_v1_data(xlsx_path))


def test_excel_v1_adapter_raises_for_bad_price(tmp_path: Path) -> None:
    xlsx_path = tmp_path / "excel.xlsx"
    write_test_xlsx(
        xlsx_path,
        headers=["Station", "Address", "City", "Fuel", "Price"],
        rows=[["Neste", "Rīgas iela 10", "Rīga", "diesel", "not_a_price"]],
    )

    with pytest.raises(ValueError, match="Nederīga Price vērtība ievades failā: not_a_price"):
        normalize_excel_v1_prices(load_excel_v1_data(xlsx_path))


def test_excel_v1_sample_preserves_latvian_characters_exactly() -> None:
    sample_path = Path("data/sample_excel_prices_v1.xlsx")

    raw_df = pd.read_excel(sample_path)
    normalized_df = normalize_excel_v1_prices(load_excel_v1_data(sample_path))

    assert raw_df.loc[0, "City"] == "Rīga"
    assert "Brīvības" in raw_df.loc[0, "Address"]
    assert raw_df.loc[2, "Station"] == "Virši"
    assert normalized_df.loc[0, "city"] == "Rīga"
    assert "Brīvības" in normalized_df.loc[0, "address"]
    assert normalized_df.loc[2, "station_name"] == "Virši"
