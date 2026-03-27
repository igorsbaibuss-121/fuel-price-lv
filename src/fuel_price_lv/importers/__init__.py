from pathlib import Path

import pandas as pd

from .excel_v1 import load_excel_v1_data, normalize_excel_v1_prices
from .raw_v1 import load_raw_v1_data, normalize_raw_v1_prices
from .remote_csv_v1 import load_remote_csv_v1_data, normalize_remote_csv_v1_data
from .standard import load_standard_data


def load_input_data(csv_path: Path, input_format: str, source_url: str | None = None) -> pd.DataFrame:
    if input_format == "standard":
        return load_standard_data(csv_path)
    if input_format == "raw_v1":
        return normalize_raw_v1_prices(load_raw_v1_data(csv_path))
    if input_format == "excel_v1":
        return normalize_excel_v1_prices(load_excel_v1_data(csv_path))
    if input_format == "remote_csv_v1":
        return normalize_remote_csv_v1_data(load_remote_csv_v1_data(source_url))
    raise ValueError(f"Neatbalstīts input format: {input_format}")
