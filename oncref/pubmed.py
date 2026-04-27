import requests
import pandas as pd
import re
import time

# Search settings
search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
params = {
    "db": "pubmed",
    "term": "cancer clinical AND 2025[PDAT]",
    "retmax": 2000,
    "retmode": "json"
}

# company indicator keywords and exclude (academic) terms
company_keywords = ["therapeutics", "biotech", "pharma", "pharmaceuticals", "biosciences", "bio", "inc", "ltd", "corporation", "llc", "corp"]
exclude_terms = ["university", "hospital", "institute", "college", "school", "center", "centre", "department", "division", "faculty", "laboratory", "lab", "clinic", "program", "group"]

# Heuristics lists
body_parts_list = ["lung", "breast", "prostate", "colon", "liver", "pancreas", "ovary", "skin", "brain", "kidney", "bladder", "stomach", "esophagus", "thyroid", "bone", "blood", "eye", "head", "neck"]
cancer_types_list = ["carcinoma", "sarcoma", "lymphoma", "leukemia", "melanoma", "glioma", "myeloma", "adenocarcinoma", "tumor", "cancer"]
subparts_list = ["ductal", "lobular", "small cell", "non-small cell", "squamous", "clear cell", "triple negative", "her2", "er-positive", "pr-positive"]
who_list = ["patient", "patients", "mouse", "mice", "rat", "rats", "subject", "subjects", "volunteer", "volunteers", "child", "children", "adult", "adults", "man", "woman", "men", "women"]

# Fetch PMIDs
search = requests.get(search_url, params=params).json()
ids = search.get("esearchresult", {}).get("idlist", [])
print(f"Found {len(ids)} PMIDs")

rows = []
total = len(ids)
for i, pmid in enumerate(ids, start=1):
    print(f"Processing {i}/{total} PMID {pmid}")
    resp = requests.get(fetch_url, params={"db": "pubmed", "id": pmid, "retmode": "xml"})
    text = resp.text or ""

    # Extract title, abstract(s), mesh terms, NCT ID
    title_m = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", text, re.DOTALL)
    abstract_ms = re.findall(r"<AbstractText.*?>(.*?)</AbstractText>", text, re.DOTALL)
    mesh = re.findall(r"<MeshHeading>.*?<DescriptorName.*?>(.*?)</DescriptorName>.*?</MeshHeading>", text, re.DOTALL)
    nct_m = re.search(r"NCT\d{8}", text)
    nct_id = nct_m.group(0) if nct_m else ""

    title = title_m.group(1).strip() if title_m else ""
    abstract = " ".join(a.strip() for a in abstract_ms) if abstract_ms else ""
    mesh_terms = "; ".join(m.strip() for m in mesh) if mesh else ""
    search_text = " ".join([title.lower(), abstract.lower(), mesh_terms.lower()])

    body_part = next((bp for bp in body_parts_list if bp in search_text), "")
    cancer_type = next((ct for ct in cancer_types_list if ct in search_text), "")
    subpart = next((sp for sp in subparts_list if sp in search_text), "")
    who = next((w for w in who_list if w in search_text), "")

    # Extract affiliations and match companies
    affiliations = re.findall(r"<Affiliation>(.*?)</Affiliation>", text, re.DOTALL)
    matched = []
    for aff in affiliations:
        clean = re.sub(r"\d+", "", aff)
        clean = re.sub(r"\(.*?\)", "", clean).strip()
        low = clean.lower()
        if any(k in low for k in company_keywords) and not any(x in low for x in exclude_terms):
            # trim location/after-comma
            comp = re.sub(r",.*", "", clean).strip()
            if comp:
                matched.append(comp)

    # For each matched company, emit a row linking the company to this trial
    for comp in sorted(set(matched)):
        rows.append({
            "PMID": pmid,
            "NCT_ID": nct_id,
            "Company": comp,
            "AffiliationRaw": "; ".join(affiliations),
            "Who": who,
            "BodyPart": body_part,
            "CancerType": cancer_type,
            "Subpart": subpart,
            "Title": title,
            "MeshTerms": mesh_terms
        })

    # polite pause to avoid hammering the server (adjust or remove if you like)
    time.sleep(0.1)

# Save results (one row per company-trial pair)
df = pd.DataFrame(rows)
df.to_csv("preclinical_oncology_company_trials_2025.csv", index=False)
print("Saved", len(df), "company-trial rows to preclinical_oncology_company_trials_2025.csv")