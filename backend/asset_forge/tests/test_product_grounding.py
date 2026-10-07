from __future__ import annotations

import pytest

from backend.asset_forge.backend import product_grounding


def test_commercial_product_detection() -> None:
    assert product_grounding.is_commercial_product_job({"goal": "conversion"})
    assert product_grounding.is_commercial_product_job({"affiliate_placement": "comment"})
    assert product_grounding.is_commercial_product_job({"content_type": "promo_post"})
    assert not product_grounding.is_commercial_product_job({"goal": "education"})


def test_validate_product_grounding_locks_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        product_grounding.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("203.0.113.10", 443)),
        ],
    )
    package = {
        "product_grounding": {
            "source": "shopee",
            "canonical_title": "Magnetic Cable Clip",
            "shop_name": "Example Shop",
            "product_url": "https://shopee.example/item/1",
            "affiliate_url": "https://s.shopee.example/abc",
            "image_urls": ["https://cdn.example/product.jpg"],
        }
    }

    result = product_grounding.validate_product_grounding(package)

    assert result["identity_status"] == "LOCKED"
    assert result["version"] == product_grounding.PRODUCT_GROUNDING_VERSION
    assert result["canonical_title"] == "Magnetic Cable Clip"
    assert result["image_urls"] == ["https://cdn.example/product.jpg"]


def test_validate_product_grounding_requires_image() -> None:
    with pytest.raises(product_grounding.ProductGroundingError, match="image URL"):
        product_grounding.validate_product_grounding(
            {"product_grounding": {"canonical_title": "Product"}}
        )


def test_validate_product_grounding_rejects_private_host(monkeypatch) -> None:
    monkeypatch.setattr(
        product_grounding.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("127.0.0.1", 443)),
        ],
    )

    with pytest.raises(product_grounding.ProductGroundingError, match="non-public"):
        product_grounding.validate_product_grounding(
            {
                "product_grounding": {
                    "canonical_title": "Product",
                    "image_urls": ["https://internal.example/product.jpg"],
                }
            }
        )
