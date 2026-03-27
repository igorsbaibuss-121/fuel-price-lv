from html import unescape
from pathlib import Path
import re
from urllib.parse import urljoin

import pandas as pd

from ..net import fetch_url_text
from .common import normalize_price_value, normalize_text_value

CIRCLEK_PRICES_URL = "https://www.circlek.lv/degviela-miles/degvielas-cenas"
CIRCLEK_STATIONS_URL = "https://www.circlek.lv/stations"
CIRCLEK_BASE_URL = "https://www.circlek.lv"


def fetch_circlek_prices_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(CIRCLEK_PRICES_URL, ca_bundle=ca_bundle)
    except ValueError as error:
        raise ValueError(f"Neizdevās nolasīt Circle K cenu lapu: {error}") from error


def extract_station_links(html: str) -> list[dict[str, str]]:
    station_links: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for href, label in re.findall(r'<a[^>]+href="([^"]*/station/[^"]+)"[^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL):
        station_url = urljoin(CIRCLEK_BASE_URL, unescape(href))
        if station_url in seen_urls:
            continue
        station_name = normalize_text_value(strip_tags(label))
        if not station_name:
            continue
        seen_urls.add(station_url)
        station_links.append({"station_name": station_name, "station_url": station_url})
    return station_links


def fetch_circlek_station_page(station_url: str, ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(station_url, ca_bundle=ca_bundle)
    except ValueError as error:
        raise ValueError(f"Neizdevās nolasīt Circle K staciju sarakstu: {error}") from error


def fetch_circlek_station_list_page(ca_bundle: str | None = None) -> str:
    try:
        return fetch_url_text(CIRCLEK_STATIONS_URL, ca_bundle=ca_bundle)
    except ValueError as error:
        raise ValueError(f"Neizdevās nolasīt Circle K staciju sarakstu: {error}") from error


def strip_tags(value: str) -> str:
    return normalize_text_value(unescape(re.sub(r"<[^>]+>", " ", value)))


def normalize_circlek_fuel_type(fuel_label: str) -> str:
    normalized_label = normalize_text_value(fuel_label, lowercase=True)
    fuel_type_mapping = {
        "95miles": "petrol_95",
        "benzīns miles 95": "petrol_95",
        "98miles+": "petrol_98",
        "benzīns miles+ 98": "petrol_98",
        "dmiles": "diesel",
        "dīzeļdegviela miles": "diesel",
        "dmiles+": "diesel_plus",
        "dīzeļdegviela miles+": "diesel_plus",
        "miles+ xtl": "diesel_xtl",
        "dīzeļdegviela miles+ xtl": "diesel_xtl",
        "autogāze": "lpg",
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


def parse_circlek_stations(html: str, ca_bundle: str | None = None) -> list[dict]:
    stations: list[dict] = []
    for station_link in extract_station_links(html):
        if ca_bundle is None:
            station_html = fetch_circlek_station_page(station_link["station_url"])
        else:
            station_html = fetch_circlek_station_page(station_link["station_url"], ca_bundle=ca_bundle)
        station = parse_circlek_station_detail(
            station_html,
            station_name=station_link["station_name"],
            station_url=station_link["station_url"],
        )
        if station is not None:
            stations.append(station)
    return stations


def normalize_address_for_matching(address: str) -> str:
    normalized_address = normalize_text_value(address, lowercase=True)
    return re.sub(r"[^a-z0-9āčēģīķļņšūž]+", "", normalized_address)


def station_matches_address(station: dict, station_address: str) -> bool:
    normalized_station_address = normalize_address_for_matching(station["address"])
    normalized_target_address = normalize_address_for_matching(station_address)
    return (
        normalized_target_address in normalized_station_address
        or normalized_station_address in normalized_target_address
    )


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

    return pd.DataFrame(rows, columns=["station_name", "address", "city", "fuel_type", "price"])


def load_circlek_lv_v1_data(_csv_path: Path | None = None, ca_bundle: str | None = None) -> pd.DataFrame:
    if ca_bundle is None:
        prices_html = fetch_circlek_prices_page()
    else:
        prices_html = fetch_circlek_prices_page(ca_bundle=ca_bundle)
    prices = parse_circlek_prices(prices_html)
    if not prices:
        raise ValueError("Neizdevās atrast Circle K degvielas cenas avotā")

    if ca_bundle is None:
        stations_html = fetch_circlek_station_list_page()
    else:
        stations_html = fetch_circlek_station_list_page(ca_bundle=ca_bundle)
    stations = parse_circlek_stations(stations_html, ca_bundle=ca_bundle)
    if not stations:
        raise ValueError("Neizdevās atrast Circle K stacijas avotā")

    return build_circlek_dataset(prices, stations)
