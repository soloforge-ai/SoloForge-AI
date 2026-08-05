"""
SoloForge AI
Product Discovery Engine

Sprint 44
Production Version

Read ranked JSONL files
↓
Category Filter
↓
Category Ranker
↓
top_products.json
↓
Category Export
↓
category_index.json
↓
Discovery Statistics
"""

import json
from datetime import datetime
from pathlib import Path

from category_filter import CategoryFilter
from content_filter import ContentFilter
from category_ranker import CategoryRanker
from category_exporter import export_categories

ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "data" / "discovery"

OUTPUT_FILE = OUTPUT_DIR / "top_products.json"
STATS_FILE = OUTPUT_DIR / "discovery_stats.json"
REPORT_FILE = OUTPUT_DIR / "discovery_report.json"

TOP_N = 200


# ----------------------------------------------------------
# Read JSONL
# ----------------------------------------------------------

def iter_products():

    files = sorted(INPUT_DIR.glob("ranked_products_*.jsonl"))

    print("=" * 60)
    print(f"Found {len(files)} JSONL files")
    print("=" * 60)

    for file in files:

        print(f"Reading {file.name}")

        with open(file, "r", encoding="utf-8") as f:

            for line in f:

                line = line.strip()

                if not line:
                    continue

                try:
                    yield json.loads(line)

                except json.JSONDecodeError:
                    continue


# ----------------------------------------------------------
# Statistics
# ----------------------------------------------------------

def build_statistics(result, processed, filtered):

    exported_products = sum(
        len(products)
        for products in result.values()
    )

    category_statistics = []

    for category, products in sorted(result.items()):

        if not products:
            continue

        scores = [
            p.get("miniBossScore", 0)
            for p in products
        ]

        category_statistics.append({

            "category": category,

            "products": len(products),

            "top_score": max(scores),

            "average_score": round(
                sum(scores) / len(scores),
                2,
            )

        })

    return {

        "processed_products": processed,

        "filtered_products": filtered,

        "categories": len(result),

        "exported_products": exported_products,

        "coverage_percent": round(
            exported_products / filtered * 100,
            2,
        ) if filtered else 0,

        "top_n": TOP_N,

        "category_statistics": category_statistics

    }


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------

def main():

    category_filter = CategoryFilter()

    content_filter = ContentFilter()

    ranker = CategoryRanker(
        top_n=TOP_N
    )

    processed = 0
    filtered = 0

    for product in iter_products():

        processed += 1

        # ----------------------------------------------
        # Category Filter
        # ----------------------------------------------

        if not category_filter.accept(product):
            continue

        # ----------------------------------------------
        # Content Filter
        # ----------------------------------------------

        if not content_filter.accept(product):
            continue

        filtered += 1

        ranker.add(product)

        if processed % 100000 == 0:

            print(
                f"Processed : {processed:,}"
            )

    result = ranker.finish()

    stats = build_statistics(
        result,
        processed,
        filtered,
    )

    # ------------------------------------------------------
    # Discovery Report
    # ------------------------------------------------------

    report = {
        "version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": stats,
        "content_filter": content_filter.get_statistics(),
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ------------------------------------------------------
    # Export Discovery Catalog
    # ------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ------------------------------------------------------
    # Export Category Files
    # ------------------------------------------------------

    export_categories(result)

    # ------------------------------------------------------
    # Export Statistics
    # ------------------------------------------------------

    with open(
        STATS_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            stats,
            f,
            ensure_ascii=False,
            indent=2,
        )
    
    # ------------------------------------------------------
    # Export Discovery Report
    # ------------------------------------------------------

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()

    print("=" * 60)
    print("Product Discovery Complete")
    print("=" * 60)
    print(f"Products Processed : {processed:,}")
    print(f"Products Filtered  : {filtered:,}")
    print(f"Categories         : {stats['categories']}")
    print(f"Products Exported  : {stats['exported_products']:,}")
    print(f"Coverage           : {stats['coverage_percent']}%")
    print(f"Top N              : {TOP_N}")
    print()

    print(f"Discovery Output   : {OUTPUT_FILE}")
    print(f"Category Export    : {OUTPUT_DIR / 'categories'}")
    print(f"Category Index     : {OUTPUT_DIR / 'category_index.json'}")
    print(f"Statistics Output  : {STATS_FILE}")
    print(f"Discovery Report   : {REPORT_FILE}")

    content_filter.print_statistics()

    print("=" * 60)


if __name__ == "__main__":
    main()