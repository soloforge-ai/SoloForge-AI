from pprint import pprint

from reader import stream_rows
from transformer import transform_row
from miniboss import load_rules, analyze


def main():
    rules = load_rules()

    row = next(stream_rows())

    product = transform_row(row)

    print("=" * 80)
    print("RAW CSV")
    print(f"shop_rating          : {row.get('shop_rating')}")
    print(f"discount_percentage  : {row.get('discount_percentage')}")
    print()

    print("=" * 80)
    print("TRANSFORMED PRODUCT")
    pprint(product, sort_dicts=False)
    print()

    print("=" * 80)
    print("CHECK IMPORTANT FIELDS")
    print(f"Product Rating : {product['rating']}")
    print(f"Shop Rating    : {product['shop']['rating']}")
    print(f"Discount       : {product['discount']}")
    print(f"Sold           : {product['sold']}")
    print(f"Stock          : {product['stock']}")
    print()

    result = analyze(product, rules)

    print("=" * 80)
    print("MINIBOSS RESULT")
    pprint(result, sort_dicts=False)


if __name__ == "__main__":
    main()