import csv

# อ่านรหัสจาก Master Catalog
master_ids = set()

with open("../data/raw/Shopee_MasterCatalog.csv", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        master_ids.add(row["รหัสสินค้า"].strip())

print("Master IDs:", len(master_ids))

# นับจำนวนที่ตรงกับ Product Feed
matches = 0

with open("../data/raw/product_feed.csv", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["itemid"].strip() in master_ids:
            matches += 1

print("Matched:", matches)