import os
import ssl
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import certifi
import pandas as pd
from Bio import Entrez, Medline


# Keyword mappings for subtype classification (copied from your script)
subtype_keywords: Dict[str, List[str]] = {
    "Interim": ["interim", "updated interim"],
    "Final": [
        "final overall survival",
        "final analysis",
        "final update",
        "final progression free survival",
        "final results",
        "final result",
    ],
    "Update": ["updated analysis", "updated"],
    "Secondary": ["secondary analysis"],
    "Exploratory": ["exploratory analysis", "exploratory analyses", "additional analyses"],
    "Correlation": ["correlation between", "correlation of"],
    "Subgroup": [
        "subgroup analysis",
        "subgroup",
        "subpopulation",
        "subpopulation analysis",
        "subgroups",
        "based on",
        "subanalysis",
        "sub-analysis",
        "sub-group",
        "Child-Pugh",
        "Child Pugh",
        "serum",
        "biomarkers",
        "biomarker",
        "proteinuria",
        "urine",
        "creatinine ratio",
        "ratio",
        "DNA Liquid Biopsies",
        "dna liquid",
        "ctdna",
        "circulating tumor",
    ],
    "QOL": ["quality of life", "Health-Related Quality of Life", "quality-of-life"],
    "RWE": ["real"],
    "Cost-Effectiveness": ["cost-effectiveness"],
    "Retrospective": ["retrospective analysis", "retrospective"],
    "Post hoc": ["Prognostic Score and Benefit", "post hoc analysis", "post hoc", "prognostic score"],
    "Stratified": ["stratified analysis", "stratified"],
    "Patient-Reported Outcomes": [
        "patient-reported outcome",
        "patient-reported",
        "patient reported",
    ],
    "Systematic Review or Meta-Analysis": ["systematic review", "meta-analysis"],
    "Long-term": [
        "long-term safety and efficacy",
        "long-term",
        "long-term extension study",
    ],
    "2-year results": [
        "2-year results",
        "2 year results",
        "two year results",
        "two-year results",
        "2 year",
        "two year",
        "two-year",
    ],
    "3-year results": [
        "3-year results",
        "3 year results",
        "three year results",
        "three-year results",
        "3 year",
        "three year",
        "three-year",
    ],
    "4-year results": [
        "4-year results",
        "4 year results",
        "four year results",
        "four-year results",
        "4 year",
        "four year",
        "four-year",
    ],
    "5-year results": [
        "5-year results",
        "5 year results",
        "five year results",
        "five-year results",
        "5 year",
        "5-year",
        "five year",
        "five-year",
    ],
    "Other": [
        "Observational studies",
        "observational study",
        "Covariate-adjusted analysis",
        "Matching-Adjusted",
        "practice guideline",
    ],
    "Treatment sequencing": ["treatment sequencing", "treatment sequence"],
    "China": ["Chinese", "China"],
    "Japan": ["Japanese", "Japan"],
    "Asia": ["Asian"],
    "Safety Analysis": ["hepatic events", "viral events", "safety analysis"],
    "Characterization": ["characterization", "characterization of response"],
    "Summary": [
        "FDA Approval Summary",
        "Approval Summary",
        "Plain language summary",
        "plain language",
    ],
    "Pharmacokinetics/pharmacodynamics": ["Pharmacokinetics", "pharmacodynamics"],
    "Statistical": ["Statistical", "Covariate", "covariate-adjusted", "adjusted analysis"],
    "Case Study": ["A case of", "a case", "patient case", "case study"],
    "Predictive/Prognostic": ["predictive", "prognostic"],
}


def _configure_entrez(email: Optional[str] = None, api_key: Optional[str] = None) -> None:
    """Configure Entrez credentials.

    Email is required by NCBI; api_key is optional but recommended.
    Values can be passed explicitly or via NCBI_EMAIL / NCBI_API_KEY env vars.
    """

    resolved_email = email or os.getenv("NCBI_EMAIL")
    if not resolved_email:
        raise ValueError(
            "NCBI email is required. Pass email=... or set NCBI_EMAIL env var."
        )

    Entrez.email = resolved_email
    Entrez.api_key = api_key or os.getenv("NCBI_API_KEY")

    # Use certifi CA roots so Entrez HTTPS works reliably in local environments.
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())


def read_nct_numbers(file_path: str) -> List[str]:
    df = pd.read_csv(file_path)
    return df.iloc[:, 0].dropna().astype(str).str.strip().unique().tolist()


def search_pubmed_by_nct(nct_number: str) -> Tuple[str, str, int]:
    handle = Entrez.esearch(db="pubmed", term=nct_number, usehistory="y", retmax=1000)
    record = Entrez.read(handle)
    handle.close()
    time.sleep(0.1)
    webenv = record.get("WebEnv", "")
    query_key = record.get("QueryKey", "")
    count = int(record.get("Count", 0))
    return webenv, query_key, count


