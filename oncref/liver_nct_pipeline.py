import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from ctgov_pubmed_poc import extract_ctgov_metrics, fetch_ctgov_study

CTGOV_SEARCH_URL = "https://clinicaltrials.gov/api/v2/studies"
LIVER_KEYWORDS = [
    "liver",
    "hepatocellular",
    "hcc",
    "cholangiocarcinoma",
    "biliary tract",
    "hepatic",
]


def _extract_condition_terms(study: Dict[str, Any]) -> List[str]:
    terms: List[str] = []

    protocol_conditions = (
        (study.get("protocolSection") or {})
        .get("conditionsModule", {})
        .get("conditions", [])
    )
    for c in protocol_conditions:
        if c:
            terms.append(str(c))

    meshes = (
        (study.get("derivedSection") or {})
        .get("conditionBrowseModule", {})
        .get("meshes", [])
    )
    for m in meshes:
        term = (m or {}).get("term")
        if term:
            terms.append(str(term))

    return terms


def _is_liver_study(study: Dict[str, Any]) -> bool:
    text = " ".join(_extract_condition_terms(study)).lower()
    return any(k in text for k in LIVER_KEYWORDS)


def fetch_liver_nct_ids(max_trials: int = 200) -> List[str]:
    """Fetch strictly liver-related NCT IDs from CT.gov search results.

    If max_trials <= 0, fetches all available pages without a numeric cap.
    """

    nct_ids: List[str] = []
    page_token: Optional[str] = None

    fetch_all = max_trials <= 0

    while fetch_all or len(nct_ids) < max_trials:
        page_size = 50 if fetch_all else min(50, max_trials - len(nct_ids))
        params: Dict[str, Any] = {
            "query.term": "Liver Neoplasms",
            "pageSize": page_size,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(CTGOV_SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        studies = data.get("studies", [])
        for study in studies:
            if not _is_liver_study(study):
                continue
            nct = (
                (study.get("protocolSection") or {})
                .get("identificationModule", {})
                .get("nctId")
            )
            if nct and nct not in nct_ids:
                nct_ids.append(nct)

        page_token = data.get("nextPageToken")
        if not page_token or not studies:
            break

    return nct_ids


def _extract_status_dates(study: Dict[str, Any]) -> Dict[str, Optional[str]]:
    status = (study.get("protocolSection") or {}).get("statusModule") or {}
    first_posted = (status.get("resultsFirstPostDateStruct") or {}).get("date")
    last_updated = (status.get("lastUpdatePostDateStruct") or {}).get("date")
    start_date = (status.get("startDateStruct") or {}).get("date")
    completion_date = (status.get("completionDateStruct") or {}).get("date")
    primary_completion_date = (status.get("primaryCompletionDateStruct") or {}).get("date")
    return {
        "ctgov_results_first_posted": first_posted,
        "ctgov_results_last_updated": last_updated,
        "ctgov_start_date": start_date,
        "ctgov_completion_date": completion_date,
        "ctgov_primary_completion_date": primary_completion_date,
    }


def build_liver_trial_doc(nct_id: str) -> Dict[str, Any]:
    study = fetch_ctgov_study(nct_id)
    if not _is_liver_study(study):
        raise ValueError("Study excluded by strict liver condition filter")
    dates = _extract_status_dates(study)

    doc: Dict[str, Any] = {
        "nct_id": nct_id,
        "condition": "; ".join(_extract_condition_terms(study)) or None,
        "interventions": [
            i.get("name")
            for i in (study.get("protocolSection") or {})
            .get("armsInterventionsModule", {})
            .get("interventions", [])
            if i.get("name")
        ],
        "metrics": extract_ctgov_metrics(study),
        "ctgov_results_first_posted": dates.get("ctgov_results_first_posted"),
        "ctgov_results_last_updated": dates.get("ctgov_results_last_updated"),
        "ctgov_start_date": dates.get("ctgov_start_date"),
        "ctgov_completion_date": dates.get("ctgov_completion_date"),
        "ctgov_primary_completion_date": dates.get("ctgov_primary_completion_date"),
    }
    return doc


def flatten_efficacy(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for arm, m in (doc.get("metrics") or {}).items():
        os_m = m.get("os") or {}
        pfs_m = m.get("pfs") or {}
        orr_m = m.get("orr") or {}
        rows.append(
            {
                "Trial (NCT)": doc.get("nct_id"),
                "Condition": doc.get("condition"),
                "Arm": arm,
                "Interventions": ", ".join(doc.get("interventions") or []),
                "OS median": os_m.get("median"),
                "OS 95% CI low": (os_m.get("ci") or [None, None])[0],
                "OS 95% CI high": (os_m.get("ci") or [None, None])[1],
                "OS N": os_m.get("n"),
                "PFS median": pfs_m.get("median"),
                "PFS 95% CI low": (pfs_m.get("ci") or [None, None])[0],
                "PFS 95% CI high": (pfs_m.get("ci") or [None, None])[1],
                "PFS N": pfs_m.get("n"),
                "ORR %": orr_m.get("orr_pct"),
                "CT.gov last updated": doc.get("ctgov_results_last_updated"),
                "Trial start date": doc.get("ctgov_start_date"),
                "Trial completion date": doc.get("ctgov_completion_date") or doc.get("ctgov_primary_completion_date"),
            }
        )
    return rows


def flatten_safety(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for arm, m in (doc.get("metrics") or {}).items():
        ae_m = m.get("ae") or {}
        if not ae_m:
            continue
        rows.append(
            {
                "Trial (NCT)": doc.get("nct_id"),
                "Condition": doc.get("condition"),
                "Arm": arm,
                "Any AE %": ae_m.get("overall_ae_pct"),
                "Serious AE %": ae_m.get("serious_ae_pct"),
                "AE leading to discontinuation %": ae_m.get("discontinuation_ae_pct"),
                "CT.gov last updated": doc.get("ctgov_results_last_updated"),
                "Trial start date": doc.get("ctgov_start_date"),
                "Trial completion date": doc.get("ctgov_completion_date") or doc.get("ctgov_primary_completion_date"),
            }
        )
    return rows


def run_pipeline(max_trials: int, out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    nct_ids = fetch_liver_nct_ids(max_trials=max_trials)
    docs: List[Dict[str, Any]] = []
    efficacy_rows: List[Dict[str, Any]] = []
    safety_rows: List[Dict[str, Any]] = []

    for nct_id in nct_ids:
        try:
            doc = build_liver_trial_doc(nct_id)
        except Exception as exc:  # noqa: BLE001
            print(f"Error for {nct_id}: {exc}")
            continue
        docs.append(doc)
        efficacy_rows.extend(flatten_efficacy(doc))
        safety_rows.extend(flatten_safety(doc))

    docs_file = out_dir / f"liver_trial_documents_{timestamp}.json"
    eff_file = out_dir / f"liver_efficacy_{timestamp}.csv"
    saf_file = out_dir / f"liver_safety_{timestamp}.csv"
    nct_file = out_dir / f"liver_ncts_{timestamp}.csv"

    with docs_file.open("w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)

    pd.DataFrame({"NCT": nct_ids}).to_csv(nct_file, index=False)
    pd.DataFrame(efficacy_rows).to_csv(eff_file, index=False)
    pd.DataFrame(safety_rows).to_csv(saf_file, index=False)

    manifest = {
        "generated_at": timestamp,
        "nct_count_input": str(len(nct_ids)),
        "trial_docs": str(docs_file),
        "efficacy_csv": str(eff_file),
        "safety_csv": str(saf_file),
        "nct_csv": str(nct_file),
    }
    manifest_file = out_dir / "liver_latest_manifest.json"
    with manifest_file.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("Pipeline completed.")
    print(json.dumps(manifest, indent=2))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Liver cancer CT.gov extraction pipeline")
    parser.add_argument(
        "--max-trials",
        type=int,
        default=200,
        help="Maximum number of liver trials to process. Use 0 for all available trials.",
    )
    parser.add_argument("--out-dir", default="liver_pipeline_outputs", help="Output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(max_trials=args.max_trials, out_dir=Path(args.out_dir))
