"""Inspect the FDA Press Releases collection to understand schema and content."""
import os
import certifi
from collections import Counter
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())
db = client[os.environ["MONGODB_DB"]]
coll = db[os.environ["MONGODB_COLLECTION"]]

total = coll.count_documents({})
print(f"Total documents: {total}")

# Field frequency
print("\n--- Field frequency in first 500 docs ---")
field_counts = Counter()
for doc in coll.find({}, limit=500):
    for k in doc.keys():
        field_counts[k] += 1
for k, v in field_counts.most_common():
    print(f"  {k}: {v}")

# Show 3 sample docs
print("\n--- 3 sample documents ---")
for i, doc in enumerate(coll.find({}, limit=3)):
    print(f"\n[{i}]")
    for k, v in doc.items():
        s = str(v)
        if len(s) > 400:
            s = s[:400] + "...<truncated>"
        print(f"  {k}: {s}")

# Year coverage if there's a date field
print("\n--- Year distribution (probe for date/year fields) ---")
for year_field in ["year", "date", "publication_date", "release_date", "press_release_date"]:
    sample = coll.find_one({year_field: {"$exists": True}})
    if sample:
        print(f"  Found field: {year_field} -> example value: {sample.get(year_field)}")

# Check if line_of_therapy already exists
existing_lot = coll.count_documents({"line_of_therapy": {"$exists": True}})
print(f"\nDocs with 'line_of_therapy' already set: {existing_lot}")

# Description length stats
print("\n--- Description length sampling ---")
desc_lengths = []
for doc in coll.find({"description": {"$exists": True}}, {"description": 1}, limit=200):
    if isinstance(doc.get("description"), str):
        desc_lengths.append(len(doc["description"]))
if desc_lengths:
    print(f"  count: {len(desc_lengths)}")
    print(f"  min: {min(desc_lengths)}")
    print(f"  max: {max(desc_lengths)}")
    print(f"  avg: {sum(desc_lengths)//len(desc_lengths)}")
