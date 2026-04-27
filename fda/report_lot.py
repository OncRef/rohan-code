"""Report on the line_of_therapy field after extraction."""
import os
import certifi
from collections import Counter
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

coll = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())[
    os.environ["MONGODB_DB"]
][os.environ["MONGODB_COLLECTION"]]

total = coll.count_documents({})
with_lot = coll.count_documents({"line_of_therapy": {"$exists": True}})
print(f"Total docs: {total}")
print(f"Docs with line_of_therapy set: {with_lot}")
print(f"Coverage: {with_lot/total:.1%}")

print("\n--- Line-of-therapy distribution ---")
pipe = [{"$group": {"_id": "$line_of_therapy", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}]
for row in coll.aggregate(pipe):
    print(f"  {str(row['_id']):24s}  {row['n']}")

print("\n--- Confidence distribution ---")
pipe = [{"$group": {"_id": "$line_of_therapy_confidence", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}]
for row in coll.aggregate(pipe):
    print(f"  {str(row['_id']):10s}  {row['n']}")

print("\n--- Low-confidence samples (up to 10) ---")
for d in coll.find({"line_of_therapy_confidence": "low"},
                   {"brand_name": 1, "year": 1, "line_of_therapy": 1, "headline": 1}).limit(10):
    print(f"  {d.get('year')} {d.get('brand_name','?')[:30]:30s} -> "
          f"{d.get('line_of_therapy')} :: {d.get('headline','')[:80]}")

print("\n--- Unspecified samples (up to 10) ---")
for d in coll.find({"line_of_therapy": "Unspecified"},
                   {"brand_name": 1, "year": 1, "headline": 1}).limit(10):
    print(f"  {d.get('year')} {d.get('brand_name','?')[:30]:30s} :: {d.get('headline','')[:80]}")
