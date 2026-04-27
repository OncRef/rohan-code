"""Inspect current broad_cancer values in the DB."""
import os
import certifi
from collections import Counter
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

coll = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())[
    os.environ["MONGODB_DB"]
][os.environ["MONGODB_COLLECTION"]]

print("--- Current broad_cancer distribution ---")
pipe = [{"$group": {"_id": "$broad_cancer", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}]
for row in coll.aggregate(pipe):
    print(f"  {str(row['_id']):40s}  {row['n']}")

print("\n--- Sample (broad_cancer, extracted_cancer) pairs (20) ---")
for d in coll.find({}, {"broad_cancer": 1, "extracted_cancer": 1, "brand_name": 1, "year": 1}).limit(20):
    bc = (d.get("broad_cancer") or "")[:30]
    ec = (d.get("extracted_cancer") or "")[:60]
    print(f"  {d.get('year')} {d.get('brand_name','?')[:25]:25s} | {bc:30s} | {ec}")
