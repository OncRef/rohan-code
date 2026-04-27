"""Report on the remapped broad_cancer / heme_subcancer fields."""
import os
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

coll = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())[
    os.environ["MONGODB_DB"]
][os.environ["MONGODB_COLLECTION"]]

total = coll.count_documents({})
remapped = coll.count_documents({"broad_cancer_remapped_at": {"$exists": True}})
print(f"Total docs: {total}    Remapped: {remapped}    Coverage: {remapped/total:.1%}")

print("\n--- Remapped broad_cancer distribution ---")
for r in coll.aggregate([
    {"$group": {"_id": "$broad_cancer", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]):
    print(f"  {str(r['_id']):42s}  {r['n']}")

print("\n--- heme_subcancer distribution (Hematological Malignancies only) ---")
for r in coll.aggregate([
    {"$match": {"broad_cancer": "Hematological Malignancies"}},
    {"$group": {"_id": "$heme_subcancer", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]):
    label = r["_id"] if r["_id"] else "(no canonical sub)"
    print(f"  {label:55s}  {r['n']}")

print("\n--- Confidence distribution ---")
for r in coll.aggregate([
    {"$group": {"_id": "$broad_cancer_confidence", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]):
    print(f"  {str(r['_id']):10s}  {r['n']}")

print("\n--- Legacy -> new transitions (top 25) ---")
for r in coll.aggregate([
    {"$group": {
        "_id": {"old": "$broad_cancer_legacy", "new": "$broad_cancer"},
        "n": {"$sum": 1},
    }},
    {"$sort": {"n": -1}},
    {"$limit": 25},
]):
    old = r["_id"]["old"] or "(none)"
    new = r["_id"]["new"] or "(none)"
    print(f"  {old:25s} -> {new:42s}  {r['n']}")

print("\n--- 'Other' bucket (sample of 20) — verify these are truly off-taxonomy ---")
for d in coll.find({"broad_cancer": "Other"},
                   {"brand_name": 1, "year": 1, "headline": 1,
                    "extracted_cancer": 1, "broad_cancer_rationale": 1}).limit(20):
    print(f"  {d.get('year')} {(d.get('brand_name') or '?')[:22]:22s} | "
          f"{(d.get('extracted_cancer') or '')[:40]:40s} | "
          f"{(d.get('broad_cancer_rationale') or '')[:80]}")

print("\n--- Low-confidence rows (up to 20) ---")
for d in coll.find({"broad_cancer_confidence": "low"},
                   {"brand_name": 1, "year": 1, "broad_cancer": 1,
                    "heme_subcancer": 1, "headline": 1}).limit(20):
    print(f"  {d.get('year')} {(d.get('brand_name') or '?')[:22]:22s} -> "
          f"{d.get('broad_cancer'):35s} heme={d.get('heme_subcancer') or '-'}")
