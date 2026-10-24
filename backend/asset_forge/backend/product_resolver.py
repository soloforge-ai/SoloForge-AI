"""Shopee-first product resolver for commercial content grounding."""

from __future__ import annotations

import ipaddress
import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any


_logger = logging.getLogger(__name__)

PRODUCT_RESOLVER_VERSION = "shopee_product_resolver_v0.1"
_MAX_HTML_BYTES = 2 * 1024 * 1024
_ALLOWED_SHOPEE_HOSTS = (
    "shopee.co.th",
    "s.shopee.co.th",
    "shopee.com",
)


class ProductResolverError(RuntimeError):
    """Raised when a product URL cannot be resolved into safe grounding data."""


class _ShopeeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, diagnostics: dict[str, Any]) -> None:
        super().__init__()
        self.diagnostics = diagnostics

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.diagnostics["stage"] = "redirect_validation"
        self.diagnostics["upstream_http_status"] = code
        self.diagnostics["redirect_count"] += 1
        self.diagnostics["redirect_hosts"].append(_diagnostic_host(newurl))
        _assert_safe_shopee_url(newurl)
        self.diagnostics["stage"] = "http_fetch"
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _ProductMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.json_ld: list[dict[str, Any]] = []
        self.json_ld_parse_failures = 0
        self._json_ld_depth = 0
        self._json_ld_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        if tag.lower() == "meta":
            key = (
                values.get("property")
                or values.get("name")
                or values.get("itemprop")
                or ""
            ).strip().lower()
            content = values.get("content", "").strip()
            if key and content and key not in self.meta:
                self.meta[key] = content
            return

        if tag.lower() == "script":
            script_type = values.get("type", "").strip().lower()
            if script_type == "application/ld+json":
                self._json_ld_depth = 1
                self._json_ld_chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script" or not self._json_ld_depth:
            return
        raw = "".join(self._json_ld_chunks).strip()
        self._json_ld_depth = 0
        self._json_ld_chunks = []
        if not raw:
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.json_ld_parse_failures += 1
            return
        for item in _flatten_json_ld(payload):
            if isinstance(item, dict):
                self.json_ld.append(item)

    def handle_data(self, data: str) -> None:
        if self._json_ld_depth:
            self._json_ld_chunks.append(data)


def resolve_shopee_product(url: str, *, timeout: int = 20) -> dict[str, Any]:
    """Resolve a Shopee URL into the Product Grounding contract shape."""
    diagnostics: dict[str, Any] = {
        "resolver_version": PRODUCT_RESOLVER_VERSION,
        "stage": "input_validation",
        "upstream_http_status": None,
        "content_type": None,
        "response_bytes": None,
        "redirect_count": 0,
        "redirect_hosts": [],
        "final_host": None,
        "metadata_presence": None,
        "json_ld_parse_failures": None,
    }
    try:
        return _resolve_shopee_product(url, timeout=timeout, diagnostics=diagnostics)
    except ProductResolverError:
        # Only fixed keys and sanitized structural values; never log the exception,
        # URL, HTML, headers, cookies, or metadata contents.
        _logger.warning("product_resolver_failure %s", json.dumps(diagnostics))
        raise


def _diagnostic_host(url: str) -> str:
    host = (urllib.parse.urlparse(url).hostname or "").lower().rstrip(".")
    # Do not echo arbitrary (potentially identifying) subdomains into logs.
    if host in {*_ALLOWED_SHOPEE_HOSTS, "www.shopee.co.th", "www.shopee.com"}:
        return host
    return "other_host"


