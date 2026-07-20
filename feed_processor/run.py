from time import perf_counter

from reader import stream_rows
from transformer import transform_row
from miniboss import load_rules, analyze
from exporter import JsonlExporter
from manifest import write_manifest


def main():

    rules = load_rules()

    start = perf_counter()

    processed = 0

    with JsonlExporter() as exporter:

        for row in stream_rows():

            product = transform_row(row)

            miniboss = analyze(product, rules)

            product["miniboss"] = miniboss

            exporter.write(product)

            processed += 1

            if processed % 10000 == 0:

                elapsed = perf_counter() - start

                speed = processed / elapsed if elapsed else 0

                print(
                    f"\rProcessed: {processed:,} products | "
                    f"{speed:,.0f} products/sec",
                    end="",
                    flush=True,
                )

        write_manifest(exporter)

    elapsed = perf_counter() - start

    speed = processed / elapsed if elapsed else 0

    print("\n")
    print("=" * 50)
    print("Processing Complete")
    print("=" * 50)
    print(f"Products      : {processed:,}")
    print(f"Chunks        : {len(exporter.chunk_files)}")
    print(f"Time          : {elapsed:.2f} sec")
    print(f"Speed         : {speed:,.0f} products/sec")
    print(f"Output Folder : data/processed")
    print("=" * 50)


if __name__ == "__main__":
    main()