"""Extract line_of_therapy from FDA press release descriptions using OpenAI.

Usage:
  python3 extract_lot.py --sample 5      # test on 5 docs (no DB writes)
  python3 extract_lot.py --all           # process all docs that lack line_of_therapy
  python3 extract_lot.py --all --force   # re-process every doc
"""
import argparse
import json
import os
import sys
import time
import certifi
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are an oncology-specialist data extractor. Given an FDA oncology press release, classify the LINE OF THERAPY conveyed by the indication.

Return STRICT JSON with these fields:
- line_of_therapy: one of:
    "1L"          first-line / treatment-naive / previously untreated / newly diagnosed
    "2L"          second-line / after exactly one prior systemic therapy
    "2L+"         second-line or later (e.g. "after at least one prior therapy")
    "3L+"         third-line or later (e.g. "after at least two prior therapies", "previously treated with X and Y")
    "Adjuvant"    post-surgery adjuvant treatment
    "Neoadjuvant" pre-surgery neoadjuvant treatment
    "Maintenance" maintenance therapy after initial response
    "Refractory/Relapsed"  relapsed and/or refractory disease without explicit line count
    "Any line"    explicitly approved across lines / no line restriction
    "Unspecified" line of therapy is not stated or cannot be determined
- line_of_therapy_detail: a short verbatim quote (<=200 chars) from the text that justifies the classification, or "" if Unspecified
- confidence: "high" | "medium" | "low"

Rules:
- Base the answer ONLY on the supplied text.
- If the indication explicitly says "in combination with X for previously untreated...", that is 1L.
- "Who have received at least one prior therapy" = 2L+.
- "Who have received at least two prior therapies" = 3L+.
- "Adjuvant treatment" => Adjuvant. "Neoadjuvant" => Neoadjuvant. Both adjuvant and neoadjuvant => use "Adjuvant" and note in detail.
- "Refractory" or "relapsed" without prior-line count => Refractory/Relapsed.
- If multiple indications cover different lines, pick the broadest applicable category and explain in detail.
- Output JSON only, no prose."""


def build_user_prompt(doc: dict) -> str:
    parts = []
    for field in ("headline", "indication", "previous_therapy", "description"):
        val = doc.get(field)
        if isinstance(val, str) and val.strip():
            parts.append(f"## {field}\n{val.strip()}")
    return "\n\n".join(parts)


def classify(client: OpenAI, doc: dict) -> dict:
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(doc)},
        ],
    )
    return json.loads(resp.choices[0].message.content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="dry-run on N docs, no DB writes")
    ap.add_argument("--all", action="store_true", help="process all unprocessed docs")
    ap.add_argument("--force", action="store_true", help="re-process even if line_of_therapy exists")
    ap.add_argument("--limit", type=int, default=0, help="cap number of docs processed")
    ap.add_argument("--workers", type=int, default=8, help="parallel OpenAI requests")
    args = ap.parse_args()

    if not args.sample and not args.all:
        ap.error("Pass --sample N or --all")

    mongo = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())
    coll = mongo[os.environ["MONGODB_DB"]][os.environ["MONGODB_COLLECTION"]]
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    query = {} if args.force else {"line_of_therapy": {"$exists": False}}
    projection = {"description": 1, "indication": 1, "previous_therapy": 1, "headline": 1,
                  "brand_name": 1, "year": 1}

    cursor = coll.find(query, projection)
    if args.sample:
        cursor = cursor.limit(args.sample)
    elif args.limit:
        cursor = cursor.limit(args.limit)

    docs = list(cursor)
    total = len(docs)
    print(f"Processing {total} docs (sample={bool(args.sample)}, force={args.force}, workers={args.workers})")

    ok = err = 0
    started = time.time()

    def work(doc):
        try:
            return doc, classify(oai, doc), None
        except Exception as e:
            return doc, None, e

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, d) for d in docs]
        for i, fut in enumerate(as_completed(futures), 1):
            doc, result, exc = fut.result()
            if exc is not None:
                err += 1
                print(f"[{i}/{total}] ERROR {doc.get('_id')}: {exc}")
                continue
            lot = result.get("line_of_therapy")
            detail = result.get("line_of_therapy_detail", "")
            conf = result.get("confidence", "")
            print(f"[{i}/{total}] {doc.get('brand_name','?')} ({doc.get('year','?')}) -> "
                  f"{lot} ({conf}) :: {detail[:120]}")
            if not args.sample:
                try:
                    coll.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {
                            "line_of_therapy": lot,
                            "line_of_therapy_detail": detail,
                            "line_of_therapy_confidence": conf,
                            "line_of_therapy_model": MODEL,
                        }},
                    )
                except PyMongoError as e:
                    err += 1
                    print(f"  mongo update failed: {e}")
                    continue
            ok += 1

    elapsed = time.time() - started
    print(f"\nDone. ok={ok} err={err} elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