def fetch_article_details(nct_number: str, webenv: str, query_key: str, count: int) -> List[Dict[str, str]]:
    batch_size = 100
    articles: List[Dict[str, str]] = []

    for start in range(0, count, batch_size):
        handle = Entrez.efetch(
            db="pubmed",
            rettype="medline",
            retmode="text",
            retstart=start,
            retmax=batch_size,
            webenv=webenv,
            query_key=query_key,
        )
        records = Medline.parse(handle)
        for record in records:
            articles.append(
                {
                    "NCT Number": nct_number,
                    "PMID": record.get("PMID", ""),
                    "Date": record.get("DP", ""),
                    "Journal": record.get("JT", ""),
                    "Title": record.get("TI", ""),
                    "Publication Type": "; ".join(record.get("PT", [])),
                    "Abstract": record.get("AB", ""),
                }
            )
        handle.close()
        time.sleep(0.1)
    return articles


def assign_primary_and_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Assign one Primary article per NCT and subtype labels for others."""

    results: List[pd.DataFrame] = []

    for nct, group in df.groupby("NCT Number"):
        group = group.copy()
        group["Parsed Date"] = pd.to_datetime(group["Date"], errors="coerce")
        group = group.sort_values("Parsed Date")

        # Find oldest eligible non-review for primary
        primary_idx = None
        for idx, row in group.iterrows():
            is_review = (
                "review" in str(row["Title"]).lower()
                or "review" in str(row["Publication Type"]).lower()
                or "review" in str(row["Abstract"]).lower()
            )
            if not is_review:
                primary_idx = idx
                break

        group["Label"] = "Uncategorized"
        group["Matched Keywords"] = ""
        group["Match Source"] = ""

        if primary_idx is not None:
            group.at[primary_idx, "Label"] = "Primary"
            group.at[primary_idx, "Matched Keywords"] = "Earliest eligible publication"
            group.at[primary_idx, "Match Source"] = "System"

        # First pass: classify via Title
        for idx, row in group.iterrows():
            if idx == primary_idx:
                continue
            title = str(row["Title"]).lower()
            for label, keywords in subtype_keywords.items():
                for kw in keywords:
                    if kw.lower() in title:
                        group.at[idx, "Label"] = label
                        group.at[idx, "Matched Keywords"] = kw
                        group.at[idx, "Match Source"] = "Title"
                        break
                if group.at[idx, "Label"] != "Uncategorized":
                    break

        # Second pass: classify via Abstract if still Uncategorized
        for idx, row in group.iterrows():
            if row["Label"] != "Uncategorized":
                continue
            abstract = str(row["Abstract"]).lower()
            for label, keywords in subtype_keywords.items():
                for kw in keywords:
                    if kw.lower() in abstract:
                        group.at[idx, "Label"] = label
                        group.at[idx, "Matched Keywords"] = kw
                        group.at[idx, "Match Source"] = "Abstract"
                        break
                if group.at[idx, "Label"] != "Uncategorized":
                    break

        results.append(group)

    return pd.concat(results, ignore_index=True) if results else df


def index_pubmed_for_ncts(
    nct_numbers: List[str], email: Optional[str] = None, api_key: Optional[str] = None
) -> pd.DataFrame:
    """Index PubMed articles for given NCT IDs and classify them.

    Returns a DataFrame with one row per PubMed article and columns:
    [NCT Number, PMID, Date, Journal, Title, Publication Type, Abstract,
     Parsed Date, Label, Matched Keywords, Match Source].
    """

    if not nct_numbers:
        return pd.DataFrame()

    _configure_entrez(email=email, api_key=api_key)

    all_articles: List[Dict[str, str]] = []
    for nct in sorted({n.strip() for n in nct_numbers if n}):
        if not nct:
            continue
        print(f"Searching PubMed for {nct}...")
        try:
            webenv, query_key, count = search_pubmed_by_nct(nct)
            if count > 0:
                arts = fetch_article_details(nct, webenv, query_key, count)
                all_articles.extend(arts)
                print(f"  {count} article(s) found for {nct}")
            else:
                print(f"  No articles found for {nct}")
        except Exception as exc:  # noqa: BLE001
            print(f"  Error for {nct}: {exc}")

    if not all_articles:
        return pd.DataFrame()

    df = pd.DataFrame(all_articles)
    df = assign_primary_and_labels(df)
    return df


def save_index_from_csv(input_file: str, output_file: Optional[str] = None) -> str:
    """CLI helper: read NCTs from a CSV and write a classified index CSV.

    This mirrors your original script but is optional for the Streamlit app.
    """

    nct_numbers = read_nct_numbers(input_file)
    df = index_pubmed_for_ncts(nct_numbers)
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"nct_pubmed_indexed_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    return os.path.abspath(output_file)


if __name__ == "__main__":
    # Simple CLI: python nct_pubmed_classifier.py NCTs.csv
    import sys

    if len(sys.argv) < 2:
        print("Usage: python nct_pubmed_classifier.py NCTs.csv [OUTPUT.csv]")
        raise SystemExit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    out = save_index_from_csv(in_path, out_path)
    print(f"Results saved to: {out}")
