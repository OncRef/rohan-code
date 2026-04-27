import pandas as pd
from Bio import Entrez, Medline
import os
import ssl
import time
from datetime import datetime
import certifi

# Configure NCBI API access
Entrez.email = os.getenv("NCBI_EMAIL", "thomasrcoughlin@gmail.com")
Entrez.api_key = os.getenv("NCBI_API_KEY", "")
# Ensure HTTPS cert chain works consistently in local environments.
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

# Keyword mappings for subtype classification
subtype_keywords = {
    "Interim": ["interim", "updated interim"],
    "Final": ["final overall survival", "final analysis", "final update", "final progression free survival", "final results", "final result"],
    "Update": ["updated analysis", "updated"],
    "Secondary": ["secondary analysis"],
    "Exploratory": ["exploratory analysis", "exploratory analyses", "additional analyses"],
    "Correlation": ["correlation between", "correlation of"],
    "Subgroup": [
        "subgroup analysis", "subgroup", "subpopulation", "subpopulation analysis", "subgroups",
        "based on", "subanalysis", "sub-analysis", "sub-group", "Child-Pugh", "Child Pugh",
        "serum", "biomarkers", "biomarker", "proteinuria", "urine", "creatinine ratio", "ratio",
        "DNA Liquid Biopsies", "dna liquid", "ctdna", "circulating tumor"
    ],
    "QOL": ["quality of life", "Health-Related Quality of Life", "quality-of-life"],
    "RWE": ["real"],
    "Cost-Effectiveness": ["cost-effectiveness"],
    "Retrospective": ["retrospective analysis", "retrospective"],
    "Post hoc": ["Prognostic Score and Benefit", "post hoc analysis", "post hoc", "prognostic score"],
    "Stratified": ["stratified analysis", "stratified"],
    "Patient-Reported Outcomes": ["patient-reported outcome", "patient-reported", "patient reported"],
    "Systematic Review or Meta-Analysis": ["systematic review", "meta-analysis"],
    "Long-term": ["long-term safety and efficacy", "long-term", "long-term extension study"],
    "2-year results": ["2-year results", "2 year results", "two year results", "two-year results", "2 year", "two year", "two-year"],
    "3-year results": ["3-year results", "3 year results", "three year results", "three-year results", "3 year", "three year", "three-year"],
    "4-year results": ["4-year results", "4 year results", "four year results", "four-year results", "4 year", "four year", "four-year"],
    "5-year results": ["5-year results", "5 year results", "five year results", "five-year results", "5 year", "5-year", "five year", "five-year"],
    "Other": ["Observational studies", "observational study", "Covariate-adjusted analysis", "Matching-Adjusted", "practice guideline"],
    "Treatment sequencing": ["treatment sequencing", "treatment sequence"],
    "China": ["Chinese", "China"],
    "Japan": ["Japanese", "Japan"],
    "Asia": ["Asian"],
    "Safety Analysis": ["hepatic events", "viral events", "safety analysis"],
    "Characterization": ["characterization", "characterization of response"],
    "Summary": ["FDA Approval Summary", "Approval Summary", "Plain language summary", "plain language"],
    "Pharmacokinetics/pharmacodynamics": ["Pharmacokinetics", "pharmacodynamics"],
    "Statistical": ["Statistical", "Covariate", "covariate-adjusted", "adjusted analysis"],
    "Case Study": ["A case of", "a case", "patient case", "case study"],
    "Predictive/Prognostic": ["predictive", "prognostic"]
}

# Read NCTs from CSV
def read_nct_numbers(file_path):
    df = pd.read_csv(file_path)
    return df.iloc[:, 0].dropna().unique().tolist()

# Search PubMed by NCT
def search_pubmed_by_nct(nct_number):
    handle = Entrez.esearch(db="pubmed", term=nct_number, usehistory="y", retmax=1000)
    record = Entrez.read(handle)
    handle.close()
    time.sleep(0.1)
    return record.get("WebEnv"), record.get("QueryKey"), int(record.get("Count", 0))

# Fetch metadata from PubMed
def fetch_article_details(nct_number, webenv, query_key, count):
    batch_size = 100
    articles = []

    for start in range(0, count, batch_size):
        handle = Entrez.efetch(
            db="pubmed",
            rettype="medline",
            retmode="text",
            retstart=start,
            retmax=batch_size,
            webenv=webenv,
            query_key=query_key
        )
        records = Medline.parse(handle)
        for record in records:
            articles.append({
                "NCT Number": nct_number,
                "PMID": record.get("PMID", ""),
                "Date": record.get("DP", ""),
                "Journal": record.get("JT", ""),
                "Title": record.get("TI", ""),
                "Publication Type": "; ".join(record.get("PT", [])),
                "Abstract": record.get("AB", "")
            })
        handle.close()
        time.sleep(0.1)
    return articles

# Assign "Primary" and keyword labels
def assign_primary_and_labels(df):
    results = []

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

    return pd.concat(results, ignore_index=True)

# Full process
def process_nct_articles(input_file, output_file):
    nct_numbers = read_nct_numbers(input_file)
    all_articles = []

    for nct in nct_numbers:
        print(f"\n🔎 Searching PubMed for {nct}...")
        try:
            webenv, query_key, count = search_pubmed_by_nct(nct)
            if count > 0:
                articles = fetch_article_details(nct, webenv, query_key, count)
                all_articles.extend(articles)
                print(f"  ✅ {count} article(s) found for {nct}")
            else:
                print(f"  ⚠️ No articles found for {nct}")
        except Exception as e:
            print(f"  ❌ Error for {nct}: {e}")

    if all_articles:
        df = pd.DataFrame(all_articles)
        df = assign_primary_and_labels(df)
        df.to_csv(output_file, index=False)
        print(f"\n✅ Results saved to: {os.path.abspath(output_file)}")
    else:
        print("\n⚠️ No articles found for any NCT numbers.")

# Main entry
if __name__ == "__main__":
    input_file = "NCTs.csv"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"nct_pubmed_indexed_{timestamp}.csv"
    process_nct_articles(input_file, output_file)