def _diagnostic_content_type(headers: Any) -> str:
    value = str(headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
    if value in {"text/html", "application/xhtml+xml", "application/json", "text/plain"}:
        return value
    return "other" if value else "missing"


def _resolve_shopee_product(
    url: str, *, timeout: int, diagnostics: dict[str, Any]
) -> dict[str, Any]:
    input_url = str(url or "").strip()
    _assert_safe_shopee_url(input_url)

    request = urllib.request.Request(
        input_url,
        headers={
            "User-Agent": "SoloForge-ProductResolver/0.1",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(_ShopeeRedirectHandler(diagnostics))
    diagnostics["stage"] = "http_fetch"

    try:
        with opener.open(request, timeout=timeout) as response:
            diagnostics["upstream_http_status"] = getattr(response, "status", None)
            diagnostics["content_type"] = _diagnostic_content_type(response.headers)
            final_url = str(response.geturl() or input_url)
            diagnostics["final_host"] = _diagnostic_host(final_url)
            diagnostics["stage"] = "final_url_validation"
            _assert_safe_shopee_url(final_url)
            diagnostics["stage"] = "content_type"
            content_type = (
                str(response.headers.get("Content-Type") or "")
                .split(";", 1)[0]
                .strip()
                .lower()
            )
            if content_type and content_type not in {"text/html", "application/xhtml+xml"}:
                raise ProductResolverError("Shopee product URL did not return an HTML page")
            diagnostics["stage"] = "body_read"
            data = response.read(_MAX_HTML_BYTES + 1)
            diagnostics["response_bytes"] = len(data)
    except ProductResolverError:
        raise
    except urllib.error.HTTPError as exc:
        diagnostics["upstream_http_status"] = exc.code
        diagnostics["content_type"] = _diagnostic_content_type(exc.headers or {})
        raise ProductResolverError(
            f"Shopee product page returned HTTP {exc.code}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProductResolverError("Shopee product page could not be reached") from exc

    diagnostics["stage"] = "body_validation"
    if not data:
        raise ProductResolverError("Shopee product page was empty")
    if len(data) > _MAX_HTML_BYTES:
        raise ProductResolverError("Shopee product page was too large")

    html = data.decode("utf-8", errors="replace")
    parser = _ProductMetadataParser()
    diagnostics["stage"] = "metadata_parse"
    parser.feed(html)
    diagnostics["json_ld_parse_failures"] = parser.json_ld_parse_failures
    diagnostics["metadata_presence"] = {
        "og_title": bool(parser.meta.get("og:title")),
        "twitter_title": bool(parser.meta.get("twitter:title")),
        "json_ld_name": bool(_json_ld_value(parser.json_ld, "name")),
        "og_image": bool(parser.meta.get("og:image")),
        "twitter_image": bool(parser.meta.get("twitter:image")),
        "json_ld_image": bool(_json_ld_images(parser.json_ld)),
    }

    title = _first_nonempty(
        parser.meta.get("og:title"),
        parser.meta.get("twitter:title"),
        _json_ld_value(parser.json_ld, "name"),
    )
    title = _clean_title(title)
    image_urls = _unique_nonempty(
        [
            parser.meta.get("og:image"),
            parser.meta.get("twitter:image"),
            *_json_ld_images(parser.json_ld),
        ]
    )
    price = _first_nonempty(
        parser.meta.get("product:price:amount"),
        parser.meta.get("og:price:amount"),
        _json_ld_offer_value(parser.json_ld, "price"),
    )
    shop_name = _first_nonempty(
        _json_ld_offer_seller(parser.json_ld),
        _json_ld_value(parser.json_ld, "brand"),
    )

    diagnostics["stage"] = "title_extraction"
    if not title:
        raise ProductResolverError("Shopee product title could not be resolved")
    diagnostics["stage"] = "image_extraction"
    if not image_urls:
        raise ProductResolverError("Shopee product image could not be resolved")

    affiliate_url = input_url if _is_shopee_short_host(input_url) else ""

    return {
        "resolver_version": PRODUCT_RESOLVER_VERSION,
        "provider": "shopee",
        "input_url": input_url,
        "resolved_url": final_url,
        "grounding": {
            "source": "shopee",
            "canonical_title": title,
            "shop_name": shop_name,
            "price": price or None,
            "product_url": final_url,
            "affiliate_url": affiliate_url,
            "image_urls": image_urls[:12],
        },
    }


def _assert_safe_shopee_url(value: str) -> None:
    parsed = urllib.parse.urlparse(str(value or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ProductResolverError("Product URL must be Shopee HTTPS")
    if parsed.username or parsed.password:
        raise ProductResolverError("Product URL must not contain credentials")

    host = parsed.hostname.strip().lower().rstrip(".")
    if not _is_allowed_shopee_host(host):
        raise ProductResolverError("Product URL must use an allowlisted Shopee host")

    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        _assert_public_ip(literal_ip)
        return

    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ProductResolverError("Shopee product host could not be resolved") from exc
    if not addresses:
        raise ProductResolverError("Shopee product host could not be resolved")
    for address in addresses:
        _assert_public_ip(ipaddress.ip_address(address[4][0]))


def _assert_public_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if not address.is_global:
        raise ProductResolverError("Shopee product URL resolved to a non-public address")


def _is_allowed_shopee_host(host: str) -> bool:
    normalized = host.strip().lower().rstrip(".")
    return any(
        normalized == allowed or normalized.endswith(f".{allowed}")
        for allowed in _ALLOWED_SHOPEE_HOSTS
    )


def _is_shopee_short_host(value: str) -> bool:
    host = (urllib.parse.urlparse(value).hostname or "").strip().lower().rstrip(".")
    return host == "s.shopee.co.th" or host.endswith(".s.shopee.co.th")


def _flatten_json_ld(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        output: list[Any] = []
        for item in payload:
            output.extend(_flatten_json_ld(item))
        return output
    if isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            return [payload, *graph]
        return [payload]
    return []


def _product_json_ld(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    products = []
    for item in items:
        raw_type = item.get("@type")
        types = raw_type if isinstance(raw_type, list) else [raw_type]
        if any(str(value or "").lower() == "product" for value in types):
            products.append(item)
    return products or items


def _json_ld_value(items: list[dict[str, Any]], key: str) -> str:
    for item in _product_json_ld(items):
        value = item.get(key)
        if isinstance(value, dict):
            value = value.get("name")
        if isinstance(value, list):
            value = value[0] if value else ""
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _json_ld_images(items: list[dict[str, Any]]) -> list[str]:
    output: list[str] = []
    for item in _product_json_ld(items):
        value = item.get("image")
        if isinstance(value, str):
            output.append(value)
        elif isinstance(value, list):
            output.extend(str(entry or "").strip() for entry in value)
        elif isinstance(value, dict):
            output.append(str(value.get("url") or "").strip())
    return output


def _json_ld_offer_value(items: list[dict[str, Any]], key: str) -> str:
    for item in _product_json_ld(items):
        offers = item.get("offers")
        candidates = offers if isinstance(offers, list) else [offers]
        for offer in candidates:
            if not isinstance(offer, dict):
                continue
            text = str(offer.get(key) or "").strip()
            if text:
                return text
    return ""


def _json_ld_offer_seller(items: list[dict[str, Any]]) -> str:
    for item in _product_json_ld(items):
        offers = item.get("offers")
        candidates = offers if isinstance(offers, list) else [offers]
        for offer in candidates:
            if not isinstance(offer, dict):
                continue
            seller = offer.get("seller")
            if isinstance(seller, dict):
                value = seller.get("name")
            else:
                value = seller
            text = str(value or "").strip()
            if text:
                return text
    return ""


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _unique_nonempty(values: list[Any]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _clean_title(value: str) -> str:
    title = str(value or "").strip()
    for suffix in (" | Shopee Thailand", " | Shopee ประเทศไทย"):
        if title.endswith(suffix):
            title = title[: -len(suffix)].rstrip()
    return title
