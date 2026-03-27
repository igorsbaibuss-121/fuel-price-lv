import os
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def resolve_ca_bundle(ca_bundle: str | None = None) -> str | None:
    if ca_bundle:
        return ca_bundle
    for env_var_name in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        env_value = os.getenv(env_var_name)
        if env_value:
            return env_value
    return None


def build_ssl_context(ca_bundle: str | None = None) -> ssl.SSLContext:
    resolved_ca_bundle = resolve_ca_bundle(ca_bundle)
    if resolved_ca_bundle:
        return ssl.create_default_context(cafile=resolved_ca_bundle)
    return ssl.create_default_context()


def map_network_error(error: Exception) -> ValueError:
    if isinstance(error, ssl.SSLCertVerificationError):
        return ValueError(
            "SSL verifikācija neizdevās. Iespējams nepieciešams uzņēmuma CA bundle. "
            "Vari iestatīt SSL_CERT_FILE vai REQUESTS_CA_BUNDLE."
        )
    if isinstance(error, ssl.SSLError):
        return ValueError(
            "SSL verifikācija neizdevās. Iespējams nepieciešams uzņēmuma CA bundle. "
            "Vari iestatīt SSL_CERT_FILE vai REQUESTS_CA_BUNDLE."
        )
    if isinstance(error, socket.timeout):
        return ValueError("Savienojuma taimauts, mēģini vēlreiz vēlāk.")
    if isinstance(error, HTTPError):
        return ValueError(f"Neizdevās nolasīt attālināto avotu: HTTP {error.code}")
    if isinstance(error, URLError):
        reason = error.reason
        if isinstance(reason, socket.timeout):
            return ValueError("Savienojuma taimauts, mēģini vēlreiz vēlāk.")
        if isinstance(reason, (ssl.SSLCertVerificationError, ssl.SSLError)):
            return ValueError(
                "SSL verifikācija neizdevās. Iespējams nepieciešams uzņēmuma CA bundle. "
                "Vari iestatīt SSL_CERT_FILE vai REQUESTS_CA_BUNDLE."
            )
        return ValueError(f"Neizdevās nolasīt attālināto avotu: {reason}")
    return ValueError(f"Neizdevās nolasīt attālināto avotu: {error}")


def fetch_url_text(url: str, timeout: int = 20, ca_bundle: str | None = None) -> str:
    ssl_context = build_ssl_context(ca_bundle)
    try:
        with urlopen(url, timeout=timeout, context=ssl_context) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except Exception as error:
        raise map_network_error(error) from error
