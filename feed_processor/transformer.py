from cleaner import to_float
from datetime import datetime

def to_bool(value):
    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
    }

def transform_row(row):
    return {
        "id": row.get("itemid", ""),
        "source": "shopee",

        "title": row.get("title", ""),
        "brand": row.get("global_brand", ""),
        "category": " > ".join(
            filter(
                None,
                [
                    row.get("global_category1", ""),
                    row.get("global_category2", ""),
                    row.get("global_category3", ""),
                ],
            )
        ),

        "price": to_float(row.get("price")),
        "sale_price": to_float(row.get("sale_price")),

        "rating": to_float(row.get("item_rating")),
        "sold": int(to_float(row.get("item_sold")) or 0),

        "shop": {
            "name": row.get("shop_name", ""),
            "seller": row.get("seller_name", ""),
            "official": to_bool(row.get("is_official_shop")),
            "preferred": to_bool(row.get("is_preferred_shop")),
        },

        "commission": {
            "rate": 0.0,
            "amount": 0.0,
        },

        "images": [
            image
            for image in [
                row.get("image_link", ""),
                row.get("image_link_2", ""),
                row.get("image_link_3", ""),
                row.get("image_link_4", ""),
                row.get("image_link_5", ""),
                row.get("image_link_6", ""),
                row.get("image_link_7", ""),
                row.get("image_link_8", ""),
                row.get("image_link_9", ""),
                row.get("image_link_10", ""),
            ]
            if image
        ],

        "links": {
            "product": row.get("product_link", ""),
            "short": row.get("product_short link", ""),
        },

        "created_at": datetime.now().isoformat(timespec="seconds"),
    }