"""Remap broad_cancer (and assign heme_subcancer) using the canonical taxonomy
from the conference CSV (Master_Conference_List.csv).

The original value is preserved in `broad_cancer_legacy` on the first run.

Usage:
  python3 remap_broad_cancer.py --sample 10
  python3 remap_broad_cancer.py --all
  python3 remap_broad_cancer.py --all --force        # re-run even if already remapped
"""
import argparse
import csv
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

MODEL = "gpt-4o"
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "Master_Conference_List.csv")


def load_taxonomy(path):
    broad = []
    heme = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = (row.get("Cancer Type FINAL") or "").strip()
            if v and v != "All" and v not in broad:
                broad.append(v)
            h = (row.get("Heme subcancers") or "").strip()
            if h and h not in heme:
                heme.append(h)
    return broad, heme


BROAD, HEME = load_taxonomy(CSV_PATH)

SYSTEM_PROMPT = f"""You are an oncology data taxonomist. Given an FDA oncology press release, classify it into the canonical taxonomy below.

CANONICAL BROAD CANCER CATEGORIES (the ONLY allowed values for `broad_cancer`):
{chr(10).join(f"- {b}" for b in BROAD)}
- Other (use ONLY if nothing above fits — e.g. pancreatic cancer, supportive-care drugs, vaccines, broad label updates)

CANONICAL HEME SUBCANCERS (only used when broad_cancer == "Hematological Malignancies"):
{chr(10).join(f"- {h}" for h in HEME)}
- (empty string if heme but doesn't match one of the above — e.g. AML, ALL, CML, Hodgkin lymphoma, T-cell lymphoma, etc.)

CRITICAL DISTINCTIONS — do NOT confuse these:
- Chronic MYELOID leukemia (CML) is NOT Chronic LYMPHOCYTIC leukemia (CLL). CML -> heme_subcancer = "" (CML is not in the canonical heme list).
- Acute LYMPHOBLASTIC leukemia (ALL) is NOT Acute MYELOID leukemia (AML). ALL -> heme_subcancer = "" (ALL is not in the canonical heme list).
- Cutaneous T-cell lymphoma (CTCL, mycosis fungoides, Sezary) is HEMATOLOGICAL — broad_cancer = "Hematological Malignancies", heme_subcancer = "" (T-cell lymphoma is not in the canonical heme list). It is NOT "Skin Cancers".
- Hodgkin lymphoma -> heme_subcancer = "" (not in canonical list).
- Anaplastic large cell, peripheral T-cell, NK-cell lymphomas -> heme_subcancer = "" (T-cell, not B-cell).
- Dermatofibrosarcoma protuberans (DFSP) is a SOFT TISSUE SARCOMA -> "Soft Tissue Cancers (including Heart)", not heme.
- For multi-indication approvals where indications span DIFFERENT broad categories or DIFFERENT heme subs, use heme_subcancer = "" and pick the most prominent broad_cancer; explain in rationale.

MAPPING RULES:
- Any leukemia, lymphoma, myeloma, MDS, MPN, mastocytosis (other than CTCL=skin? NO — CTCL is heme) -> broad_cancer = "Hematological Malignancies", then heme_subcancer ONLY if exact match:
  * Multiple myeloma, plasma cell myeloma, plasmacytoma -> "Multiple Myeloma"
  * Polycythemia vera (PV), essential thrombocythemia (ET), primary/post-PV/post-ET myelofibrosis -> "Myeloproliferative Neoplasms"
  * Acute MYELOID leukemia (AML, AML-MRC, t-AML) -> "Acute Myeloid Leukemia"
  * Systemic mastocytosis (ASM, SM-AHN, MCL) -> "Systemic Mastocytosis"
  * Diffuse large B-cell lymphoma (DLBCL), follicular lymphoma (FL), mantle cell lymphoma (MCL), marginal zone lymphoma (MZL), Waldenstrom, Burkitt, B-NHL, primary mediastinal B-cell -> "B-Cell Lymphomas"
  * Hairy cell leukemia (HCL) -> "Hairy Cell Leukemia"
  * Myelodysplastic syndromes (MDS), MDS/MPN overlap -> "Myelodysplastic Syndromes"
  * CLL or SLL (chronic LYMPHOCYTIC leukemia / small lymphocytic lymphoma) -> "Chronic Lymphocytic Leukemia/Small Lymphocytic Lymphoma"
  * Anything else heme (AML and ALL look similar but ALL is NOT in this list; CML, Hodgkin, T-cell lymphoma, CTCL) -> heme_subcancer = ""
- Cervical, ovarian, endometrial, uterine, vulvar, vaginal, fallopian, peritoneal -> "Gynecological Cancers"
- Anal, rectal, colon, colorectal, appendiceal -> "Colorectal Cancer"
- Stomach, esophageal, esophagogastric junction (GEJ) -> "Gastric (Stomach) Cancer"
- GIST (gastrointestinal stromal tumor) -> "Soft Tissue Cancers (including Heart)" (it is a sarcoma)
- Bladder, urothelial, ureter, urethra, renal pelvis, kidney (RCC) -> "Kidney (Renal) and Urethral Cancers"
- Melanoma (cutaneous, mucosal, uveal -> uveal goes to Ocular), basal cell, cutaneous squamous cell, Merkel cell, BCC -> "Skin Cancers"
- Uveal/intraocular melanoma, retinoblastoma -> "Ocular Cancers"
- Glioma, glioblastoma (GBM), astrocytoma, medulloblastoma (adult), DIPG (adult), meningioma -> "Brain and Other Nervous System"
- Hepatocellular carcinoma (HCC), cholangiocarcinoma, gallbladder, intrahepatic/extrahepatic bile duct -> "Liver and Bile Duct Cancers"
- Pancreatic neuroendocrine tumor (pNET), GI/lung NET, pheochromocytoma, paraganglioma, adrenocortical -> "Adrenal Cancer and Neuroendocrine Tumors"
- Pancreatic adenocarcinoma (no clean fit) -> "Other"
- Soft tissue sarcoma (leiomyosarcoma, liposarcoma, synovial, rhabdo in adults), GIST, DFSP, angiosarcoma, MPNST -> "Soft Tissue Cancers (including Heart)"
- Osteosarcoma, Ewing sarcoma (adult), chondrosarcoma, giant cell tumor of bone -> "Bone and Joint Cancers"
- Pediatric ALL/AML/neuroblastoma/Wilms/medulloblastoma/rhabdo (when explicitly pediatric) -> "Pediatric Cancers"
- Hereditary cancer syndromes (Lynch, BRCA carrier, NF1, Cowden, FAP) -> "Specific Syndromes"
- Supportive care (ESAs like epoetin/darbepoetin, plerixafor, dexrazoxane, palifermin, antiemetics, chelators), HPV vaccine, oncology imaging agents, anticoagulants for cancer -> "Other"
- Pure package-insert label changes for non-cancer supportive drugs -> "Other"

Return STRICT JSON:
{{
  "broad_cancer": "<one canonical value or 'Other'>",
  "heme_subcancer": "<one canonical heme sub or ''>",
  "rationale": "<<=200 char verbatim or near-verbatim quote justifying the call>",
  "confidence": "high" | "medium" | "low"
}}
"""


