from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ==========================
# Input
# ==========================

INPUT_FILE = ROOT / "data" / "raw" / "product_feed.csv"

ENCODING = "utf-8"

# ==========================
# Output
# ==========================

OUTPUT_DIR = ROOT / "data" / "processed"

# จำนวนสินค้าต่อไฟล์
CHUNK_SIZE = 50_000

# Prefix ของไฟล์ที่ Export
OUTPUT_PREFIX = "ranked_products"

# manifest
MANIFEST_FILE = OUTPUT_DIR / "manifest.json"