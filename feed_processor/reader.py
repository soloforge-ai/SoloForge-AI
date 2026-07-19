import csv

from config import INPUT_FILE, ENCODING

csv.field_size_limit(1024 * 1024 * 100)


def stream_rows():
    with open(INPUT_FILE, "r", encoding=ENCODING, newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            yield row