def build_user_prompt(doc: dict) -> str:
    parts = []
    for field in ("headline", "extracted_cancer", "indication", "previous_therapy", "description"):
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
    ap.add_argument("--sample", type=int, default=0, help="dry run on N docs, no DB writes")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    if not args.sample and not args.all:
        ap.error("pass --sample N or --all")

    print(f"Canonical broad categories: {len(BROAD)}")
    print(f"Canonical heme subs: {len(HEME)}")

    mongo = MongoClient(os.environ["MONGODB_URI"], tlsCAFile=certifi.where())
    coll = mongo[os.environ["MONGODB_DB"]][os.environ["MONGODB_COLLECTION"]]
    oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    query = {} if args.force else {"broad_cancer_remapped_at": {"$exists": False}}
    projection = {"description": 1, "indication": 1, "previous_therapy": 1, "headline": 1,
                  "brand_name": 1, "year": 1, "extracted_cancer": 1, "broad_cancer": 1}

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

    def work(d):
        try:
            return d, classify(oai, d), None
        except Exception as e:
            return d, None, e

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, d) for d in docs]
        for i, fut in enumerate(as_completed(futures), 1):
            doc, result, exc = fut.result()
            if exc is not None:
                err += 1
                print(f"[{i}/{total}] ERROR {doc.get('_id')}: {exc}")
                continue
            new_bc = (result.get("broad_cancer") or "").strip()
            heme_sub = (result.get("heme_subcancer") or "").strip()
            rationale = result.get("rationale", "")
            conf = result.get("confidence", "")

            # Sanity-check the LLM stuck to the canonical set
            allowed_broad = set(BROAD) | {"Other"}
            allowed_heme = set(HEME) | {""}
            if new_bc not in allowed_broad:
                print(f"  [warn] non-canonical broad: {new_bc!r} -> coercing to 'Other'")
                new_bc = "Other"
            if heme_sub not in allowed_heme:
                print(f"  [warn] non-canonical heme: {heme_sub!r} -> coercing to ''")
                heme_sub = ""

            old_bc = doc.get("broad_cancer", "")
            print(f"[{i}/{total}] {doc.get('brand_name','?')[:24]:24s} ({doc.get('year','?')}) "
                  f"{old_bc:20s} -> {new_bc:35s} | heme={heme_sub or '-'} ({conf})")

            if not args.sample:
                update = {
                    "broad_cancer": new_bc,
                    "heme_subcancer": heme_sub,
                    "broad_cancer_rationale": rationale,
                    "broad_cancer_confidence": conf,
                    "broad_cancer_model": MODEL,
                    "broad_cancer_remapped_at": time.time(),
                }
                # Preserve legacy value once (don't overwrite on re-runs)
                if "broad_cancer_legacy" not in doc:
                    update["broad_cancer_legacy"] = old_bc
                try:
                    coll.update_one({"_id": doc["_id"]}, {"$set": update})
                except PyMongoError as e:
                    err += 1
                    print(f"  mongo update failed: {e}")
                    continue
            ok += 1

    elapsed = time.time() - started
    print(f"\nDone. ok={ok} err={err} elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
