import json
from collections import Counter, defaultdict
from typing import Any, Dict, List

import requests

CTGOV_SEARCH_URL = "https://clinicaltrials.gov/api/v2/studies"


# You can extend this list with the cancer labels you care about.
# Using CT.gov-style condition terms works best (e.g. "Colorectal Neoplasms").
CANCER_TYPES = [
    "Colorectal Neoplasms",
    "Lung Neoplasms",
    "Breast Neoplasms",
]


def search_trials_for_condition(condition: str, max_trials: int = 200) -> List[Dict[str, Any]]:
    """Fetch up to max_trials trials for a given condition term from CT.gov v2.

    We keep the query simple (term + pageSize) to avoid 400 errors from
    incompatible filters in v2. You can later refine with status/phase filters.
    """

    studies: List[Dict[str, Any]] = []
    page_token: str | None = None
    remaining = max_trials

    while remaining > 0:
        page_size = min(50, remaining)
        params: Dict[str, Any] = {"query.term": condition, "pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(CTGOV_SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("studies", [])
        studies.extend(batch)
        remaining -= len(batch)
        page_token = data.get("nextPageToken")
        if not page_token or not batch:
            break

    return studies


def discover_drugs_for_condition(condition: str, top_n_drugs: int = 3, max_trials: int = 200) -> Dict[str, List[str]]:
    """Return mapping drug_name -> list of representative NCT IDs for a condition.

    We:
      - search CT.gov trials for the condition
      - count intervention names (drugs/regimens)
      - pick the top_n_drugs by frequency
      - for each drug, keep up to 2 NCT IDs from trials where it appears
    """

    studies = search_trials_for_condition(condition, max_trials=max_trials)

    # Count intervention names
    counts: Counter[str] = Counter()
    drug_to_ncts: defaultdict[str, List[str]] = defaultdict(list)

    for s in studies:
        nct_id = (
            (s.get("protocolSection") or {})
            .get("identificationModule", {})
            .get("nctId")
        )
        arms_mod = (s.get("protocolSection") or {}).get("armsInterventionsModule", {})
        interventions = arms_mod.get("interventions", [])
        for iv in interventions:
            name = (iv.get("name") or "").strip()
            if not name:
                continue
            counts[name] += 1
            if nct_id and len(drug_to_ncts[name]) < 2:
                drug_to_ncts[name].append(nct_id)

    top_drugs = [name for name, _ in counts.most_common(top_n_drugs)]
    return {name: drug_to_ncts.get(name, []) for name in top_drugs}


def build_cancer_drug_mapping(cancer_types: List[str]) -> Dict[str, Dict[str, List[str]]]:
    """Build mapping: cancer_type -> { drug_name -> [nct_ids...] }"""

    mapping: Dict[str, Dict[str, List[str]]] = {}
    for cond in cancer_types:
        print(f"Discovering drugs for condition: {cond} ...")
        try:
            mapping[cond] = discover_drugs_for_condition(cond)
        except Exception as exc:  # noqa: BLE001
            print(f"  Error for {cond}: {exc}")
    return mapping


def main() -> None:
    mapping = build_cancer_drug_mapping(CANCER_TYPES)
    outfile = "cancer_drug_nct_mapping.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    print(f"Saved mapping to {outfile}")


if __name__ == "__main__":
    main()
