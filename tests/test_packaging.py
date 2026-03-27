from pathlib import Path
import tomllib

from fuel_price_lv.main import main


def test_pyproject_defines_console_script_entry_point() -> None:
    pyproject_path = Path("pyproject.toml")
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["fuel-price-lv"] == "fuel_price_lv.main:main"


def test_main_is_exposed_as_callable_for_console_script() -> None:
    assert callable(main)
