from pathlib import Path
import sys

import pytest

from fuel_price_lv.importers import load_input_data
from fuel_price_lv.importers.virsi_lv_v1 import (
    build_virsi_dataset,
    load_virsi_lv_v1_data,
    parse_virsi_prices,
    parse_virsi_stations,
)
from fuel_price_lv.main import main


def test_parse_virsi_prices_extracts_supported_fuels() -> None:
    html = """
    <ul class="prices-grid">
      <div class="price-card" data-type="dd">
        <p class="price"><span>DD</span><span>1.654</span></p>
        <p class="address">Brīvības gatve 297, Rīga, LV-1006</p>
      </div>
      <div class="price-card" data-type="95e">
        <p class="price"><span>95E</span><span>1.594</span></p>
        <p class="address">Brīvības gatve 297, Rīga, LV-1006</p>
      </div>
      <div class="price-card" data-type="98e">
        <p class="price"><span>98E</span><span>1.674</span></p>
        <p class="address">Brīvības gatve 297, Rīga, LV-1006</p>
      </div>
      <div class="price-card" data-type="lpg">
        <p class="price"><span>LPG</span><span>0.799</span></p>
        <p class="address">Visā Viršu tīklā</p>
      </div>
    </ul>
    """

    result = parse_virsi_prices(html)

    assert result == [
        {
            "fuel_type": "diesel",
            "price": 1.654,
            "scope": "station",
            "station_address": "Brīvības gatve 297, Rīga, LV-1006",
            "source_fuel_label": "DD",
        },
        {
            "fuel_type": "petrol_95",
            "price": 1.594,
            "scope": "station",
            "station_address": "Brīvības gatve 297, Rīga, LV-1006",
            "source_fuel_label": "95E",
        },
        {
            "fuel_type": "petrol_98",
            "price": 1.674,
            "scope": "station",
            "station_address": "Brīvības gatve 297, Rīga, LV-1006",
            "source_fuel_label": "98E",
        },
    ]


def test_parse_virsi_prices_marks_network_scope_when_present() -> None:
    html = """
    <div class="price-card" data-type="95e">
      <p class="price"><span>95E</span><span>1.594</span></p>
      <p class="address">Visā Viršu tīklā</p>
    </div>
    """

    result = parse_virsi_prices(html)

    assert result == [
        {
            "fuel_type": "petrol_95",
            "price": 1.594,
            "scope": "network",
            "station_address": None,
            "source_fuel_label": "95E",
        }
    ]


def test_parse_virsi_stations_extracts_station_names_addresses_and_city() -> None:
    payload = """
    {
      "stations": [
        {
          "title": "Virši Teika",
          "address": "Brīvības gatve 297, Rīga, LV-1006"
        },
        {
          "title": "Virši Apvedceļš",
          "address": "\\"Jaungaņģi\\", Ķekava, Ķekavas nov., LV-2123"
        },
        {
          "title": "Partner Station",
          "address": "Example iela 1, Rīga, LV-1001"
        }
      ]
    }
    """

    result = parse_virsi_stations(payload)

    assert result == [
        {
            "station_name": "Virši Teika",
            "address": "Brīvības gatve 297, Rīga, LV-1006",
            "city": "Rīga",
        },
        {
            "station_name": "Virši Apvedceļš",
            "address": "\"Jaungaņģi\", Ķekava, Ķekavas nov., LV-2123",
            "city": "Ķekava",
        },
    ]


def test_build_virsi_dataset_returns_standard_schema_rows() -> None:
    prices = [
        {"fuel_type": "diesel", "price": 1.654, "scope": "station", "station_address": "Brīvības gatve 297, Rīga, LV-1006"},
        {"fuel_type": "petrol_95", "price": 1.594, "scope": "network", "station_address": None},
    ]
    stations = [
        {"station_name": "Virši Teika", "address": "Brīvības gatve 297, Rīga, LV-1006", "city": "Rīga"},
        {"station_name": "Virši Ādaži", "address": "Rīgas gatve 45, Ādaži, LV-2164", "city": "Ādaži"},
    ]

    result = build_virsi_dataset(prices, stations)

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert len(result) == 3
    assert set(result["fuel_type"]) == {"diesel", "petrol_95"}
    diesel_rows = result[result["fuel_type"] == "diesel"]
    assert len(diesel_rows) == 1
    assert diesel_rows.iloc[0]["station_name"] == "Virši Teika"


