"""
ESMO Congress 2025 programme extractor.

Reads the ESMO 2025 final programme PDF and extracts:
  - All sessions (date, time, type, title, location, chairs)
  - Industry Satellite Symposia with the sponsoring company parsed out
  - A clean unique list of industry sponsors

Output: esmo_2025_programme.xlsx with three sheets.

Mirrors the shape of aacr.py but tuned to ESMO's structured programme
(sessions, not author affiliations).
"""

import re
import pdfplumber
import pandas as pd
from tqdm import tqdm

PDF_PATH = "final_programme_esmo2025.pdf"
OUT_XLSX = "esmo_2025_programme.xlsx"
OUT_COMPANIES_XLSX = "esmo_2025_companies_clean.xlsx"
OUT_COMPANIES_CSV = "esmo_2025_companies_clean.csv"

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
SESSION_HEADER_RE = re.compile(
    r"^(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s+(.+)$"
)
TITLE_RE = re.compile(r"^Title:\s*(.+)$")
CHAIR_RE = re.compile(r"^Chair\(s\):\s*(.+)$")
TIME_PREFIX_RE = re.compile(r"^\d{2}:\d{2}\s*-\s*\d{2}:\d{2}")
# Trailing hall fragment at end of a wrapped title line: "6.2", "7.1c", "23"
HALL_TRAIL_RE = re.compile(r"\s+(\d{1,2}(?:\.\d{1,2}[a-z]?)?)\s*$")

# Known ESMO 2025 session types (longest first for greedy match)
KNOWN_TYPES = sorted([
    "Industry Satellite Symposium",
    "EONS Industry Satellite Symposium",
    "Proffered Paper session",
    "Mini Oral session",
    "Educational session",
    "Special symposium",
    "Special session",
    "Multidisciplinary session",
    "Challenge your Expert",
    "Young Oncologists session",
    "Patient Advocacy session",
    "EONS session",
    "Keynote lecture",
    "Opening session",
    "Scientific Congress highlights",
], key=len, reverse=True)

# Drop noisy header/footer text
NOISE_PATTERNS = [
    re.compile(r"^Last update:"),
    re.compile(r"^Programme$"),
    re.compile(r"^\d{1,4}$"),  # bare page numbers
]


