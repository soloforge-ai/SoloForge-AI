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
            (2, 1, 6, "", ("8.8.8.8", 443)),
        ],
    )
    package = {
        "product_grounding": {
            "source": "shopee",
            "canonical_title": "Magnetic Cable Clip",
            "shop_name": "Example Shop",
            "product_url": "https://shopee.co.th/item/1",
            "affiliate_url": "https://s.shopee.co.th/abc",
            "image_urls": ["https://down-th.img.susercontent.com/product.jpg"],
        }
    }

    result = product_grounding.validate_product_grounding(package)

    assert result["identity_status"] == "LOCKED"
    assert result["version"] == product_grounding.PRODUCT_GROUNDING_VERSION
    assert result["canonical_title"] == "Magnetic Cable Clip"
    assert result["image_urls"] == ["https://down-th.img.susercontent.com/product.jpg"]


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
                    "image_urls": ["https://down-th.img.susercontent.com/product.jpg"],
                }
            }
        )



def test_validate_product_grounding_rejects_unallowlisted_public_host(monkeypatch) -> None:
    monkeypatch.setattr(
        product_grounding.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("8.8.8.8", 443)),
        ],
    )

    with pytest.raises(product_grounding.ProductGroundingError, match="allowlisted"):
        product_grounding.validate_product_grounding(
            {
                "product_grounding": {
                    "canonical_title": "Product",
                    "image_urls": ["https://example.com/product.jpg"],
                }
            }
        )


def test_allowed_hosts_can_be_extended_by_env(monkeypatch) -> None:
    monkeypatch.setenv("PRODUCT_GROUNDING_ALLOWED_HOSTS", "cdn.example.com")
    monkeypatch.setattr(
        product_grounding.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (2, 1, 6, "", ("8.8.8.8", 443)),
        ],
    )

    result = product_grounding.validate_product_grounding(
        {
            "product_grounding": {
                "canonical_title": "Product",
                "image_urls": ["https://cdn.example.com/product.jpg"],
            }
        }
    )

    assert result["identity_status"] == "LOCKED"


def test_own_storage_product_reference_requires_exact_public_path(monkeypatch):
    from backend.product_grounding import _assert_safe_public_https_url, ProductGroundingError
    monkeypatch.setenv("SUPABASE_URL", "https://myproject.supabase.co")
    monkeypatch.setattr(
        "backend.product_grounding.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("8.8.8.8", 443))],
    )
    _assert_safe_public_https_url(
        "https://myproject.supabase.co/storage/v1/object/public/content-assets/product-references/job/a.png"
    )
    import pytest
    with pytest.raises(ProductGroundingError):
        _assert_safe_public_https_url(
            "https://myproject.supabase.co/storage/v1/object/public/other-bucket/secret.png"
        )
