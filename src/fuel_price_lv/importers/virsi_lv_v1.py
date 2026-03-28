from html import unescape
from pathlib import Path
import json
import re

import pandas as pd

from ..net import fetch_url_text
from .common import normalize_price_value, normalize_text_value

VIRSI_PRICES_URL = "https://www.virsi.lv/lv/privatpersonam/degviela/degvielas-un-elektrouzlades-cenas"
VIRSI_STATIONS_URL = "https://www.virsi.lv/lv/privatpersonam/uzpildes-stacijas/data"
STANDARD_COLUMNS = ["station_name", "address", "city", "fuel_type", "price"]


def fetch_virsi_prices_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(VIRSI_PRICES_URL, ca_bundle=ca_bundle)
    except ValueError as error:
        raise ValueError(f"Neizdevās nolasīt Virši cenu lapu: {error}") from error


def fetch_virsi_station_list_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(VIRSI_STATIONS_URL, ca_bundle=ca_bundle)
    except ValueError as error:
        raise ValueError(f"Neizdevās nolasīt Virši staciju lapu: {error}") from error


def strip_tags(value: str) -> str:
    return normalize_text_value(unescape(re.sub(r"<[^>]+>", " ", value)))


def normalize_virsi_fuel_type(fuel_label: str) -> str | None:
    normalized_label = normalize_text_value(fuel_label, lowercase=True)
    fuel_type_mapping = {
        "dd": "diesel",
        "95e": "petrol_95",
        "98e": "petrol_98",
    }
    return fuel_type_mapping.get(normalized_label)


def parse_virsi_prices(html: str) -> list[dict]:
    price_entries: list[dict] = []
    price_card_pattern = re.compile(
        r'<div class="price-card[^"]*"[^>]*>.*?<p class="price">\s*<span>(.*?)</span>\s*<span>(.*?)</span>\s*</p>.*?<p class="address">(.*?)</p>',
        flags=re.IGNORECASE | re.DOTALL,
    )

    for fuel_label, price_text, address_text in price_card_pattern.findall(html):
        normalized_fuel_label = strip_tags(fuel_label)
        fuel_type = normalize_virsi_fuel_type(normalized_fuel_label)
        if fuel_type is None:
            continue

        normalized_address = strip_tags(address_text)
        is_network_wide = "visā viršu tīklā" in normalized_address.lower()
        price_entries.append(
            {
                "fuel_type": fuel_type,
                "price": normalize_price_value(strip_tags(price_text), "Virši cena"),
                "scope": "network" if is_network_wide else "station",
                "station_address": None if is_network_wide else normalized_address,
                "source_fuel_label": normalized_fuel_label,
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


def is_virsi_station(station: dict) -> bool:
    station_title = normalize_text_value(station.get("title", ""), lowercase=True)
    return station_title.startswith("virši") or station_title.startswith("virsi")


def parse_virsi_stations(html: str) -> list[dict]:
    try:
        payload = json.loads(html)
    except json.JSONDecodeError as error:
        raise ValueError("Neizdevās atrast Virši staciju datus avotā") from error

    raw_stations = payload.get("stations")
    if not isinstance(raw_stations, list):
        raise ValueError("Neizdevās atrast Virši staciju datus avotā")

    stations: list[dict] = []
    for station in raw_stations:
        if not isinstance(station, dict) or not is_virsi_station(station):
            continue

        station_name = normalize_text_value(station.get("title", ""))
        address = normalize_text_value(station.get("address", ""))
        if not station_name or not address:
            continue

        stations.append(
            {
                "station_name": station_name,
                "address": address,
                "city": derive_city_from_address(address),
            }
        )

    return stations


def normalize_address_for_matching(address: str) -> str:
    normalized_address = normalize_text_value(address, lowercase=True)
    return re.sub(r"[\W_]+", "", normalized_address, flags=re.UNICODE)


def station_matches_address(station: dict, station_address: str) -> bool:
    normalized_station_address = normalize_address_for_matching(station["address"])
    normalized_target_address = normalize_address_for_matching(station_address)
    return (
        normalized_target_address in normalized_station_address
        or normalized_station_address in normalized_target_address
    )


def build_virsi_dataset(prices: list[dict], stations: list[dict]) -> pd.DataFrame:
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
        if not station_address:
            continue

        matching_stations = [station for station in stations if station_matches_address(station, station_address)]
        if matching_stations:
            for station in matching_stations:
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

        rows.append(
            {
                "station_name": "Virši",
                "address": station_address,
                "city": derive_city_from_address(station_address),
                "fuel_type": price_entry["fuel_type"],
                "price": price_entry["price"],
            }
        )

    return pd.DataFrame(rows, columns=STANDARD_COLUMNS)


def load_virsi_lv_v1_data(_csv_path: Path | None = None, ca_bundle: str | None = None) -> pd.DataFrame:
    if ca_bundle is None:
        prices_html = fetch_virsi_prices_page()
    else:
        prices_html = fetch_virsi_prices_page(ca_bundle=ca_bundle)
    prices = parse_virsi_prices(prices_html)
    if not prices:
        raise ValueError("Neizdevās atrast Virši degvielas cenas avotā")

    if ca_bundle is None:
        stations_html = fetch_virsi_station_list_page()
    else:
        stations_html = fetch_virsi_station_list_page(ca_bundle=ca_bundle)
    stations = parse_virsi_stations(stations_html)
    if not stations:
        raise ValueError("Neizdevās atrast Virši staciju datus avotā")

    return build_virsi_dataset(prices, stations)
