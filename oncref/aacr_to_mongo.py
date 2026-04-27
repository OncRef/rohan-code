"""
Parse the AACR 2025 Proceedings PDF and dump every abstract as a document
into MongoDB Conferences.AACR_2025.

Schema (fields omitted when empty so Mongo docs don't carry blank columns):

    _id                 string  incremental index
    abstractNumber      string  e.g. "1", "LB123"
    title               string
    date                string  e.g. "Sunday, April 27, 2025"
    track               string  e.g. "TUMOR BIOLOGY: Cancer Stem Cells"
    sessionType         string  e.g. "Poster Session"
    authors             list    ["Juan Carlos Quintero-Gallegos", ...]
    organizations       list    ["Unidad de ...", "Departamento de Biologia, ..."]
    abstract            string  full body text (always set when body exists)
    background          string  only if explicitly labelled
    methods             string  only if explicitly labelled
    results             string  only if explicitly labelled
    conclusions         string  only if explicitly labelled
    clinicalTrialInformation string  first NCT id in body (if any)
    page                int     start page in PDF
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import certifi
import pdfplumber
from pymongo import MongoClient
from tqdm import tqdm

# --- Paths / Mongo -----------------------------------------------------------

ROOT = Path("/Users/rohansharma/Desktop/oncref")
PDF_PATH = ROOT / "AACR2025_Proceedings_050725.pdf"
PAGES_CACHE = ROOT / "aacr2025_pages.jsonl"  # streaming: one page per line
JSON_OUT = ROOT / "aacr2025_abstracts.json"
PROGRESS_LOG = ROOT / "aacr2025_progress.log"

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = "Conferences"
COLL_NAME = "AACR_2025"

# --- Regexes -----------------------------------------------------------------

ABSTRACT_RE = re.compile(r"^#(LB?\d+|\d+)\s+(.*)$")

DATE_RE = re.compile(
    r"^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),\s+"
    r"[A-Z][a-z]+\s+\d{1,2},\s+\d{4}$"
)

SESSION_RE = re.compile(
    r"^(Poster Session|Oral Abstract Session|Oral Presentation|"
    r"Plenary Session|Opening Plenary|Closing Plenary|"
    r"Minisymposium|Major Symposium|"
    r"Educational Session|Methods Workshop|"
    r"Late[- ]Breaking[^,]*|Late[- ]Breaking Research[^,]*|"
    r"Clinical Trial(?:s)? Plenary(?:\s+Session)?|"
    r"Forum|Spotlight Session|Proffered Abstract Session|"
    r"Regular Abstract(?:s)? Submission|Invited Presentation|"
    r"Advances in[^,]*)$",
    re.IGNORECASE,
)

# Uppercase-prefix "track" header (AACR proceedings section banner)
TRACK_RE = re.compile(r"^[A-Z][A-Z0-9 /&+,.'\-]{5,}(?::\s*[^\n]{0,200})?$")

# Labeled sections inside an abstract body
SECTION_RE = re.compile(
    r"(?im)^\s*("
    r"Background|Introduction|Purpose|Objective[s]?|"
    r"Method[s]?|Materials? and Methods?|Experimental Design|"
    r"Result[s]?|Findings|"
    r"Conclusion[s]?|Discussion|Summary|Implications"
    r")\s*:\s*"
)

SECTION_KEY = {
    "background": "background",
    "introduction": "background",
    "purpose": "background",
    "objective": "background",
    "objectives": "background",
    "method": "methods",
    "methods": "methods",
    "materials and methods": "methods",
    "material and methods": "methods",
    "experimental design": "methods",
    "result": "results",
    "results": "results",
    "findings": "results",
    "conclusion": "conclusions",
    "conclusions": "conclusions",
    "discussion": "conclusions",
    "summary": "conclusions",
    "implications": "conclusions",
}

# Structural affiliation keywords (kept deliberately narrow to avoid
# matching body-text words like "medicine", "research", "cancer").
AFFIL_RE = re.compile(
    r"\b("
    r"Universit(?:y|ies|[aeéè])|Universidad(?:e)?|Università|Universidade|"
    r"Institut[eo]?|Instituto|"
    r"Hospital(?:s|es|is)?|Klinikum|Krankenhaus|"
    r"School of [A-Z]|College|Facult(?:y|[eé]|ad|ades)|Faculdade|"
    r"Cancer Center|Cancer Institute|Comprehensive Cancer|"
    r"Medical Center|Medical School|School of Medicine|"
    r"Department|Departamento|Dept\.?|Division of [A-Z]|"
    r"Laboratory|Laboratoire|Laboratorio|"
    r"Inc\.?|Ltd\.?|LLC|Corp(?:oration)?|"
    r"Pharma(?:ceuticals?)?|Therapeutics|Biosciences|Biotech(?:nology)?|"
    r"Diagnostics|GmbH|S\.A\.|S\.p\.A\.|"
    r"Foundation|Academy of"
    r")\b",
    re.IGNORECASE,
)

NCT_RE = re.compile(r"\bNCT\d{6,9}\b")

# --- PDF extraction ----------------------------------------------------------


def extract_pages(pdf_path: Path, cache: Path) -> list[str]:
    """Stream page text to a JSONL cache, then read it back.

    Writing incrementally keeps memory flat and lets the caller see live
    progress by tailing the cache/log file.
    """
    if cache.exists():
        print(f"[extract] reusing cached pages at {cache}", flush=True)
        with cache.open("r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh]

    print(f"[extract] opening {pdf_path}", flush=True)
    count = 0
    with pdfplumber.open(str(pdf_path)) as pdf:
        total = len(pdf.pages)
        print(f"[extract] {total} pages total — streaming to {cache.name}", flush=True)
        t0 = time.time()
        with cache.open("w", encoding="utf-8") as fh:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                fh.write(json.dumps(text, ensure_ascii=False))
                fh.write("\n")
                count += 1
                # Release per-page cache eagerly to avoid memory balloon
                try:
                    page.flush_cache()
                except Exception:
                    pass
                if count % 50 == 0 or count == total:
                    elapsed = time.time() - t0
                    rate = count / elapsed if elapsed else 0
                    remaining = (total - count) / rate if rate else 0
                    pct = 100 * count / total
                    print(
                        f"[extract] {count}/{total} ({pct:.1f}%) "
                        f"{rate:.1f} pg/s  eta {remaining/60:.1f} min",
                        flush=True,
                    )
                    fh.flush()

    print(f"[extract] done — {count} pages to {cache}", flush=True)
    with cache.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


# --- Body parsing ------------------------------------------------------------


def parse_labeled_sections(body: str) -> dict:
    matches = list(SECTION_RE.finditer(body))
    if not matches:
        return {}
    out: dict = {}
    for i, m in enumerate(matches):
        label = m.group(1).strip().lower()
        key = SECTION_KEY.get(label)
        if not key:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end].strip()
        if not chunk:
            continue
        if key in out:
            out[key] = (out[key] + " " + chunk).strip()
        else:
            out[key] = chunk
    return out


# --- Abstract block parser ---------------------------------------------------


def parse_abstract(
    abstract_num: str,
    title_start: str,
    body_lines: list[str],
    ctx: dict,
    start_page: int,
) -> Optional[dict]:
    """Parse one abstract from its accumulated lines."""
    all_lines = [ln for ln in ([title_start] + body_lines) if ln.strip()]
    if not all_lines:
        return None

    # --- Title: first 1..3 lines until one ends with a period (or fallback) ---
    title_lines: list[str] = []
    idx = 0
    while idx < len(all_lines) and idx < 3:
        ln = all_lines[idx].strip()
        title_lines.append(ln)
        idx += 1
        if ln.endswith("."):
            break
    title = " ".join(title_lines).strip()

    remaining = [ln.strip() for ln in all_lines[idx:]]

    doc: dict = {
        "abstractNumber": abstract_num,
        "title": title,
        "page": start_page,
    }
    if ctx.get("date"):
        doc["date"] = ctx["date"]
    if ctx.get("track"):
        doc["track"] = ctx["track"]
    if ctx.get("sessionType"):
        doc["sessionType"] = ctx["sessionType"]

    if not remaining:
        return doc

    # --- Authors: first line; possibly extended if it ends with a comma ------
    authors_raw = remaining[0]
    j = 1
    while (
        j < len(remaining)
        and j < 4
        and authors_raw.rstrip().endswith(",")
        and not re.match(r"^\d", remaining[j])
        and not AFFIL_RE.search(remaining[j])
        and not SECTION_RE.match(remaining[j])
    ):
        authors_raw = authors_raw + " " + remaining[j]
        j += 1

    max_org = 0
    for m in re.finditer(r"\d+", authors_raw):
        max_org = max(max_org, int(m.group()))

    authors = []
    for part in re.split(r",\s*", authors_raw):
        name = re.sub(r"[\d\*†‡§¶#]+$", "", part).strip()
        name = name.strip(" ,;")
        if name:
            authors.append(name)
    if authors:
        doc["authors"] = authors

    remaining2 = remaining[j:]
    if not remaining2:
        return doc

    # --- Organizations and body split ---------------------------------------
    org_lines: list[str] = []
    body_start: Optional[int] = None

    if max_org == 0:
        # Single organization: exactly one line, then body.
        org_lines = [remaining2[0]]
        body_start = 1
    else:
        for k, ln in enumerate(remaining2):
            if SECTION_RE.match(ln):
                body_start = k
                break
            if k == 0:
                org_lines.append(ln)
                continue
            # Continuation from word-wrapped previous affiliation line
            if ln and ln[0].islower():
                org_lines.append(ln)
                continue
            if org_lines and org_lines[-1].rstrip()[-1:] in {",", "-"}:
                org_lines.append(ln)
                continue
            # Start of a new numbered organization
            if re.match(r"^\d", ln):
                org_lines.append(ln)
                continue
            # Still an affiliation (contains structural keyword)
            if AFFIL_RE.search(ln):
                org_lines.append(ln)
                continue
            # Looks like a body sentence: starts with an uppercase letter,
            # not an affiliation, long enough to be a sentence fragment.
            if re.match(r"^[A-Z(\"']", ln) and len(ln) > 30:
                body_start = k
                break
            # Default: keep as org continuation
            org_lines.append(ln)
        if body_start is None:
            body_start = len(remaining2)

    body_lines_only = remaining2[body_start:] if body_start is not None else []

    # --- Build organizations list ------------------------------------------
    organizations: list[str] = []
    org_text = " ".join(org_lines).strip()
    if org_text:
        if re.search(r"\d+[A-Z]", org_text):
            # Split on digit prefixes (1Org,2Org,3Org,...)
            parts = re.split(r"(?:(?<=^)|(?<=[\s,]))(?=\d+[A-Z])", org_text)
            for p in parts:
                p = p.strip(" ,;")
                if not p:
                    continue
                p = re.sub(r"^\d+", "", p).strip(" ,;")
                if p:
                    organizations.append(p)
        else:
            organizations = [org_text.strip(" ,;")]
    if organizations:
        doc["organizations"] = organizations

    # --- Body / sections ---------------------------------------------------
    body_text = "\n".join(body_lines_only).strip()
    if body_text:
        doc["abstract"] = body_text
        sections = parse_labeled_sections(body_text)
        for k, v in sections.items():
            if v:
                doc[k] = v
        nct = NCT_RE.search(body_text)
        if nct:
            doc["clinicalTrialInformation"] = nct.group(0)

    return doc


# --- Top-level walker --------------------------------------------------------


def walk_pages(pages: list[str]) -> list[dict]:
    ctx = {"date": "", "track": "", "sessionType": ""}
    abstracts: list[dict] = []

    current_num: Optional[str] = None
    current_title_start = ""
    current_ctx: dict = {}
    current_lines: list[str] = []
    current_page: int = 0

    def flush() -> None:
        nonlocal current_num, current_title_start, current_ctx, current_lines, current_page
        if current_num is None:
            return
        doc = parse_abstract(
            current_num,
            current_title_start,
            current_lines,
            current_ctx,
            current_page,
        )
        if doc:
            abstracts.append(doc)
        current_num = None
        current_title_start = ""
        current_ctx = {}
        current_lines = []
        current_page = 0

    for pg_idx, page_text in enumerate(tqdm(pages, desc="parse")):
        raw_lines = page_text.splitlines()

        # Scan the top of the page for context headers.
        ptr = 0
        while ptr < min(8, len(raw_lines)):
            ln = raw_lines[ptr].strip()
            if not ln:
                ptr += 1
                continue
            if DATE_RE.match(ln):
                ctx["date"] = ln
                ptr += 1
                continue
            if SESSION_RE.match(ln):
                ctx["sessionType"] = ln
                ptr += 1
                continue
            # Track header: uppercase-prefix line. Accept only if prefix >= 6 chars.
            m = re.match(r"^[A-Z][A-Z0-9 /&+,.'\-]{5,}", ln)
            if m and not ln.startswith("#") and len(m.group()) >= 6:
                # Could be multi-line track: take this line plus next if it
                # looks like a subcategory (title-case)
                track_line = ln
                look = ptr + 1
                if look < len(raw_lines):
                    nxt = raw_lines[look].strip()
                    if nxt and not DATE_RE.match(nxt) and not SESSION_RE.match(nxt) \
                            and not ABSTRACT_RE.match(nxt) and len(nxt) < 120 \
                            and re.match(r"^[A-Z]", nxt) \
                            and not nxt.endswith(".") \
                            and not AFFIL_RE.search(nxt):
                        track_line = f"{track_line}: {nxt}" if ":" not in track_line else f"{track_line} {nxt}"
                        ptr = look + 1
                    else:
                        ptr += 1
                else:
                    ptr += 1
                ctx["track"] = track_line
                continue
            break

        for ln in raw_lines[ptr:]:
            stripped = ln.strip()
            m = ABSTRACT_RE.match(stripped)
            if m:
                flush()
                current_num = m.group(1)
                current_title_start = m.group(2).strip()
                current_ctx = dict(ctx)
                current_lines = []
                current_page = pg_idx + 1
            else:
                if current_num is not None:
                    current_lines.append(ln)

    flush()
    return abstracts


# --- Mongo load --------------------------------------------------------------


def load_into_mongo(docs: list[dict]) -> None:
    print(f"[mongo] connecting → {DB_NAME}.{COLL_NAME}")
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    coll = client[DB_NAME][COLL_NAME]
    before = coll.estimated_document_count()
    print(f"[mongo] existing docs in {COLL_NAME}: {before}")
    if before:
        print(f"[mongo] dropping existing {COLL_NAME} for a clean reload")
        coll.drop()
    batch = 1000
    for start in tqdm(range(0, len(docs), batch), desc="mongo"):
        coll.insert_many(docs[start : start + batch], ordered=False)
    print(f"[mongo] final docs: {coll.estimated_document_count()}")


# --- main --------------------------------------------------------------------


def main() -> None:
    t0 = time.time()
    pages = extract_pages(PDF_PATH, PAGES_CACHE)
    print(f"[main] {len(pages):,} pages loaded")
    abstracts = walk_pages(pages)
    print(f"[main] parsed {len(abstracts):,} abstracts")

    for i, d in enumerate(abstracts):
        d["_id"] = str(i)

    JSON_OUT.write_text(json.dumps(abstracts, ensure_ascii=False), encoding="utf-8")
    print(f"[main] wrote JSON cache → {JSON_OUT}")

    if "--no-mongo" in sys.argv:
        print("[main] skipping Mongo (--no-mongo)")
    else:
        load_into_mongo(abstracts)

    print(f"[main] elapsed {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
