"""Deterministic product-image grounding for commercial content jobs."""

from __future__ import annotations

import hashlib
import ipaddress
import os
import socket
import urllib.parse
import urllib.request
from typing import Any


PRODUCT_GROUNDING_VERSION = "product_grounding_v0.1"
_MAX_IMAGE_BYTES = 12 * 1024 * 1024
_DEFAULT_ALLOWED_HOST_SUFFIXES = (
    ".susercontent.com",
    ".shopee.co.th",
    ".shopee.com",
)


class ProductGroundingError(RuntimeError):
    """Raised when a commercial job lacks a safe, usable product reference."""


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _assert_safe_public_https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def is_commercial_product_job(package: dict[str, Any]) -> bool:
    goal = str(package.get("goal") or "").strip().lower()
    placement = str(package.get("affiliate_placement") or "").strip().lower()
    content_type = str(package.get("content_type") or "").strip().lower()
    return (
        goal in {"conversion", "affiliate", "sales", "commerce"}
        or placement not in {"", "none"}
        or "affiliate" in content_type
        or "promo" in content_type
    )


def normalize_product_grounding(package: dict[str, Any]) -> dict[str, Any]:
    raw = package.get("product_grounding")
    grounding = dict(raw) if isinstance(raw, dict) else {}

    images = grounding.get("image_urls")
    if not isinstance(images, list):
        images = []
    image_urls = [
        str(value).strip()
        for value in images
        if str(value).strip()
    ]

    return {
        "version": str(grounding.get("version") or PRODUCT_GROUNDING_VERSION),
        "source": str(grounding.get("source") or "").strip(),
        "canonical_title": str(grounding.get("canonical_title") or "").strip(),
        "shop_name": str(grounding.get("shop_name") or "").strip(),
        "price": grounding.get("price"),
        "product_url": str(grounding.get("product_url") or "").strip(),
        "affiliate_url": str(grounding.get("affiliate_url") or "").strip(),
        "image_urls": image_urls,
        "identity_status": str(grounding.get("identity_status") or "").strip().upper(),
    }


def validate_product_grounding(package: dict[str, Any]) -> dict[str, Any]:
    grounding = normalize_product_grounding(package)
    if not grounding["canonical_title"]:
        raise ProductGroundingError("Product grounding requires canonical_title")
    if not grounding["image_urls"]:
        raise ProductGroundingError("Product grounding requires at least one product image URL")

    safe_urls = []
    for value in grounding["image_urls"]:
        _assert_safe_public_https_url(value)
        safe_urls.append(value)

    grounding["image_urls"] = safe_urls
    grounding["identity_status"] = "LOCKED"
    grounding["version"] = PRODUCT_GROUNDING_VERSION
    return grounding


def first_grounded_image_url(package: dict[str, Any]) -> str:
    grounding = validate_product_grounding(package)
    return str(grounding["image_urls"][0])


def download_grounded_product_image(
    image_url: str,
    *,
    timeout: int = 30,
) -> tuple[bytes, dict[str, object]]:
    _assert_safe_public_https_url(image_url)
    request = urllib.request.Request(
        image_url,
        headers={
            "User-Agent": "SoloForge-ProductGrounding/0.1",
            "Accept": "image/*",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if not content_type.startswith("image/"):
            raise ProductGroundingError("Grounded product URL did not return an image")
        data = response.read(_MAX_IMAGE_BYTES + 1)
        if len(data) > _MAX_IMAGE_BYTES:
            raise ProductGroundingError("Grounded product image is too large")
        if not data:
            raise ProductGroundingError("Grounded product image was empty")
        final_url = str(response.geturl() or image_url)
        _assert_safe_public_https_url(final_url)
        return data, {
            "provider": "product_source",
            "mode": "product_grounded",
            "provider_version": PRODUCT_GROUNDING_VERSION,
            "source_url": final_url,
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "content_type": content_type,
            "attempts": [
                {
                    "provider": "product_source",
                    "result": "success",
                    "source_url": final_url,
                }
            ],
        }


def _assert_safe_public_https_url(value: str) -> None:
    parsed = urllib.parse.urlparse(str(value).strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ProductGroundingError("Product image URL must be public HTTPS")
    if parsed.username or parsed.password:
        raise ProductGroundingError("Product image URL must not contain credentials")

    host = parsed.hostname.strip().lower()
    if host == "localhost" or host.endswith(".local"):
        raise ProductGroundingError("Product image URL must use a public host")
    if not _host_is_allowed(host):
        raise ProductGroundingError("Product image host is not allowlisted")

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
        raise ProductGroundingError("Product image host could not be resolved") from exc

    if not addresses:
        raise ProductGroundingError("Product image host could not be resolved")
    for address in addresses:
        _assert_public_ip(ipaddress.ip_address(address[4][0]))


def _assert_public_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if not address.is_global:
        raise ProductGroundingError("Product image URL resolved to a non-public address")



def _allowed_host_suffixes() -> tuple[str, ...]:
    configured = os.getenv("PRODUCT_GROUNDING_ALLOWED_HOSTS", "").strip()
    if not configured:
        return _DEFAULT_ALLOWED_HOST_SUFFIXES
    values = []
    for raw in configured.split(","):
        value = raw.strip().lower()
        if not value:
            continue
        values.append(value if value.startswith(".") else f".{value}")
    return tuple(values)


def _host_is_allowed(host: str) -> bool:
    normalized = host.strip().lower().rstrip(".")
    for suffix in _allowed_host_suffixes():
        bare = suffix.lstrip(".")
        if normalized == bare or normalized.endswith(suffix):
            return True
    return False
