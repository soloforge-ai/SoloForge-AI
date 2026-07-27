"""
SoloForge AI
MiniBoss Engine V2

Score Builder
"""

from .rating import score_rating
from .shop_rating import score_shop_rating
from .sold import score_sold
from .discount import score_discount
from .official import score_official
from .preferred import score_preferred
from .stock import score_stock


def build_scores(product, rules):
    """
    Execute every scoring engine.
    """

    return [
        score_rating(product, rules),
        score_shop_rating(product, rules),
        score_sold(product, rules),
        score_discount(product, rules),
        score_official(product, rules),
        score_preferred(product, rules),
        score_stock(product, rules),
    ]