def is_noise(line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    return any(p.search(line) for p in NOISE_PATTERNS)


def parse_sessions(pdf_path: str):
    """Walk the PDF line by line and emit one record per session block."""
    sessions = []
    current_date = None
    current = None  # in-progress session dict

    def flush():
        nonlocal current
        if current and current.get("title"):
            sessions.append(current)
        current = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in tqdm(pdf.pages, desc="Pages"):
            text = page.extract_text() or ""
            for raw in text.split("\n"):
                line = raw.strip()
                if is_noise(line):
                    continue

                # Date marker
                if DATE_RE.match(line):
                    flush()
                    current_date = line
                    continue

                # Session header: "HH:MM - HH:MM ..."
                m = SESSION_HEADER_RE.match(line)
                if m:
                    flush()
                    start, end, rest = m.group(1), m.group(2), m.group(3)
                    # Strip optional "Type:" prefix
                    rest_clean = re.sub(r"^Type:\s*", "", rest).strip()
                    sess_type = ""
                    location = rest_clean
                    for t in KNOWN_TYPES:
                        if t in rest_clean:
                            sess_type = t
                            location = rest_clean.replace(t, "", 1).strip()
                            break
                    current = {
                        "date": current_date,
                        "start": start,
                        "end": end,
                        "type": sess_type,
                        "title": "",
                        "_title_open": False,
                        "location": location,
                        "chairs": "",
                    }
                    continue

                if current is None:
                    continue

                # Title (may wrap to next lines until Chair(s) or next header)
                tm = TITLE_RE.match(line)
                if tm:
                    title_text = tm.group(1).strip()
                    # If the location field ended dangling ("- Hall" with no
                    # number), the wrapped hall fragment landed in the title.
                    # Pull it back into location.
                    loc_end = current["location"].rstrip()
                    if loc_end.endswith("Hall") or loc_end.endswith("Hub"):
                        frag = HALL_TRAIL_RE.search(title_text)
                        if frag:
                            current["location"] = (
                                loc_end + " " + frag.group(1)
                            ).strip()
                            title_text = HALL_TRAIL_RE.sub("", title_text).strip()
                    current["title"] = title_text
                    current["_title_open"] = True
                    continue

                cm = CHAIR_RE.match(line)
                if cm:
                    current["chairs"] = cm.group(1).strip()
                    current["_title_open"] = False
                    continue

                # Continuation of a wrapped Title line
                if current.get("_title_open"):
                    # Stop wrapping if we hit something that looks like a talk
                    # (e.g., starts with a time, an LBA/MO id, or speaker initial)
                    if re.match(r"^\d{2}:\d{2}\s*-\s*\d{2}:\d{2}", line):
                        current["_title_open"] = False
                    elif re.match(r"^(LBA|[0-9]{1,4}(O|MO|P))\b", line):
                        current["_title_open"] = False
                    else:
                        current["title"] = (current["title"] + " " + line).strip()

        flush()

    # Strip helper key
    for s in sessions:
        s.pop("_title_open", None)
    return sessions


# Companies that appear as Industry Satellite Symposium sponsors.
# These are matched at the start of the Title (case-insensitive). Order matters
# for longest-prefix matching.
KNOWN_SPONSORS = [
    "AstraZeneca",
    "Bristol Myers Squibb",
    "Boehringer Ingelheim International GmbH",
    "Boehringer Ingelheim",
    "Johnson and Johnson Innovative Medicine",
    "Johnson & Johnson",
    "Daiichi Sankyo - AstraZeneca",
    "Daiichi Sankyo",
    "F. Hoffmann-La Roche",
    "Eli Lilly and Company",
    "Gilead and Kite Oncology",
    "Pfizer Oncology",
    "Pierre Fabre Laboratories",
    "Merck Healthcare KGaA",
    "Menarini Stemline",
    "Medscape Global Oncology",
    "Nestlé Health Science",
    "Replimune Inc",
    "Regeneron Pharmaceuticals",
    "Regeneron Pharmaceutials",
    "Jazz Pharmaceuticals",
    "AbbVie Inc.",
    "AbbVie",
    "Genmab",
    "Novartis",
    "Astellas",
    "Eisai",
    "GSK",
    "MSD",
    "BMS",
    "Servier",
    "Pfizer",
    "Sanofi",
    "Takeda",
    "Bayer",
    "Amgen",
    "BeOne",
    "PharmaMar",
    "IPSEN",
    "Incyte",
    "Paxman",
    "J&J",
]


# Map raw sponsor strings to a canonical company name
SPONSOR_CANONICAL = {
    "BMS": "Bristol Myers Squibb",
    "Bristol Myers Squibb": "Bristol Myers Squibb",
    "AbbVie": "AbbVie",
    "AbbVie Inc.": "AbbVie",
    "Eli Lilly": "Eli Lilly",
    "Eli Lilly and Company": "Eli Lilly",
    "Pfizer": "Pfizer",
    "Pfizer Oncology": "Pfizer",
    "Johnson & Johnson": "Johnson & Johnson",
    "Johnson and Johnson Innovative Medicine": "Johnson & Johnson",
    "J&J": "Johnson & Johnson",
    "Daiichi Sankyo": "Daiichi Sankyo",
    "Daiichi Sankyo - AstraZeneca": "Daiichi Sankyo / AstraZeneca",
    "Boehringer Ingelheim": "Boehringer Ingelheim",
    "Boehringer Ingelheim International GmbH": "Boehringer Ingelheim",
    "Regeneron Pharmaceuticals": "Regeneron",
    "Regeneron Pharmaceutials": "Regeneron",  # PDF typo
    "F. Hoffmann-La Roche": "Roche",
    "Gilead and Kite Oncology": "Gilead / Kite",
}


def canonicalize(name):
    if name is None:
        return None
    return SPONSOR_CANONICAL.get(name, name)


def extract_sponsor(title: str):
    """Return (sponsor, remainder) if the title starts with a known sponsor."""
    if not title:
        return None, title
    low = title.lower()
    for name in KNOWN_SPONSORS:
        if low.startswith(name.lower()):
            rest = title[len(name):].lstrip(" -–:")
            return name, rest
    # Generic fallback: split on " - " and treat the prefix as sponsor only if
    # it looks short and capitalized (a heuristic for unknown vendors).
    if " - " in title:
        prefix, rest = title.split(" - ", 1)
        if 2 <= len(prefix) <= 60 and prefix[0].isupper():
            return prefix.strip(), rest.strip()
    return None, title


def main():
    sessions = parse_sessions(PDF_PATH)
    print(f"Parsed {len(sessions)} sessions")

    df_all = pd.DataFrame(sessions, columns=[
        "date", "start", "end", "type", "title", "location", "chairs",
    ])

    # Industry symposia subset
    industry_mask = df_all["type"].str.contains(
        "Industry Satellite Symposium", case=False, na=False
    )
    df_industry = df_all[industry_mask].copy()
    parsed = df_industry["title"].apply(extract_sponsor)
    df_industry["sponsor"] = parsed.apply(lambda t: canonicalize(t[0]))
    df_industry["symposium_title"] = parsed.apply(lambda t: t[1])
    df_industry = df_industry[[
        "date", "start", "end", "sponsor", "symposium_title",
        "location", "chairs",
    ]]

    # Unique sponsor list
    sponsors = (
        df_industry["sponsor"]
        .dropna()
        .astype(str)
        .str.strip()
    )
    sponsor_counts = (
        sponsors.value_counts()
        .rename_axis("sponsor")
        .reset_index(name="symposium_count")
    )

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as xw:
        df_all.to_excel(xw, sheet_name="all_sessions", index=False)
        df_industry.to_excel(xw, sheet_name="industry_symposia", index=False)
        sponsor_counts.to_excel(xw, sheet_name="sponsors_unique", index=False)

    # Clean single-column company list, AACR-style
    df_companies = pd.DataFrame(
        sorted(sponsors.unique(), key=str.lower),
        columns=["Company"],
    )
    df_companies.to_excel(OUT_COMPANIES_XLSX, index=False)
    df_companies.to_csv(OUT_COMPANIES_CSV, index=False)

    print(f"Wrote {OUT_XLSX}")
    print(f"  all_sessions      : {len(df_all)} rows")
    print(f"  industry_symposia : {len(df_industry)} rows")
    print(f"  sponsors_unique   : {len(sponsor_counts)} rows")
    print(f"Wrote {OUT_COMPANIES_XLSX} ({len(df_companies)} companies)")
    print(f"Wrote {OUT_COMPANIES_CSV}")


if __name__ == "__main__":
    main()
