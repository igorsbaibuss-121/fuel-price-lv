from html import unescape
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urljoin

import pandas as pd

from ..net import fetch_url_text
from .common import normalize_price_value, normalize_text_value

CIRCLEK_PRICES_URL = "https://www.circlek.lv/degviela-miles/degvielas-cenas"
CIRCLEK_STATIONS_URL = "https://www.circlek.lv/stations"
CIRCLEK_BASE_URL = "https://www.circlek.lv"
CIRCLEK_FETCH_TIMEOUT_SECONDS = 15
CIRCLEK_DEBUG_HTML_ENV_VAR = "FUEL_PRICE_LV_DEBUG_HTML"
CIRCLEK_DEBUG_STATIONS_HTML_PATH = Path("output") / "_debug_circlek_stations.html"
CIRCLEK_CACHE_PATH = Path("output") / "cache" / "circlek_latest.csv"
CIRCLEK_DATASET_COLUMNS = ["station_name", "address", "city", "fuel_type", "price"]


def log_circlek_timing(stage_name: str, started_at: float) -> None:
    duration_seconds = time.perf_counter() - started_at
    print(f"[CIRCLEK DEBUG] {stage_name}: {duration_seconds:.3f}s", file=sys.stderr)


def maybe_write_circlek_debug_html(stations_html: str) -> None:
    if os.getenv(CIRCLEK_DEBUG_HTML_ENV_VAR) != "1":
        return
    CIRCLEK_DEBUG_STATIONS_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    CIRCLEK_DEBUG_STATIONS_HTML_PATH.write_text(stations_html, encoding="utf-8")
    print(f"[CIRCLEK DEBUG] stations html saved: {CIRCLEK_DEBUG_STATIONS_HTML_PATH}", file=sys.stderr)


def format_circlek_fetch_error(resource_name: str, error: ValueError) -> ValueError:
    if "taimauts" in str(error).lower():
        return ValueError(f"NeizdevÄs nolasÄ«t Circle K {resource_name}: taimauts")
    return ValueError(f"NeizdevÄs nolasÄ«t Circle K {resource_name}: {error}")


def fetch_circlek_prices_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(CIRCLEK_PRICES_URL, timeout=CIRCLEK_FETCH_TIMEOUT_SECONDS, ca_bundle=ca_bundle)
    except ValueError as error:
        raise format_circlek_fetch_error("cenu lapu", error) from error


def fetch_circlek_station_page(station_url: str, ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(station_url, timeout=CIRCLEK_FETCH_TIMEOUT_SECONDS, ca_bundle=ca_bundle)
    except ValueError as error:
        raise format_circlek_fetch_error("stacijas lapu", error) from error


def fetch_circlek_station_list_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(CIRCLEK_STATIONS_URL, timeout=CIRCLEK_FETCH_TIMEOUT_SECONDS, ca_bundle=ca_bundle)
    except ValueError as error:
        raise format_circlek_fetch_error("staciju sarakstu", error) from error


def strip_tags(value: str) -> str:
    return normalize_text_value(unescape(re.sub(r"<[^>]+>", " ", value)))


def normalize_circlek_fuel_type(fuel_label: str) -> str:
    normalized_label = normalize_text_value(fuel_label, lowercase=True)
    fuel_type_mapping = {
        "95miles": "petrol_95",
        "benzÄ«ns miles 95": "petrol_95",
        "benzÃ¤Â«ns miles 95": "petrol_95",
        "98miles+": "petrol_98",
        "benzÄ«ns miles+ 98": "petrol_98",
        "benzÃ¤Â«ns miles+ 98": "petrol_98",
        "dmiles": "diesel",
        "dÄ«zeÄ¼degviela miles": "diesel",
        "dÃ¤Â«zeÃ¤Â¼degviela miles": "diesel",
        "dmiles+": "diesel_plus",
        "dÄ«zeÄ¼degviela miles+": "diesel_plus",
        "dÃ¤Â«zeÃ¤Â¼degviela miles+": "diesel_plus",
        "miles+ xtl": "diesel_xtl",
        "dÄ«zeÄ¼degviela miles+ xtl": "diesel_xtl",
        "dÃ¤Â«zeÃ¤Â¼degviela miles+ xtl": "diesel_xtl",
        "autogÄze": "lpg",
        "autogÃ¤Âze": "lpg",
    }
    if normalized_label in fuel_type_mapping:
        return fuel_type_mapping[normalized_label]
    return normalized_label.replace(" ", "_").replace("+", "_plus")


def parse_circlek_prices(html: str) -> list[dict]:
    price_entries: list[dict] = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        cells = [strip_tags(cell_html) for cell_html in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.IGNORECASE | re.DOTALL)]
        if len(cells) < 3:
            continue
        if not re.search(r"\d+[.,]\d+", cells[1]):
            continue

        fuel_label = cells[0]
        price_text = re.search(r"\d+[.,]\d+", cells[1])
        if price_text is None:
            continue
        scope_text = cells[2]
        is_network_wide = "visos dus" in scope_text.lower()

        price_entries.append(
            {
                "fuel_type": normalize_circlek_fuel_type(fuel_label),
                "price": normalize_price_value(price_text.group(0), "Circle K cena"),
                "scope": "network" if is_network_wide else "station",
                "station_address": None if is_network_wide else normalize_text_value(scope_text),
                "source_fuel_label": fuel_label,
            }
        )

    return price_entries


def derive_city_from_address(address: str) -> str:
    address_parts = [normalize_text_value(part) for part in address.split(",")]
    for part in address_parts[1:]:
        lowered_part = part.lower()
        if lowered_part in {"lv", "latvija"} or lowered_part.startswith("lv-"):
            continue
        if lowered_part.endswith(" nov.") or lowered_part.endswith(" novads"):
            return normalize_text_value(part.rsplit(" ", 1)[0])
        return part
    return ""


