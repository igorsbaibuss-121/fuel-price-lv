import os
import socket
import ssl
from urllib.error import HTTPError, URLError

import pytest

from fuel_price_lv.net import fetch_url_text, map_network_error, resolve_ca_bundle


def test_resolve_ca_bundle_prefers_explicit_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", "/env/ssl.pem")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/env/requests.pem")

    result = resolve_ca_bundle("/explicit/custom.pem")

    assert result == "/explicit/custom.pem"


def test_resolve_ca_bundle_uses_env_var_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", "/env/ssl.pem")
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/env/requests.pem")

    result = resolve_ca_bundle()

    assert result == "/env/ssl.pem"


def test_resolve_ca_bundle_falls_back_to_requests_ca_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/env/requests.pem")

    result = resolve_ca_bundle()

    assert result == "/env/requests.pem"


def test_map_network_error_returns_clear_ssl_message() -> None:
    error = ssl.SSLCertVerificationError("certificate verify failed")

    result = map_network_error(error)

    assert "SSL verifikācija neizdevās" in str(result)
    assert "SSL_CERT_FILE" in str(result)


def test_map_network_error_returns_timeout_message() -> None:
    result = map_network_error(socket.timeout("timed out"))

    assert str(result) == "Savienojuma taimauts, mēģini vēlreiz vēlāk."


def test_map_network_error_returns_http_message() -> None:
    error = HTTPError("https://example.com", 503, "Service Unavailable", None, None)

    result = map_network_error(error)

    assert str(result) == "Neizdevās nolasīt attālināto avotu: HTTP 503"


def test_map_network_error_returns_url_message() -> None:
    result = map_network_error(URLError("network down"))

    assert str(result) == "Neizdevās nolasīt attālināto avotu: network down"


def test_fetch_url_text_uses_explicit_ca_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeHeaders:
        @staticmethod
        def get_content_charset() -> str:
            return "utf-8"

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        @staticmethod
        def read() -> bytes:
            return b"ok"

    def fake_create_default_context(*, cafile=None):
        calls["cafile"] = cafile
        return object()

    def fake_urlopen(url, timeout=20, context=None):
        calls["url"] = url
        calls["timeout"] = timeout
        calls["context"] = context
        return FakeResponse()

    monkeypatch.setattr("fuel_price_lv.net.ssl.create_default_context", fake_create_default_context)
    monkeypatch.setattr("fuel_price_lv.net.urlopen", fake_urlopen)

    result = fetch_url_text("https://example.com", ca_bundle="/custom/ca.pem")

    assert result == "ok"
    assert calls["cafile"] == "/custom/ca.pem"
    assert calls["url"].full_url == "https://example.com"


def test_fetch_url_text_raises_clear_ssl_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(url, timeout=20, context=None):
        raise ssl.SSLCertVerificationError("certificate verify failed")

    monkeypatch.setattr("fuel_price_lv.net.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="SSL verifikācija neizdevās"):
        fetch_url_text("https://example.com")
