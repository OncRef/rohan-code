import re
from datetime import datetime
from pathlib import Path

import pandas as pd


INPUT_FILE = Path("OncRef.Drugs_updated.csv")

CATEGORIES = [
    "Adrenal Cancer and Neuroendocrine Tumors",
    "Ampullary Adenocarcinoma",
    "Anal Cancer",
    "Appendix Cancer",
    "Bladder Cancer",
    "Bone and Joint Cancers",
    "Brain and Other Nervous System Cancers",
    "Breast Cancer",
    "Castleman Disease",
    "Colorectal Cancer",
    "Esophageal Cancer",
    "Gallbladder Cancer",
    "Gastric (Stomach) Cancer",
    "Gastrointestinal Stromal Tumors",
    "Gestational Cancers",
    "Gynecological Cancers",
    "Head and Neck Cancers",
    "Hematological Malignancies",
    "Kidney (Renal) and Urethral Cancers",
    "Liver and Bile Duct Cancers",
    "Lung Cancers",
    "Mesothelioma",
    "Neuroblastoma",
    "Occult Primary",
    "Ocular Cancers",
    "Pancreatic Cancer",
    "Pediatric Cancers",
    "Penile Cancer",
    "Prostate Cancer",
    "Skin Cancers",
    "Small Intestine Cancers",
    "Soft Tissue Cancers (including Heart)",
    "Testicular Cancer",
    "Thymic Cancer",
    "Thyroid Cancer",
]


RULES = [
    (
        "Adrenal Cancer and Neuroendocrine Tumors",
        r"\badrenal\b|pheochromocytoma|paraganglioma|neuroendocrine|carcinoid|islet cell|vipoma|glucagonoma|insulinoma",
    ),
    ("Ampullary Adenocarcinoma", r"\bampullary\b|ampulla of vater"),
    ("Anal Cancer", r"\banal\b"),
    ("Appendix Cancer", r"appendi(c|x)|appendiceal"),
    (
        "Bladder Cancer",
        r"\bbladder\b|urothelial carcinoma|urothelial cancer|urothelial tumor|upper tract urothelial",
    ),
    (
        "Bone and Joint Cancers",
        r"osteosarcoma|ewing|chondrosarcoma|bone cancer|bone sarcoma|paget.*bone|joint",
    ),
    (
        "Brain and Other Nervous System Cancers",
        r"glioblastoma|glioma|astrocytoma|oligodendroglioma|ependymoma|medulloblastoma|meningioma|cns\b|brain|central nervous system|spinal cord|neurofibromatosis",
    ),
    ("Breast Cancer", r"breast|mammary|her2[- ]positive|triple[- ]negative"),
    ("Castleman Disease", r"castleman"),
    ("Colorectal Cancer", r"colorectal|colon|rectal|rectum|sigmoid"),
    ("Esophageal Cancer", r"esophag"),
    ("Gallbladder Cancer", r"gallbladder"),
    ("Gastric (Stomach) Cancer", r"\bgastric\b|stomach"),
    ("Gastrointestinal Stromal Tumors", r"\bgist\b|gastrointestinal stromal"),
    (
        "Gestational Cancers",
        r"gestational|choriocarcinoma|hydatidiform mole|trophoblastic",
    ),
    (
        "Gynecological Cancers",
        r"ovarian|cervical|endometrial|uterine|fallopian|vulvar|vaginal|gynecolog",
    ),
    (
        "Head and Neck Cancers",
        r"head and neck|nasopharyn|oropharyn|hypopharyn|laryn|oral cavity|salivary|tongue|tonsil|sinonasal|maxillary",
    ),
    (
        "Hematological Malignancies",
        r"leukemia|lymphoma|myeloma|myelodysplastic|myeloproliferative|polycythemia vera|thrombocythemia|waldenstrom|hodgkin|non[- ]hodgkin|cll|\baml\b|\ball\b|\bcml\b|cmml|mantle cell|plasma cell|lymphocytic|hematologic|myelofibrosis|mycosis fungoides",
    ),
    (
        "Kidney (Renal) and Urethral Cancers",
        r"\brenal\b|kidney|urethral|collecting duct|wilms tumor",
    ),
    (
        "Liver and Bile Duct Cancers",
        r"\bliver\b|hepatocellular|\bhcc\b|cholangiocarcinoma|biliary|intrahepatic",
    ),
    ("Lung Cancers", r"\blung\b|nsclc|non[- ]small cell|small cell lung|sclc"),
    ("Mesothelioma", r"mesothelioma"),
    ("Neuroblastoma", r"neuroblastoma"),
    ("Occult Primary", r"occult primary|unknown primary|\bcup\b"),
    (
        "Ocular Cancers",
        r"ocular|uveal|retinoblastoma|choroidal|conjunctival|melanoma of the eye",
    ),
    ("Pancreatic Cancer", r"pancrea"),
    ("Pediatric Cancers", r"pediatric|paediatric|childhood|children|infant"),
    ("Penile Cancer", r"penile|penis cancer"),
    ("Prostate Cancer", r"prostate|prostatic"),
    ("Skin Cancers", r"melanoma|skin cancer|cutaneous|basal cell|squamous cell skin|merkel|actinic keratos"),
    ("Small Intestine Cancers", r"small intestine|duodenal|jejunal|ileal|duodenum"),
    (
        "Soft Tissue Cancers (including Heart)",
        r"sarcoma|leiomyosarcoma|liposarcoma|rhabdomyosarcoma|angiosarcoma|synovial sarcoma|soft tissue|cardiac tumor|heart cancer|desmoid",
    ),
    ("Testicular Cancer", r"testicular|testis|germ cell tumor"),
    ("Thymic Cancer", r"thymic|thymoma"),
    ("Thyroid Cancer", r"thyroid|medullary thyroid|anaplastic thyroid"),
]


COMPILED_RULES = [(category, re.compile(pattern, re.IGNORECASE)) for category, pattern in RULES]


def map_categories(indication_text: str) -> list[str]:
    if not isinstance(indication_text, str) or not indication_text.strip():
        return ["Occult Primary"]

    hits = [category for category, pattern in COMPILED_RULES if pattern.search(indication_text)]
    unique_hits = sorted(set(hits), key=CATEGORIES.index)
    return unique_hits if unique_hits else ["Occult Primary"]


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE, low_memory=False)
    extracted_cols = [c for c in df.columns if c.endswith(".extracted_cancer")]
    if not extracted_cols:
        raise ValueError("No extracted cancer indication columns found.")

    def build_text(row: pd.Series) -> str:
        parts = []
        for col in extracted_cols:
            value = row[col]
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        return " | ".join(parts)

    df["indication_text_combined"] = df.apply(build_text, axis=1)
    mapped = df["indication_text_combined"].apply(map_categories)

    df["mapped_cancer_types"] = mapped.apply(lambda x: " | ".join(x))
    df["primary_cancer_type"] = mapped.apply(lambda x: x[0])
    df["mapping_method"] = mapped.apply(
        lambda x: "keyword_rules" if x != ["Occult Primary"] else "fallback_occult_primary"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(f"OncRef.Drugs_updated_mapped_{timestamp}.csv")
    df.to_csv(output_file, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Output file: {output_file}")
    print("Primary category distribution:")
    print(df["primary_cancer_type"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()