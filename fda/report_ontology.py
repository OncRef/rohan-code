"""Distribution report for the ontology-extracted columns."""
import os
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

coll = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())[
    os.environ["MONGODB_DB"]
][os.environ["MONGODB_COLLECTION"]]

total = coll.count_documents({})
covered = coll.count_documents({"ontology_extracted_at": {"$exists": True}})
print(f"Total: {total}    Ontology-extracted: {covered}    Coverage: {covered/total:.1%}")

# How many have any LOT match
with_lot = coll.count_documents({"lot_canonical.0": {"$exists": True}})
no_lot = coll.count_documents({"lot_canonical": {"$size": 0}})
print(f"\nDocs with >=1 LOT canonical match: {with_lot}    With 0: {no_lot}")

with_stage = coll.count_documents({"stage_canonical.0": {"$exists": True}})
no_stage = coll.count_documents({"stage_canonical": {"$size": 0}})
print(f"Docs with >=1 stage canonical match: {with_stage}    With 0: {no_stage}")

print("\n--- Top LOT canonical names ---")
for r in coll.aggregate([
    {"$unwind": "$lot_canonical"},
    {"$group": {"_id": "$lot_canonical", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]):
    print(f"  {r['_id']:42s}  {r['n']}")

print("\n--- Top stage canonical names (top 30) ---")
for r in coll.aggregate([
    {"$unwind": "$stage_canonical"},
    {"$group": {"_id": "$stage_canonical", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
    {"$limit": 30},
]):
    print(f"  {r['_id']:30s}  {r['n']}")

print("\n--- Cross-check: ontology lot vs LLM line_of_therapy (first 12) ---")
for d in coll.find({}, {"brand_name":1,"year":1,"line_of_therapy":1,
                        "lot_canonical":1,"stage_canonical":1}).limit(12):
    bn = (d.get("brand_name") or "?")[:22]
    print(f"  {d.get('year')} {bn:22s} | LLM-LOT={d.get('line_of_therapy','?'):20s} | "
          f"ontology-LOT={d.get('lot_canonical') or '[]'} | "
          f"stage={(d.get('stage_canonical') or [])[:5]}")