def test_build_virsi_dataset_falls_back_to_price_page_address_when_match_missing() -> None:
    prices = [
        {"fuel_type": "diesel", "price": 1.654, "scope": "station", "station_address": "Unknown iela 1, Rīga, LV-1001"},
    ]

    result = build_virsi_dataset(prices, [])

    assert result.to_dict(orient="records") == [
        {
            "station_name": "Virši",
            "address": "Unknown iela 1, Rīga, LV-1001",
            "city": "Rīga",
            "fuel_type": "diesel",
            "price": 1.654,
        }
    ]


def test_load_input_data_supports_virsi_lv_v1_with_mocked_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.virsi_lv_v1.fetch_virsi_prices_page",
        lambda: """
        <div class="price-card" data-type="dd">
          <p class="price"><span>DD</span><span>1.654</span></p>
          <p class="address">Brīvības gatve 297, Rīga, LV-1006</p>
        </div>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.virsi_lv_v1.fetch_virsi_station_list_page",
        lambda: """
        {
          "stations": [
            {
              "title": "Virši Teika",
              "address": "Brīvības gatve 297, Rīga, LV-1006"
            }
          ]
        }
        """,
    )

    result = load_input_data(csv_path=tmp_path / "unused.csv", input_format="virsi_lv_v1")

    assert list(result.columns) == ["station_name", "address", "city", "fuel_type", "price"]
    assert result.loc[0, "station_name"] == "Virši Teika"
    assert result.loc[0, "fuel_type"] == "diesel"
    assert result.loc[0, "price"] == 1.654


def test_load_virsi_lv_v1_data_reports_missing_prices(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("fuel_price_lv.importers.virsi_lv_v1.fetch_virsi_prices_page", lambda: "<html></html>")

    with pytest.raises(ValueError, match="Neizdevās atrast Virši degvielas cenas avotā"):
        load_virsi_lv_v1_data(tmp_path / "unused.csv")


def test_load_virsi_lv_v1_data_reports_missing_stations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.virsi_lv_v1.fetch_virsi_prices_page",
        lambda: """
        <div class="price-card" data-type="95e">
          <p class="price"><span>95E</span><span>1.594</span></p>
          <p class="address">Brīvības gatve 297, Rīga, LV-1006</p>
        </div>
        """,
    )
    monkeypatch.setattr("fuel_price_lv.importers.virsi_lv_v1.fetch_virsi_station_list_page", lambda: "{}")

    with pytest.raises(ValueError, match="Neizdevās atrast Virši staciju datus avotā"):
        load_virsi_lv_v1_data(tmp_path / "unused.csv")


def test_main_supports_virsi_lv_v1_input_format(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "fuel_price_lv.importers.virsi_lv_v1.fetch_virsi_prices_page",
        lambda: """
        <div class="price-card" data-type="95e">
          <p class="price"><span>95E</span><span>1.594</span></p>
          <p class="address">Brīvības gatve 297, Rīga, LV-1006</p>
        </div>
        """,
    )
    monkeypatch.setattr(
        "fuel_price_lv.importers.virsi_lv_v1.fetch_virsi_station_list_page",
        lambda: """
        {
          "stations": [
            {
              "title": "Virši Teika",
              "address": "Brīvības gatve 297, Rīga, LV-1006"
            }
          ]
        }
        """,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "--input-format",
            "virsi_lv_v1",
            "--fuel-type",
            "petrol_95",
            "--top-n",
            "1",
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Top 1 petrol_95 cenas" in captured.out
    assert "Virši Teika" in captured.out


def test_virsi_fetch_uses_shared_network_helper_with_ca_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_fetch_url_text(url: str, timeout: int = 20, ca_bundle: str | None = None) -> str:
        calls.append((url, ca_bundle))
        return "<html></html>"

    monkeypatch.setattr("fuel_price_lv.importers.virsi_lv_v1.fetch_url_text", fake_fetch_url_text)

    from fuel_price_lv.importers.virsi_lv_v1 import fetch_virsi_prices_page

    fetch_virsi_prices_page(ca_bundle="/custom/ca.pem")

    assert calls == [("https://www.virsi.lv/lv/privatpersonam/degviela/degvielas-un-elektrouzlades-cenas", "/custom/ca.pem")]
