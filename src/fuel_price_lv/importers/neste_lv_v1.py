from html import unescape
from pathlib import Path
import re

import pandas as pd

from ..net import fetch_url_text
from .common import normalize_price_value, normalize_text_value

NESTE_PRICES_URL = "https://www.neste.lv/lv/content/degvielas-cenas"
NESTE_STATIONS_URL = "https://www.neste.lv/en/node/1192"


def fetch_neste_prices_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(NESTE_PRICES_URL, ca_bundle=ca_bundle)
    except ValueError as error:
        raise ValueError(f"Neizdevās nolasīt Neste cenu lapu: {error}") from error


def fetch_neste_station_list_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(NESTE_STATIONS_URL, ca_bundle=ca_bundle)
    except ValueError as error:
        raise ValueError(f"Neizdevās nolasīt Neste staciju sarakstu: {error}") from error


def strip_tags(value: str) -> str:
    return normalize_text_value(unescape(re.sub(r"<[^>]+>", " ", value)))


def clean_html_text(value: str) -> str:
    text_with_breaks = re.sub(r"(?i)<br\s*/?>", "\n", value)
    text_with_breaks = re.sub(r"(?i)</p>|</div>|</td>|</tr>|</li>", "\n", text_with_breaks)
    text_without_tags = unescape(re.sub(r"<[^>]+>", " ", text_with_breaks))
    normalized_lines = [normalize_text_value(line) for line in text_without_tags.splitlines()]
    return "\n".join(line for line in normalized_lines if line)


def normalize_neste_fuel_type(fuel_label: str) -> str:
    normalized_label = normalize_text_value(fuel_label, lowercase=True)
    fuel_type_mapping = {
        "neste futura 95": "petrol_95",
        "95 benzīns": "petrol_95",
        "neste futura 98": "petrol_98",
        "98 benzīns": "petrol_98",
        "neste futura d": "diesel",
        "futura dīzeļdegviela": "diesel",
        "neste pro diesel": "diesel_plus",
        "prodiesel": "diesel_plus",
    }
    if normalized_label in fuel_type_mapping:
        return fuel_type_mapping[normalized_label]
    return normalized_label.replace(" ", "_")


def parse_neste_prices(html: str) -> list[dict]:
    price_entries: list[dict] = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        cells = [
            strip_tags(cell_html)
            for cell_html in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.IGNORECASE | re.DOTALL)
        ]
        if len(cells) < 3:
            continue
        if not re.search(r"\d+[.,]\d+", cells[1]):
            continue

        fuel_label = cells[0]
        price_match = re.search(r"\d+[.,]\d+", cells[1])
        if price_match is None:
            continue
        scope_text = cells[2].lower()
        is_network_wide = "vienādas" in scope_text or "visās stacijās" in scope_text
        if not is_network_wide:
            continue

        price_entries.append(
            {
                "fuel_type": normalize_neste_fuel_type(fuel_label),
                "price": normalize_price_value(price_match.group(0), "Neste cena"),
                "scope": "network",
                "source_fuel_label": fuel_label,
            }
        )

    return price_entries


def derive_city_from_address(address: str) -> str:
    address_parts = [normalize_text_value(part) for part in address.split(",")]
    if len(address_parts) > 1:
        return address_parts[-1]
    return ""


def extract_station_lines(html: str) -> list[str]:
    cleaned_text = clean_html_text(html)
    return [normalize_text_value(line) for line in cleaned_text.splitlines() if normalize_text_value(line)]


def is_valid_neste_station_record(station_name: str, address: str, city: str) -> bool:
    noise_fragments = [
        "function(",
        "window",
        "document",
        "datalayer",
        "neste dus saraksts",
    ]
    station_name_normalized = normalize_text_value(station_name, lowercase=True)
    address_normalized = normalize_text_value(address, lowercase=True)
    city_normalized = normalize_text_value(city, lowercase=True)

    if "neste" not in station_name_normalized:
        return False
    if not address_normalized or not re.search(r"\d", address):
        return False
    if any(fragment in station_name_normalized for fragment in noise_fragments):
        return False
    if any(fragment in address_normalized for fragment in noise_fragments):
        return False
    if any(fragment in city_normalized for fragment in noise_fragments):
        return False
    return True


def parse_neste_stations(html: str) -> list[dict]:
    station_entries: list[dict] = []
    seen_station_names: set[str] = set()
    current_station_name = ""

    for line in extract_station_lines(html):
        if line.lower().startswith("neste "):
            current_station_name = line
            continue

        if not current_station_name or "," not in line:
            continue

        station = {
            "station_name": current_station_name,
            "address": line,
            "city": derive_city_from_address(line),
        }
        if not is_valid_neste_station_record(
            station["station_name"],
            station["address"],
            station["city"],
        ):
            current_station_name = ""
            continue
        if station["station_name"] in seen_station_names:
            current_station_name = ""
            continue

        seen_station_names.add(station["station_name"])
        station_entries.append(station)
        current_station_name = ""

    return station_entries


def build_neste_dataset(prices: list[dict], stations: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for price_entry in prices:
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

    return pd.DataFrame(rows, columns=["station_name", "address", "city", "fuel_type", "price"])


def load_neste_lv_v1_data(_csv_path: Path | None = None, ca_bundle: str | None = None) -> pd.DataFrame:
    if ca_bundle is None:
        prices_html = fetch_neste_prices_page()
    else:
        prices_html = fetch_neste_prices_page(ca_bundle=ca_bundle)
    prices = parse_neste_prices(prices_html)
    if not prices:
        raise ValueError("Neizdevās atrast Neste degvielas cenas avotā")

    if ca_bundle is None:
        stations_html = fetch_neste_station_list_page()
    else:
        stations_html = fetch_neste_station_list_page(ca_bundle=ca_bundle)
    stations = parse_neste_stations(stations_html)
    if not stations:
        raise ValueError("Neizdevās atrast Neste stacijas avotā")

    return build_neste_dataset(prices, stations)
