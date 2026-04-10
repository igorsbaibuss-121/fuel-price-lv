import os
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen



DEFAULT_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lv,en;q=0.9",
    "Cache-Control": "no-cache",
}


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
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass
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
    request = Request(url, headers=DEFAULT_BROWSER_HEADERS)
    try:
        with urlopen(request, timeout=timeout, context=ssl_context) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except Exception as error:
        raise map_network_error(error) from error
