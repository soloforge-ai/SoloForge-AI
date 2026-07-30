from datetime import datetime

from cleaner import to_float


def to_bool(value):
    """
    Convert Shopee boolean-like values to bool.
    """

    value = str(value).strip().lower()

    return value in {
        "true",
        "1",
        "yes",
        "official shop",
        "preferred shop",
        "official",
        "preferred",
        "on",
    }


def transform_row(row):

    return {

        # ==================================================
        # Basic
        # ==================================================

        "id": str(row.get("itemid", "")).strip(),
        "itemid": str(row.get("itemid", "")).strip(),
        "source": "shopee",

        # ==================================================
        # Product
        # ==================================================

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
        "discount": to_float(row.get("discount_percentage")),

        "rating": to_float(row.get("item_rating")),
        "sold": int(to_float(row.get("item_sold")) or 0),
        "stock": int(to_float(row.get("stock")) or 0),

        # ==================================================
        # Shop
        # ==================================================

        "shop": {

            "name": row.get("shop_name", ""),
            "seller": row.get("seller_name", ""),
            "rating": to_float(row.get("shop_rating")),

            "official": to_bool(
                row.get("is_official_shop")
            ),

            "preferred": to_bool(
                row.get("is_preferred_shop")
            ),

        },

        # ==================================================
        # Commission
        # (จะถูก Merge จาก MasterCatalog)
        # ==================================================

        "commission": {

            "rate": 0.0,
            "amount": 0.0,

        },

        # ==================================================
        # Images
        # ==================================================

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

        # ==================================================
        # Links
        # (จะถูกแทนที่โดย merge_catalog.py)
        # ==================================================

        "links": {

            "product": row.get("product_link", ""),

            "short":
                row.get("product_short_link")
                or row.get("product_short link")
                or "",

        },

        # ==================================================
        # Metadata
        # ==================================================

        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),

    }