"""
SoloForge AI
Chunk Exporter

Sprint 45.5
Production Version

Split Level 1 Discovery Database
into chunk files.

Level 1 Catalog
↓

Chunk Files

↓

chunk_index.json
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    ROOT
    / "data"
    / "discovery"
)

CATEGORY_DIR = (
    OUTPUT_DIR
    / "categories"
)


# ----------------------------------------------------------
# Config
# ----------------------------------------------------------

CHUNK_SIZE = 1000


# ----------------------------------------------------------
# Split Products
# ----------------------------------------------------------

def split_chunks(products):

    for i in range(
        0,
        len(products),
        CHUNK_SIZE,
    ):

        yield products[
            i:i + CHUNK_SIZE
        ]


# ----------------------------------------------------------
# Export Chunk Database
# ----------------------------------------------------------

def export_chunks(
    level1_catalog,
    category_index,
):

    if CATEGORY_DIR.exists():
        shutil.rmtree(CATEGORY_DIR)

    CATEGORY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    
    total_categories = 0
    total_chunks = 0
    total_products = 0

    # ------------------------------------------------------

    for (
        category,
        subcategories,
    ) in sorted(
        level1_catalog.items()
    ):

        safe_name = (
            category
            .replace("&", "and")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(" ", "_")
        )

        category_dir = (
            CATEGORY_DIR
            / safe_name
        )

        category_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ----------------------------------------------
        # Merge Every Subcategory
        # ----------------------------------------------

        merged_products = []

        for products in subcategories.values():

            merged_products.extend(
                products
            )

        # ----------------------------------------------

        chunk_files = []

        chunks = list(
            split_chunks(
                merged_products
            )
        )

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):

            filename = (
                f"chunk_{index:04d}.json"
            )

            filepath = (
                category_dir
                / filename
            )

            payload = {

                "category": category,

                "chunk": index,

                "chunk_count": len(chunks),

                "product_count": len(chunk),

                "products": chunk,

            }

            with open(
                filepath,
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    payload,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            chunk_files.append(
                f"categories/"
                f"{safe_name}/"
                f"{filename}"
            )

            total_chunks += 1

        # ----------------------------------------------

        category_index[category][
            "chunk_count"
        ] = len(chunks)

        category_index[category][
            "chunks"
        ] = chunk_files

        total_products += len(
            merged_products
        )

        total_categories += 1

    
    # ------------------------------------------------------

    print()

    print("=" * 60)
    print("Chunk Export Complete")
    print("=" * 60)

    print(
        f"Categories      : {total_categories}"
    )

    print(
        f"Chunks          : {total_chunks}"
    )

    print(
        f"Products        : {total_products:,}"
    )

    print(
        f"Chunk Size      : {CHUNK_SIZE:,}"
    )

    print()

    print(
        f"Output Directory : {CATEGORY_DIR}"
    )

    print(
        "Category Index Updated"
    )

    print("=" * 60)

    return category_index