def parse_circlek_station_detail(html: str, station_name: str, station_url: str) -> dict | None:
    address_match = re.search(r"<h2[^>]*>\s*(.*?)\s*</h2>", html, flags=re.IGNORECASE | re.DOTALL)
    if address_match is None:
        return None

    address = strip_tags(address_match.group(1))
    if not address:
        return None

    return {
        "station_name": station_name,
        "address": address,
        "city": derive_city_from_address(address),
        "station_url": station_url,
    }


def extract_station_list_items(html: str) -> list[str]:
    list_items = re.findall(r"<li[^>]*>(.*?)</li>", html, flags=re.IGNORECASE | re.DOTALL)
    if list_items:
        return list_items
    return re.findall(r'<div[^>]+class="[^"]*station[^"]*"[^>]*>(.*?)</div>', html, flags=re.IGNORECASE | re.DOTALL)


def parse_circlek_station_list_item(item_html: str) -> dict | None:
    link_match = re.search(r'<a[^>]+href="([^"]*/station/[^"]+)"[^>]*>(.*?)</a>', item_html, flags=re.IGNORECASE | re.DOTALL)
    if link_match is None:
        return None

    station_url = urljoin(CIRCLEK_BASE_URL, unescape(link_match.group(1)))
    station_name = strip_tags(link_match.group(2))
    if not station_name:
        return None

    item_text = strip_tags(item_html)
    remaining_text = normalize_text_value(item_text.replace(station_name, "", 1))
    address = remaining_text if "," in remaining_text else ""

    return {
        "station_name": station_name,
        "address": address,
        "city": derive_city_from_address(address) if address else "",
        "station_url": station_url,
    }


def parse_circlek_stations(html: str) -> list[dict]:
    stations: list[dict] = []
    seen_station_urls: set[str] = set()
    for item_html in extract_station_list_items(html):
        station = parse_circlek_station_list_item(item_html)
        if station is None:
            continue
        if station["station_url"] in seen_station_urls:
            continue
        seen_station_urls.add(station["station_url"])
        stations.append(station)
    return stations


def normalize_address_for_matching(address: str) -> str:
    normalized_address = normalize_text_value(address, lowercase=True)
    return re.sub(r"[^a-z0-9Ã„ÂÃ„ÂÃ„â€œÃ„Â£Ã„Â«Ã„Â·Ã„Â¼Ã…â€ Ã…Â¡Ã…Â«Ã…Â¾]+", "", normalized_address)


def station_matches_address(station: dict, station_address: str) -> bool:
    normalized_station_address = normalize_address_for_matching(station["address"])
    normalized_target_address = normalize_address_for_matching(station_address)
    return normalized_target_address in normalized_station_address or normalized_station_address in normalized_target_address


def build_circlek_dataset(prices: list[dict], stations: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for price_entry in prices:
        if price_entry["scope"] == "network":
            for station in stations:
                rows.append(
                    {
                        "station_name": station["station_name"],
                        "address": station["address"],
                        "city": station["city"],
                        "fuel_type": price_entry["fuel_type"],
                        "price": price_entry["price"],
                    }
                )
            continue

        station_address = price_entry.get("station_address")
        if station_address is None:
            continue
        for station in stations:
            if station_matches_address(station, station_address):
                rows.append(
                    {
                        "station_name": station["station_name"],
                        "address": station["address"],
                        "city": station["city"],
                        "fuel_type": price_entry["fuel_type"],
                        "price": price_entry["price"],
                    }
                )

    return pd.DataFrame(rows, columns=CIRCLEK_DATASET_COLUMNS)


def save_circlek_cache_csv(
    dataset: pd.DataFrame,
    cache_path: Path = CIRCLEK_CACHE_PATH,
) -> Path:
    normalized_dataset = dataset.loc[:, CIRCLEK_DATASET_COLUMNS].copy()
    for column in ("address", "city"):
        normalized_dataset[column] = normalized_dataset[column].map(
            lambda value: "" if value is None or pd.isna(value) else str(value)
        )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_dataset.to_csv(cache_path, index=False, encoding="utf-8")
    return cache_path


def load_circlek_lv_v1_data(_csv_path: Path | None = None, ca_bundle: str | None = None) -> pd.DataFrame:
    stage_started_at = time.perf_counter()
    if ca_bundle is None:
        prices_html = fetch_circlek_prices_page()
    else:
        prices_html = fetch_circlek_prices_page(ca_bundle=ca_bundle)
    log_circlek_timing("fetch prices", stage_started_at)

    stage_started_at = time.perf_counter()
    prices = parse_circlek_prices(prices_html)
    log_circlek_timing("parse prices", stage_started_at)
    if not prices:
        raise ValueError("NeizdevÃ„Âs atrast Circle K degvielas cenas avotÃ„Â")

    stage_started_at = time.perf_counter()
    if ca_bundle is None:
        stations_html = fetch_circlek_station_list_page()
    else:
        stations_html = fetch_circlek_station_list_page(ca_bundle=ca_bundle)
    log_circlek_timing("fetch station list", stage_started_at)
    maybe_write_circlek_debug_html(stations_html)

    stage_started_at = time.perf_counter()
    stations = parse_circlek_stations(stations_html)
    log_circlek_timing("parse stations", stage_started_at)
    if not stations:
        raise ValueError("NeizdevÃ„Âs atrast Circle K stacijas avotÃ„Â")

    stage_started_at = time.perf_counter()
    dataset = build_circlek_dataset(prices, stations)
    log_circlek_timing("build dataset", stage_started_at)
    return dataset
