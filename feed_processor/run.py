from time import perf_counter

from reader import stream_rows
from transformer import transform_row
from miniboss import load_rules, analyze
from exporter import JsonlExporter
from manifest import write_manifest
from quality_filter import is_valid_product
from statistics import StatisticsCollector


def main():

    rules = load_rules()

    stats = StatisticsCollector()

    start = perf_counter()

    processed = 0
    filtered = 0

    with JsonlExporter() as exporter:

        for row in stream_rows():

            # ==========================
            # Transform
            # ==========================

            product = transform_row(row)

            # ==========================
            # Quality Filter
            # ==========================

            if not is_valid_product(product):
                filtered += 1
                continue

            # ==========================
            # MiniBoss Analysis
            # ==========================

            miniboss = analyze(product, rules)

            product["miniboss"] = miniboss

            # Flat score for sorting/searching
            product["miniBossScore"] = miniboss["score"]

            # ==========================
            # Statistics
            # ==========================

            stats.add(product)

            # ==========================
            # Export
            # ==========================

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

        # ==========================
        # Output Files
        # ==========================

        write_manifest(exporter)

        stats.write()

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
    print("=" * 60)


if __name__ == "__main__":
    main()