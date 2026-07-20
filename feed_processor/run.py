from reader import stream_rows
from transformer import transform_row

for row in stream_rows():
    product = transform_row(row)

    print(product)

    break

print("\nTransformer OK")