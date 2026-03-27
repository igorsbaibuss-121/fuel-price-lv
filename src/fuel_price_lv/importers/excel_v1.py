from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import pandas as pd

from .common import normalize_price_value, normalize_text_value

EXCEL_V1_REQUIRED_COLUMNS = {
    "Station",
    "Address",
    "City",
    "Fuel",
    "Price",
}

SPREADSHEET_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def column_reference_to_index(cell_reference: str) -> int:
    column_letters = "".join(character for character in cell_reference if character.isalpha())
    column_index = 0
    for character in column_letters:
        column_index = (column_index * 26) + (ord(character.upper()) - ord("A") + 1)
    return column_index - 1


def read_excel_rows(xlsx_path: Path) -> list[dict[str, object]]:
    with ZipFile(xlsx_path) as workbook:
        sheet_root = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        shared_strings = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            shared_strings_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(text_node.text or "" for text_node in string_node.findall(".//main:t", SPREADSHEET_NS))
                for string_node in shared_strings_root.findall("main:si", SPREADSHEET_NS)
            ]

    rows: list[list[object]] = []
    for row_node in sheet_root.findall(".//main:sheetData/main:row", SPREADSHEET_NS):
        row_values: dict[int, object] = {}
        for cell_node in row_node.findall("main:c", SPREADSHEET_NS):
            column_index = column_reference_to_index(cell_node.attrib.get("r", ""))
            cell_type = cell_node.attrib.get("t")
            if cell_type == "inlineStr":
                value = "".join(text_node.text or "" for text_node in cell_node.findall(".//main:t", SPREADSHEET_NS))
            else:
                value_node = cell_node.find("main:v", SPREADSHEET_NS)
                if value_node is None:
                    value = ""
                elif cell_type == "s":
                    value = shared_strings[int(value_node.text or "0")]
                else:
                    value = value_node.text or ""
            row_values[column_index] = value

        if row_values:
            row = [""] * (max(row_values) + 1)
            for index, value in row_values.items():
                row[index] = value
            rows.append(row)

    if not rows:
        return []

    headers = [str(value) for value in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:]]


def load_excel_v1_data(xlsx_path: Path) -> pd.DataFrame:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"CSV fails nav atrasts: {xlsx_path}")
    return pd.DataFrame(read_excel_rows(xlsx_path))


def normalize_excel_v1_prices(df: pd.DataFrame) -> pd.DataFrame:
    missing_columns = [column for column in EXCEL_V1_REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        missing_columns_str = ", ".join(sorted(missing_columns))
        raise ValueError(f"Excel failā trūkst obligātās kolonnas: {missing_columns_str}")

    normalized_df = pd.DataFrame(
        {
            "station_name": df["Station"].map(normalize_text_value),
            "address": df["Address"].map(normalize_text_value),
            "city": df["City"].map(normalize_text_value),
            "fuel_type": df["Fuel"].map(lambda value: normalize_text_value(value, lowercase=True)),
            "price": df["Price"].map(lambda value: normalize_price_value(value, "Price")),
        }
    )
    return normalized_df[["station_name", "address", "city", "fuel_type", "price"]]
