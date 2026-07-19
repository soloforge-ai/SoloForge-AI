from reader import stream_rows
from cleaner import to_float

for row in stream_rows():

    print(row["title"])

    print("Price :", to_float(row["price"]))
    print("Rating:", to_float(row["item_rating"]))

    break

print("\nCleaner OK")