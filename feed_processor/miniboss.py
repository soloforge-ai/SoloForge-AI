import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RULE_FILE = ROOT / "rules" / "miniboss_rules.json"


def load_rules():
    with open(RULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    
def create_score(
    name,
    score,
    value,
    max_value,
    weight,
    passed,
    reason=None,
):
    return {
        "name": name,
        "score": round(score, 2),
        "value": value,
        "max": max_value,
        "weight": weight,
        "passed": passed,
        "reason": reason,
    }


def score_rating(product, rules):

    rating = product.get("rating", 0)

    max_rating = rules["limits"]["rating"]
    weight = rules["weights"]["rating"]

    score = round((rating / max_rating) * weight, 2)

    return {
        "name": "rating",
        "score": score,
        "value": rating,
        "max": max_rating,
        "weight": weight,
        "passed": rating >= 4.5,
        "reason": f"High product rating ({rating}/{max_rating})"
        if rating >= 4.5
        else None,
    }

def analyze(product, rules):

    rating = score_rating(product, rules)
    shop_rating = score_shop_rating(product, rules)
    sold = score_sold(product, rules)
    discount = score_discount(product, rules)
    official = score_official(product, rules)
    preferred = score_preferred(product, rules)
    stock = score_stock(product, rules)

    breakdown = {
        rating["name"]: rating,
        shop_rating["name"]: shop_rating,
        sold["name"]: sold,
        discount["name"]: discount,
        official["name"]: official,
        preferred["name"]: preferred,
        stock["name"]: stock,
    }

    total_score = round(
        sum(item["score"] for item in breakdown.values()),
        2,
    )

    reasons = [
        item["reason"]
        for item in breakdown.values()
        if item.get("reason")
    ]

    return {
    "score": total_score,
    "grade": calculate_grade(total_score),
    "breakdown": breakdown,
    "reasons": reasons,
}

def score_shop_rating(product, rules):

    rating = product.get("shop", {}).get("rating", 0)

    max_rating = rules["limits"]["shop_rating"]
    weight = rules["weights"]["shop_rating"]

    score = (rating / max_rating) * weight

    return create_score(
        name="shop_rating",
        score=score,
        value=rating,
        max_value=max_rating,
        weight=weight,
        passed=rating >= 4.5,
        reason=(
            f"High shop rating ({rating}/{max_rating})"
            if rating >= 4.5
            else None
        ),
    )


def score_sold(product, rules):

    sold = product.get("sold", 0)

    max_sold = rules["limits"]["sold"]
    weight = rules["weights"]["sold"]

    score = min(sold, max_sold) / max_sold * weight

    return create_score(
        name="sold",
        score=score,
        value=sold,
        max_value=max_sold,
        weight=weight,
        passed=sold >= 100,
        reason=(
            f"Popular product ({sold} sold)"
            if sold >= 100
            else None
        ),
    )


def score_discount(product, rules):

    discount = product.get("discount", 0)

    max_discount = rules["limits"]["discount"]
    weight = rules["weights"]["discount"]

    score = min(discount, max_discount) / max_discount * weight

    return create_score(
        name="discount",
        score=score,
        value=discount,
        max_value=max_discount,
        weight=weight,
        passed=discount >= 30,
        reason=(
            f"{discount:.1f}% discount"
            if discount >= 30
            else None
        ),
    )


def score_official(product, rules):

    official = product.get("shop", {}).get("official", False)

    weight = rules["weights"]["official_shop"]

    score = weight if official else 0

    return create_score(
        name="official_shop",
        score=score,
        value=official,
        max_value=True,
        weight=weight,
        passed=official,
        reason="Official Shop" if official else None,
    )


def score_preferred(product, rules):

    preferred = product.get("shop", {}).get("preferred", False)

    weight = rules["weights"]["preferred_shop"]

    score = weight if preferred else 0

    return create_score(
        name="preferred_shop",
        score=score,
        value=preferred,
        max_value=True,
        weight=weight,
        passed=preferred,
        reason="Preferred Shop" if preferred else None,
    )


def score_stock(product, rules):

    stock = product.get("stock", 0)

    weight = rules["weights"]["stock"]

    score = weight if stock > 0 else 0

    return create_score(
        name="stock",
        score=score,
        value=stock,
        max_value=1,
        weight=weight,
        passed=stock > 0,
        reason="In Stock" if stock > 0 else None,
    )

def calculate_grade(score):

    if score >= 90:
        return "A"

    if score >= 75:
        return "B"

    if score >= 60:
        return "C"

    if score >= 40:
        return "D"

    return "E"