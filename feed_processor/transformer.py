from cleaner import to_float


def transform_row(row):
    return {
        "title": row["title"],
        "price": to_float(row["price"]),
        "sale_price": to_float(row["sale_price"]),
        "rating": to_float(row["item_rating"]),
        "brand": row["global_brand"],
        "seller": row["seller_name"],
        "shop": row["shop_name"],
        "category": " > ".join(
            filter(
                None,
                [
                    row["global_category1"],
                    row["global_category2"],
                    row["global_category3"],
                ],
            )
        ),
    }