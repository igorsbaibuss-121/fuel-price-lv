from pathlib import Path

import pandas as pd

from ..services import load_data


def load_standard_data(csv_path: Path) -> pd.DataFrame:
    return load_data(csv_path)
