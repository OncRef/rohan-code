import pdfplumber
import re
import pandas as pd
from tqdm import tqdm  # progress bar

pdf_path = "AACR2025_Proceedings_050725.pdf"

# Regex for company names
company_pattern = re.compile(
    r"\b([A-Z][\w &\-]+(?:Inc|Ltd|LLC|Corporation|Corp|Biotech|Therapeutics|Pharma|Pharmaceuticals|Biosciences|Bio|Life Sciences))\b",
    re.IGNORECASE
)

# Exclude academic/hospital affiliations
exclude_pattern = re.compile(
    r"(university|hospital|institute|college|school|center|centre)",
    re.IGNORECASE
)

companies = set()

with pdfplumber.open(pdf_path) as pdf:
    total_pages = len(pdf.pages)
    print(f"Total pages: {total_pages}")

    for page in tqdm(pdf.pages, desc="Processing pages"):
        text = page.extract_text() or ""
        matches = company_pattern.findall(text)
        for comp in matches:
            # Clean parentheses and locations
            comp = re.sub(r"\(.*?\)", "", comp).strip()
            comp = re.sub(r",.*", "", comp).strip()
            if comp and not exclude_pattern.search(comp):
                companies.add(comp)

# Save results
df = pd.DataFrame(sorted(companies), columns=["Company"])
df.to_csv("aacr_2025_companies_clean.csv", index=False)

print("Extraction complete!")
print(f"Total companies extracted: {len(companies)}")