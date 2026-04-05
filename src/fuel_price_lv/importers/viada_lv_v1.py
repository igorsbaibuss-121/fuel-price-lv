from html import unescape
from pathlib import Path
import re

import pandas as pd

from ..net import fetch_url_text
from .common import normalize_price_value, normalize_text_value

VIADA_PRICES_URL = "https://www.viada.lv/zemakas-degvielas-cenas/"
STANDARD_COLUMNS = ["station_name", "address", "city", "fuel_type", "price"]

# Fuel type is encoded in the icon image filename, e.g. "petrol_95ecto_new.png"
VIADA_FUEL_TYPE_MAPPING = {
    "petrol_95ecto_new": "petrol_95",
    "petrol_95ectoplus_new": "petrol_95_plus",
    "petrol_98_new": "petrol_98",
    "petrol_d_new": "diesel",
    "petrol_d_ecto_new": "diesel_ecto",
    "gaze": "cng",
    "petrol_e85_new": "e85",
}


def fetch_viada_prices_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(VIADA_PRICES_URL, ca_bundle=ca_bundle)
    except ValueError as error:
        raise ValueError(f"Neizdevās nolasīt VIADA cenu lapu: {error}") from error


def strip_tags(value: str) -> str:
    return normalize_text_value(unescape(re.sub(r"<[^>]+>", " ", value)))


def normalize_viada_fuel_type(img_src: str) -> str | None:
    filename_match = re.search(r"/([^/]+)\.png", img_src, re.IGNORECASE)
    if filename_match is None:
        return None
    filename_stem = filename_match.group(1).lower()
    return VIADA_FUEL_TYPE_MAPPING.get(filename_stem)


def parse_viada_station_entries(stations_text: str) -> list[dict]:
    """Parse 'STATION_NAME : address, city' pairs from stations cell text."""
    entries: list[dict] = []
    # Split on comma followed by a station name prefix (ADUS or DUS)
    parts = re.split(r",\s*(?=(?:ADUS|DUS)\s)", stations_text.rstrip("."))
    for part in parts:
        match = re.match(r"((?:ADUS|DUS)\s+[^:]+?)\s*:\s*(.+)", part.strip())
        if match is None:
            continue
        station_name = normalize_text_value(match.group(1))
        address_with_city = normalize_text_value(match.group(2))
        address_parts = address_with_city.rsplit(",", 1)
        address = normalize_text_value(address_parts[0])
        city = normalize_text_value(address_parts[1]) if len(address_parts) > 1 else ""
        entries.append({"station_name": station_name, "address": address, "city": city})
    return entries


def parse_viada_prices(html: str) -> list[dict]:
    price_entries: list[dict] = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 3:
            continue

        img_match = re.search(r'<img[^>]+src="([^"]+\.png)"', cells[0], re.IGNORECASE)
        if img_match is None:
            continue
        fuel_type = normalize_viada_fuel_type(img_match.group(1))
        if fuel_type is None:
            continue

        price_match = re.search(r"\d+[.,]\d+", strip_tags(cells[1]))
        if price_match is None:
            continue
        price = normalize_price_value(price_match.group(0), "VIADA cena")

        stations_text = strip_tags(cells[2])
        station_entries = parse_viada_station_entries(stations_text)
        if not station_entries:
            continue

        for station in station_entries:
            price_entries.append(
                {
                    "station_name": station["station_name"],
                    "address": station["address"],
                    "city": station["city"],
                    "fuel_type": fuel_type,
                    "price": price,
                }
            )

    return price_entries


def load_viada_lv_v1_data(_csv_path: Path | None = None, ca_bundle: str | None = None) -> pd.DataFrame:
    prices_html = fetch_viada_prices_page(ca_bundle=ca_bundle)
    price_entries = parse_viada_prices(prices_html)
    if not price_entries:
        raise ValueError("Neizdevās atrast VIADA degvielas cenas avotā")
    return pd.DataFrame(price_entries, columns=STANDARD_COLUMNS)
