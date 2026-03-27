from pathlib import Path
import json


def load_source_catalog(path: Path) -> list[dict]:
    if not path.exists():
        raise ValueError(f"Source catalog fails nav atrasts: {path}")

    with path.open(encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    if not isinstance(catalog, list) or not all(isinstance(item, dict) for item in catalog):
        raise ValueError("Source catalog formāts nav derīgs")
    return catalog


def get_source_config(source_id: str, catalog_path: Path) -> dict:
    catalog = load_source_catalog(catalog_path)
    for source_config in catalog:
        if source_config.get("source_id") == source_id:
            return source_config
    raise ValueError(f"Nav atrasts source_id katalogā: {source_id}")


def get_multiple_source_configs(source_ids: list[str], catalog_path: Path) -> list[dict]:
    return [get_source_config(source_id, catalog_path) for source_id in source_ids]
