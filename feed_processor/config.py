from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

INPUT_FILE = RAW_DIR / "product_feed.csv"

ENCODING = "utf-8-sig"