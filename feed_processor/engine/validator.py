"""
SoloForge AI
MiniBoss Engine V2

Product Validator
"""

REQUIRED_FIELDS = (
    "rating",
    "sold",
    "stock",
)


def validate_product(product):
    """
    Validate required product fields.
    """

    for field in REQUIRED_FIELDS:

        if field not in product:
            return False

    return True