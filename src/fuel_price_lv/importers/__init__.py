from pathlib import Path

import pandas as pd

from .circlek_lv_v1 import load_circlek_lv_v1_data
from .excel_v1 import load_excel_v1_data, normalize_excel_v1_prices
from .neste_lv_v1 import load_neste_lv_v1_data
from .raw_v1 import load_raw_v1_data, normalize_raw_v1_prices
from .remote_csv_v1 import load_remote_csv_v1_data, normalize_remote_csv_v1_data
from .standard import load_standard_data
from .virsi_lv_v1 import load_virsi_lv_v1_data


def load_input_data(
    csv_path: Path,
    input_format: str,
    source_url: str | None = None,
    ca_bundle: str | None = None,
) -> pd.DataFrame:
    if input_format == "standard":
        return load_standard_data(csv_path)
    if input_format == "raw_v1":
        return normalize_raw_v1_prices(load_raw_v1_data(csv_path))
    if input_format == "excel_v1":
        return normalize_excel_v1_prices(load_excel_v1_data(csv_path))
    if input_format == "remote_csv_v1":
        return normalize_remote_csv_v1_data(load_remote_csv_v1_data(source_url))
    if input_format == "circlek_lv_v1":
        return load_circlek_lv_v1_data(csv_path, ca_bundle=ca_bundle)
    if input_format == "neste_lv_v1":
        return load_neste_lv_v1_data(csv_path, ca_bundle=ca_bundle)
    if input_format == "virsi_lv_v1":
        return load_virsi_lv_v1_data(csv_path, ca_bundle=ca_bundle)
    raise ValueError(f"Neatbalstīts input format: {input_format}")
