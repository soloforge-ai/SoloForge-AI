from time import perf_counter

from reader import stream_rows
from transformer import transform_row
from merge_catalog import CatalogMerger
from miniboss import load_rules, analyze
from exporter import JsonlExporter
from manifest import write_manifest
from quality_filter import is_valid_product
from statistics import StatisticsCollector
from matched_exporter import MatchedExporter

def main():

    # ---------------------------------------------
    # Load Rules
    # ---------------------------------------------

    rules = load_rules()

    # ---------------------------------------------
    # Load Master Catalog
    # ---------------------------------------------

    merger = CatalogMerger()
    merger.load()

    # ---------------------------------------------
    # Statistics
    # ---------------------------------------------

    stats = StatisticsCollector()
    matched_exporter = MatchedExporter()
    start = perf_counter()

    processed = 0
    filtered = 0

    # ---------------------------------------------
    # Export
    # ---------------------------------------------

    with JsonlExporter() as exporter:

        for row in stream_rows():

            # -------------------------------------
            # Transform
            # -------------------------------------

            product = transform_row(row)

            # -------------------------------------
            # Merge Master Catalog
            # -------------------------------------

            product = merger.merge(product)

            # -------------------------------------
            # Quality Filter
            # -------------------------------------

            if not is_valid_product(product):
                filtered += 1
                continue

            # -------------------------------------
            # MiniBoss
            # -------------------------------------

            miniboss = analyze(product, rules)

            product["miniboss"] = miniboss
            product["miniBossScore"] = miniboss["score"]

            matched_exporter.add(product)

            # -------------------------------------
            # Statistics
            # -------------------------------------

            stats.add(product)

            # -------------------------------------
            # Export
            # -------------------------------------

            exporter.write(product)

            processed += 1

            if processed % 10000 == 0:

                elapsed = perf_counter() - start

                speed = processed / elapsed if elapsed else 0

                print(
                    f"\rProcessed: {processed:,} | "
                    f"Filtered: {filtered:,} | "
                    f"Speed: {speed:,.0f} products/sec",
                    end="",
                    flush=True,
                )

        # -----------------------------------------
        # Output Files
        # -----------------------------------------

        write_manifest(exporter)

        stats.write()
        merger.summary()
        matched_exporter.write()

    elapsed = perf_counter() - start

    speed = processed / elapsed if elapsed else 0

    print()
    print("=" * 60)
    print("Feed Processor Complete")
    print("=" * 60)
    print(f"Processed      : {processed:,}")
    print(f"Filtered Out   : {filtered:,}")
    print(f"Chunks         : {len(exporter.chunk_files)}")
    print(f"Time           : {elapsed:.2f} sec")
    print(f"Speed          : {speed:,.0f} products/sec")
    print("Output Folder  : data/processed")
    print("Statistics     : data/processed/stats.json")
    print("Matched Catalog: data/processed/catalog_matched.json")
    print(f"Matched Items  : {matched_exporter.count:,}")

    print("=" * 60)


if __name__ == "__main__":
    main()