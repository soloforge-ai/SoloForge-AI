from __future__ import annotations

import pytest

from backend.asset_forge.backend import product_resolver


class _FakeResponse:
    def __init__(self, html: str, *, url: str = "https://shopee.co.th/product/10/20") -> None:
        self._data = html.encode("utf-8")
        self._url = url
        self.headers = {"Content-Type": "text/html; charset=utf-8"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def geturl(self) -> str:
        return self._url

    def read(self, amount: int = -1) -> bytes:
        if amount < 0:
            return self._data
        return self._data[:amount]


class _FakeOpener:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response

    def open(self, request, timeout=0):
        return self.response


def _public_dns(*args, **kwargs):
    return [(2, 1, 6, "", ("8.8.8.8", 443))]


def test_resolve_shopee_short_url_from_open_graph(monkeypatch) -> None:
    html = """
    <html><head>
      <meta property="og:title" content="Magnetic Cable Clip | Shopee Thailand">
      <meta property="og:image" content="https://down-th.img.susercontent.com/file/product.jpg">
      <meta property="product:price:amount" content="191">
    </head></html>
    """
    monkeypatch.setattr(product_resolver.socket, "getaddrinfo", _public_dns)
    monkeypatch.setattr(
        product_resolver.urllib.request,
        "build_opener",
        lambda *args: _FakeOpener(_FakeResponse(html)),
    )

    result = product_resolver.resolve_shopee_product(
        "https://s.shopee.co.th/abc123"
    )

    grounding = result["grounding"]
    assert result["provider"] == "shopee"
    assert result["resolver_version"] == "shopee_product_resolver_v0.1"
    assert result["resolved_url"] == "https://shopee.co.th/product/10/20"
    assert grounding["canonical_title"] == "Magnetic Cable Clip"
    assert grounding["price"] == "191"
    assert grounding["affiliate_url"] == "https://s.shopee.co.th/abc123"
    assert grounding["image_urls"] == [
        "https://down-th.img.susercontent.com/file/product.jpg"
    ]


def test_resolve_shopee_uses_json_ld_fallback(monkeypatch) -> None:
    html = """
    <html><head>
      <script type="application/ld+json">
      {
        "@type": "Product",
        "name": "Desk Organizer",
        "image": [
          "https://down-th.img.susercontent.com/file/one.jpg",
          "https://down-th.img.susercontent.com/file/two.jpg"
        ],
        "brand": {"name": "Example Brand"},
        "offers": {
          "@type": "Offer",
          "price": "89",
          "seller": {"@type": "Organization", "name": "Example Shop"}
        }
      }
      </script>
    </head></html>
    """
    monkeypatch.setattr(product_resolver.socket, "getaddrinfo", _public_dns)
    monkeypatch.setattr(
        product_resolver.urllib.request,
        "build_opener",
        lambda *args: _FakeOpener(_FakeResponse(html)),
    )

    result = product_resolver.resolve_shopee_product(
        "https://shopee.co.th/product/10/20"
    )

    grounding = result["grounding"]
    assert grounding["canonical_title"] == "Desk Organizer"
    assert grounding["shop_name"] == "Example Shop"
    assert grounding["price"] == "89"
    assert len(grounding["image_urls"]) == 2
    assert grounding["affiliate_url"] == ""


def test_resolve_rejects_non_shopee_host() -> None:
    with pytest.raises(
        product_resolver.ProductResolverError,
        match="allowlisted Shopee host",
    ):
        product_resolver.resolve_shopee_product("https://example.com/product/1")


def test_resolve_rejects_private_shopee_dns(monkeypatch) -> None:
    monkeypatch.setattr(
        product_resolver.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))],
    )

    with pytest.raises(product_resolver.ProductResolverError, match="non-public"):
        product_resolver.resolve_shopee_product(
            "https://shopee.co.th/product/10/20"
        )


def test_resolve_requires_title_and_image(monkeypatch) -> None:
    monkeypatch.setattr(product_resolver.socket, "getaddrinfo", _public_dns)
    monkeypatch.setattr(
        product_resolver.urllib.request,
        "build_opener",
        lambda *args: _FakeOpener(_FakeResponse("<html><head></head></html>")),
    )

    with pytest.raises(
        product_resolver.ProductResolverError,
        match="title could not be resolved",
    ):
        product_resolver.resolve_shopee_product(
            "https://shopee.co.th/product/10/20"
        )
