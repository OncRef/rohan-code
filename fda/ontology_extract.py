"""Regex-ontology extraction: line_of_therapy.json + stage.json -> canonical columns in Mongo.

For every FDA doc we scan headline + indication + previous_therapy + description and
emit canonical matches. Stage patterns are applied most-specific-first; later
overlapping matches are dropped so 'Stage IVB' is recorded once as `stage_IVB`,
not also as `stage_IV`.

Fields written per doc:
  lot_canonical          [str] unique canonical LOT terms found (e.g. ["first_line_therapy"])
  lot_categories         [str] unique LOT categories found
  lot_matches            [{canonical_name, category, matched_text, source_field}]
  stage_canonical        [str] unique canonical stage/status/grade/etc. terms
  stage_categories       [str] unique stage categories found
  stage_matches          [{canonical_name, category, matched_text, source_field}]
  ontology_extracted_at  float (epoch)

Usage:
  python3 ontology_extract.py --sample 10
  python3 ontology_extract.py --all
  python3 ontology_extract.py --all --force
"""
import argparse
import json
import os
import re
import sys
import time
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
LOT_PATH = os.path.join(HERE, "line_of_therapy.json")
STAGE_PATH = os.path.join(HERE, "stage.json")

SOURCE_FIELDS = ("headline", "indication", "previous_therapy", "description")


def load_ontology(path):
    with open(path) as f:
        data = json.load(f)
    terms = []
    for t in data["terms"]:
        terms.append({
            "canonical_name": t["canonical_name"],
            "category": t["category"],
            "pattern": re.compile(t["regex"]),
        })
    return terms


def extract(text: str, terms: list, source_field: str) -> list:
    """Apply regex terms in declared order; drop later matches that overlap earlier ones.
    The ontology files are ordered most-specific-first."""
    claimed = []  # (start, end) spans already taken by a more-specific term
    out = []
    for term in terms:
        for m in term["pattern"].finditer(text):
            s, e = m.start(), m.end()
            if any(cs < e and s < ce for cs, ce in claimed):
                continue
            claimed.append((s, e))
            out.append({
                "canonical_name": term["canonical_name"],
                "category": term["category"],
                "matched_text": m.group(0),
                "source_field": source_field,
            })
    return out


def extract_doc(doc, terms):
    all_matches = []
    for fld in SOURCE_FIELDS:
        v = doc.get(fld)
        if isinstance(v, str) and v.strip():
            all_matches.extend(extract(v, terms, fld))
    return all_matches


def dedupe_canonical(matches):
    seen = []
    for m in matches:
        if m["canonical_name"] not in seen:
            seen.append(m["canonical_name"])
    return seen


def dedupe_categories(matches):
    seen = []
    for m in matches:
        if m["category"] not in seen:
            seen.append(m["category"])
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if not args.sample and not args.all:
        ap.error("pass --sample N or --all")

    lot_terms = load_ontology(LOT_PATH)
    stage_terms = load_ontology(STAGE_PATH)
    print(f"Loaded {len(lot_terms)} LOT terms, {len(stage_terms)} stage terms")

    coll = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())[
        os.environ["MONGODB_DB"]
    ][os.environ["MONGODB_COLLECTION"]]

    query = {} if args.force else {"ontology_extracted_at": {"$exists": False}}
    projection = {f: 1 for f in SOURCE_FIELDS}
    projection.update({"brand_name": 1, "year": 1})

    cursor = coll.find(query, projection)
    if args.sample:
        cursor = cursor.limit(args.sample)
    elif args.limit:
        cursor = cursor.limit(args.limit)

    docs = list(cursor)
    total = len(docs)
    print(f"Processing {total} docs (sample={bool(args.sample)}, force={args.force})")

    ok = err = 0
    started = time.time()
    for i, doc in enumerate(docs, 1):
        lot_matches = extract_doc(doc, lot_terms)
        stage_matches = extract_doc(doc, stage_terms)

        lot_canon = dedupe_canonical(lot_matches)
        stage_canon = dedupe_canonical(stage_matches)

        if args.sample:
            print(f"\n[{i}/{total}] {doc.get('brand_name','?')} ({doc.get('year','?')})")
            print(f"  LOT canonical : {lot_canon or '-'}")
            for m in lot_matches[:6]:
                print(f"     - {m['canonical_name']:35s} <- {m['source_field']}: '{m['matched_text']}'")
            print(f"  Stage canonical: {stage_canon[:10] or '-'}")
            for m in stage_matches[:8]:
                print(f"     - {m['canonical_name']:25s} <- {m['source_field']}: '{m['matched_text']}'")

        if not args.sample:
            update = {
                "lot_canonical": lot_canon,
                "lot_categories": dedupe_categories(lot_matches),
                "lot_matches": lot_matches,
                "stage_canonical": stage_canon,
                "stage_categories": dedupe_categories(stage_matches),
                "stage_matches": stage_matches,
                "ontology_extracted_at": time.time(),
            }
            try:
                coll.update_one({"_id": doc["_id"]}, {"$set": update})
            except PyMongoError as e:
                err += 1
                print(f"  mongo update failed: {e}")
                continue
        ok += 1

    elapsed = time.time() - started
    print(f"\nDone. ok={ok} err={err} elapsed={elapsed:.2f}s")


if __name__ == "__main__":
    sys.exit(main())
