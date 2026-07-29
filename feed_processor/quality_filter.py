"""
SoloForge AI
Quality Filter

Filter low quality products before MiniBoss Analysis.
"""


def is_valid_product(product):
    """
    Return True if product should be kept.
    """

    # ==========================
    # Product Title
    # ==========================

    title = product.get("title", "").strip()

    if not title:
        return False

    # ==========================
    # Price
    # ==========================

    if product.get("price", 0) <= 0:
        return False

    # ==========================
    # Stock
    # ==========================

    if product.get("stock", 0) <= 0:
        print(product)
        return False

    # ==========================
    # Images
    # ==========================

    images = product.get("images", [])

    if not images:
        return False

    # ==========================
    # Product Link
    # ==========================

    product_link = (
        product.get("links", {})
        .get("product", "")
        .strip()
    )

    if not product_link:
        return False

    # ==========================
    # Commission
    # ==========================
    #
    # Enable after transformer.py
    # loads real commission data.
    #
    # Example:
    #
    # commission_rate = (
    #     product.get("commission", {})
    #     .get("rate", 0)
    # )
    #
    # if commission_rate <= 0:
    #     return False
    #
    # ==========================

    # ==========================
    # Rating (Optional)
    # ==========================
    #
    # if product.get("rating", 0) < 4.0:
    #     return False
    #
    # ==========================

    # ==========================
    # Sold Count (Optional)
    # ==========================
    #
    # if product.get("sold", 0) < 10:
    #     return False
    #
    # ==========================

    return True