import json
import sys
from datetime import date
from typing import Any, Dict, List, Optional

import requests


CTGOV_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_ctgov_study(nct_id: str) -> Dict[str, Any]:
    """Fetch full study record (including results, if posted) for a single NCT ID.

    Uses the ClinicalTrials.gov v2 single-study endpoint /studies/{nct_id}.
    """

    url = f"{CTGOV_BASE_URL}/{nct_id}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # Single-study endpoint returns the study record directly as a dict.
    return data


def _extract_ctgov_result_dates(study: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Extract CT.gov results posting / update dates for a study.

    Returns ISO-like date strings (YYYY or YYYY-MM or YYYY-MM-DD) when available.
    """

    status = (study.get("protocolSection") or {}).get("statusModule") or {}

    def _date_from_struct(key: str) -> Optional[str]:
        struct = status.get(key) or {}
        return struct.get("date")

    return {
        "ctgov_results_first_posted": _date_from_struct("resultsFirstPostDateStruct"),
        "ctgov_results_last_updated": _date_from_struct("lastUpdatePostDateStruct"),
    }


def _find_outcome_measure(outcomes: List[Dict[str, Any]], *keywords: str) -> Optional[Dict[str, Any]]:
    """Return the first outcome measure whose title contains all keywords (case-insensitive)."""

    for m in outcomes:
        title = (m.get("title") or "").lower()
        if all(k.lower() in title for k in keywords):
            return m
    return None


def _measure_group_n(measure: Dict[str, Any]) -> Dict[str, Optional[int]]:
    """Map groupId -> N (number of participants) for a measure, if denoms are present."""

    result: Dict[str, Optional[int]] = {}
    for denom in measure.get("denoms", []):
        for c in denom.get("counts", []):
            gid = c.get("groupId")
            if gid:
                try:
                    result[gid] = int(c.get("value")) if c.get("value") is not None else None
                except (TypeError, ValueError):
                    result[gid] = None
    return result


def _measure_group_values(measure: Dict[str, Any]) -> Dict[str, Dict[str, Optional[float]]]:
    """Map groupId -> {value, lower, upper} from the first category of a measure.

    For medians with 95% CI this captures the point estimate and CI bounds.
    For percentage measures, only "value" will typically be populated.
    """

    out: Dict[str, Dict[str, Optional[float]]] = {}
    classes = measure.get("classes") or []
    if not classes:
        return out

    # Most measures put the overall value in the first class / first category.
    categories = classes[0].get("categories") or []
    if not categories:
        return out

    measurements = categories[0].get("measurements") or []
    for meas in measurements:
        gid = meas.get("groupId")
        if not gid:
            continue
        def _to_float(key: str) -> Optional[float]:
            if meas.get(key) is None:
                return None
            try:
                return float(meas.get(key))
            except (TypeError, ValueError):
                return None

        out[gid] = {
            "value": _to_float("value"),
            "lower": _to_float("lowerLimit"),
            "upper": _to_float("upperLimit"),
        }

    return out


def _extract_time_to_event(measure: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract per-arm median + 95% CI + N for OS/PFS-like measures.

    Returns structure: { arm_name: {"median": float, "ci": [low, high], "n": int } }
    """

    if not measure:
        return {}

    groups = {g["id"]: g.get("title") for g in measure.get("groups", []) if g.get("id")}
    n_by_group = _measure_group_n(measure)
    vals_by_group = _measure_group_values(measure)

    summary: Dict[str, Any] = {}
    for gid, title in groups.items():
        vals = vals_by_group.get(gid) or {}
        if not vals:
            continue
        summary[title] = {
            "median": vals.get("value"),
            "ci": [vals.get("lower"), vals.get("upper")],
            "n": n_by_group.get(gid),
            "unit": measure.get("unitOfMeasure"),
        }
    return summary


def _extract_ae_summary(measure: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract key AE percentages per arm from the AE summary outcome measure.

    We look for category titles like "Any adverse event (AE)" and
    "Any serious AE (SAE)" and "Any AE resulting in discontinuation".
    Returns: { arm_name: { overall_ae, serious_ae, discontinuation_ae } }
    """

    if not measure:
        return {}

    groups = {g["id"]: g.get("title") for g in measure.get("groups", []) if g.get("id")}
    result: Dict[str, Dict[str, Optional[float]]] = {title: {} for title in groups.values()}

    def _normalize(title: str) -> str:
        return (title or "").lower()

    for cls in measure.get("classes", []):
        cat_title = _normalize(cls.get("title", ""))
        key: Optional[str] = None
        if "any adverse event" in cat_title and "treatment-related" not in cat_title:
            key = "overall_ae_pct"
        elif "serious ae" in cat_title or "serious adverse event" in cat_title:
            key = "serious_ae_pct"
        elif "resulting in discontinuation" in cat_title or "leading to discontinuation" in cat_title:
            key = "discontinuation_ae_pct"

        if not key:
            continue

        categories = cls.get("categories") or []
        if not categories:
            continue
        measurements = categories[0].get("measurements") or []
        for meas in measurements:
            gid = meas.get("groupId")
            if gid not in groups:
                continue
            arm_title = groups[gid]
            try:
                value = float(meas.get("value")) if meas.get("value") is not None else None
            except (TypeError, ValueError):
                value = None
            if arm_title not in result:
                result[arm_title] = {}
            result[arm_title][key] = value

    return result


def _extract_ae_from_events_module(study: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback AE extraction using resultsSection.adverseEventsModule.

    Some trials do not define an "Adverse events" outcome measure but do
    populate the adverseEventsModule with per-arm totals. Here we derive:
      - serious_ae_pct from seriousNumAffected / seriousNumAtRisk
      - overall_ae_pct as the max of serious and other AE percentages

    This is an approximation but good enough for a POC view when the
    dedicated AE outcome summary is missing.
    """

    module = (study.get("resultsSection") or {}).get("adverseEventsModule") or {}
    event_groups = module.get("eventGroups") or []
    if not event_groups:
        return {}

    summary: Dict[str, Dict[str, Optional[float]]] = {}

    for g in event_groups:
        title = g.get("title")
        if not title:
            continue

        def _pct(num_key: str, den_key: str) -> Optional[float]:
            num = g.get(num_key)
            den = g.get(den_key)
            if num is None or not den:
                return None
            try:
                return float(num) / float(den) * 100.0
            except (TypeError, ValueError, ZeroDivisionError):
                return None

        serious_pct = _pct("seriousNumAffected", "seriousNumAtRisk")
        other_pct = _pct("otherNumAffected", "otherNumAtRisk")

        arm_entry: Dict[str, Optional[float]] = {}
        if serious_pct is not None:
            arm_entry["serious_ae_pct"] = serious_pct
        if serious_pct is not None or other_pct is not None:
            vals = [v for v in (serious_pct, other_pct) if v is not None]
            if vals:
                arm_entry["overall_ae_pct"] = max(vals)

        if arm_entry:
            summary[title] = arm_entry

    return summary


def extract_ctgov_metrics(study: Dict[str, Any]) -> Dict[str, Any]:
    """Extract founder-defined metrics from a ClinicalTrials.gov study record.

    Metrics:
      - Overall survival (OS): median months + 95% CI per arm
      - Progression-free survival (PFS): median months + 95% CI per arm
      - Overall response rate (ORR) if present
      - AE summary: overall AEs, serious AEs, AEs leading to discontinuation (percentages)
    """

    results = (study.get("resultsSection") or {}).get("outcomeMeasuresModule") or {}
    outcome_measures = results.get("outcomeMeasures") or []

    os_m = _find_outcome_measure(outcome_measures, "overall", "survival")
    pfs_m = _find_outcome_measure(outcome_measures, "progression-free", "survival")
    orr_m = _find_outcome_measure(outcome_measures, "overall", "response") or _find_outcome_measure(
        outcome_measures, "objective", "response"
    )
    ae_m = _find_outcome_measure(outcome_measures, "adverse", "events")

    os_summary = _extract_time_to_event(os_m)
    pfs_summary = _extract_time_to_event(pfs_m)

    # ORR is usually expressed as a percentage without CI; we use the same helper.
    orr_summary: Dict[str, Any] = {}
    if orr_m:
        vals = _measure_group_values(orr_m)
        groups = {g["id"]: g.get("title") for g in orr_m.get("groups", []) if g.get("id")}
        for gid, arm_title in groups.items():
            if gid not in vals:
                continue
            try:
                value = float(vals[gid].get("value")) if vals[gid].get("value") is not None else None
            except (TypeError, ValueError):
                value = None
            orr_summary[arm_title] = {
                "orr_pct": value,
                "unit": orr_m.get("unitOfMeasure"),
            }

    ae_summary = _extract_ae_summary(ae_m)
    if not ae_summary:
        ae_summary = _extract_ae_from_events_module(study)

    metrics: Dict[str, Any] = {}
    # Merge by arm name
    arm_names = set(os_summary.keys()) | set(pfs_summary.keys()) | set(orr_summary.keys()) | set(ae_summary.keys())
    for arm in sorted(arm_names):
        metrics[arm] = {}
        if arm in os_summary:
            metrics[arm]["os"] = os_summary[arm]
        if arm in pfs_summary:
            metrics[arm]["pfs"] = pfs_summary[arm]
        if arm in orr_summary:
            metrics[arm]["orr"] = orr_summary[arm]
        if arm in ae_summary:
            metrics[arm]["ae"] = ae_summary[arm]

    return metrics


def fetch_pubmed_metadata_from_ctgov(study: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get PubMed references linked in the ClinicalTrials.gov record.

    For the POC we only fetch basic metadata (title, journal, year) for a few PMIDs.
    """

    refs = (study.get("referencesModule") or {}).get("references") or []
    pmids = [r.get("pmid") for r in refs if r.get("pmid")]
    # Limit to first 3 for the POC
    pmids = pmids[:3]
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    resp = requests.get(PUBMED_EFETCH_URL, params=params, timeout=30)
    resp.raise_for_status()
    xml_text = resp.text

    # Very lightweight parsing: pull out ArticleTitle and Journal/Year via crude regexes.
    # For a production system you'd use an XML parser, but this keeps the POC simple.
    import re

    articles: List[Dict[str, Any]] = []
    for pmid in pmids:
        # Find the block for this PMID
        pattern = rf"<PubmedArticle>[\s\S]*?<PMID[^>]*>{pmid}</PMID>[\s\S]*?</PubmedArticle>"
        m = re.search(pattern, xml_text)
        if not m:
            continue
        block = m.group(0)

        def _first(tag: str) -> Optional[str]:
            mm = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, re.DOTALL)
            return mm.group(1).strip() if mm else None

        title = _first("ArticleTitle")
        journal = _first("Title")  # Journal title inside <Journal>
        year = _first("Year")
        month = _first("Month")
        day = _first("Day")

        pub_date: Optional[str] = None
        if year:
            # Build a simple YYYY[-MM[-DD]] string when possible.
            if month and day:
                pub_date = f"{year}-{month}-{day}"
            elif month:
                pub_date = f"{year}-{month}"
            else:
                pub_date = year
        articles.append({
            "pmid": pmid,
            "title": title,
            "journal": journal,
            "year": year,
            "pub_date": pub_date,
        })

    return articles


def _parse_loose_date(value: Optional[str]) -> Optional[date]:
    """Parse ISO-like dates from CT.gov or PubMed (YYYY or YYYY-MM or YYYY-MM-DD).

    Returns a date object with missing month/day padded as 01 when needed.
    """

    if not value:
        return None
    try:
        # Try full ISO format first.
        return date.fromisoformat(value)
    except ValueError:
        parts = value.split("-")
        try:
            if len(parts) == 1:
                return date(int(parts[0]), 1, 1)
            if len(parts) == 2:
                return date(int(parts[0]), int(parts[1]), 1)
        except Exception:  # noqa: BLE001
            return None
    return None


def build_trial_document(nct_id: str) -> Dict[str, Any]:
    """High-level helper: fetch CT.gov + PubMed and build a single trial document.

    This is the shape you could later store as a MongoDB document.
    """

    study = fetch_ctgov_study(nct_id)
    ctgov_metrics = extract_ctgov_metrics(study)
    ctgov_dates = _extract_ctgov_result_dates(study)
    pubmed_articles = fetch_pubmed_metadata_from_ctgov(study)

    # Choose the first linked PubMed article as the "primary" one for dating.
    primary_pubmed_date: Optional[str] = None
    if pubmed_articles:
        primary_pubmed_date = pubmed_articles[0].get("pub_date") or pubmed_articles[0].get("year")

    ct_last = _parse_loose_date(ctgov_dates.get("ctgov_results_last_updated"))
    pm_date = _parse_loose_date(primary_pubmed_date)
    pubmed_newer_than_ctgov: Optional[bool]
    if ct_last and pm_date:
        pubmed_newer_than_ctgov = pm_date > ct_last
    else:
        pubmed_newer_than_ctgov = None

    doc: Dict[str, Any] = {
        "nct_id": nct_id,
        "condition": (study.get("derivedSection") or {})
        .get("conditionBrowseModule", {})
        .get("meshes", [{}])[0]
        .get("term"),
        "interventions": [
            i.get("name")
            for i in (study.get("protocolSection") or {})
            .get("armsInterventionsModule", {})
            .get("interventions", [])
            if i.get("name")
        ],
        "metrics": ctgov_metrics,
        "pubmed_references": pubmed_articles,
        "ctgov_results_first_posted": ctgov_dates.get("ctgov_results_first_posted"),
        "ctgov_results_last_updated": ctgov_dates.get("ctgov_results_last_updated"),
        "primary_pubmed_publication_date": primary_pubmed_date,
        "pubmed_newer_than_ctgov": pubmed_newer_than_ctgov,
    }

    return doc


def main(argv: List[str]) -> None:
    if len(argv) < 2:
        print("Usage: python ctgov_pubmed_poc.py NCT_ID [NCT_ID2 ...]")
        print("Example: python ctgov_pubmed_poc.py NCT01607957")
        raise SystemExit(1)

    nct_ids = [arg.strip().upper() for arg in argv[1:]]
    for nct_id in nct_ids:
        if not nct_id.startswith("NCT"):
            print(f"NCT ID '{nct_id}' should look like 'NCT01234567'")
            raise SystemExit(1)

    for nct_id in nct_ids:
        print(f"\nFetching trial data for {nct_id} from ClinicalTrials.gov and PubMed ...")
        doc = build_trial_document(nct_id)

        outfile = f"trial_metrics_{nct_id}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

        print(f"Saved metrics document to {outfile}")
        print("Summary (per arm):")
        for arm, metrics in doc.get("metrics", {}).items():
            print(f"\nArm: {arm}")
            os_m = metrics.get("os")
            if os_m:
                print(
                    f"  OS median: {os_m.get('median')} {os_m.get('unit')} (95% CI {os_m.get('ci')}, N={os_m.get('n')})"
                )
            pfs_m = metrics.get("pfs")
            if pfs_m:
                print(
                    f"  PFS median: {pfs_m.get('median')} {pfs_m.get('unit')} (95% CI {pfs_m.get('ci')}, N={pfs_m.get('n')})"
                )
            orr_m = metrics.get("orr")
            if orr_m:
                print(f"  ORR: {orr_m.get('orr_pct')} {orr_m.get('unit')}")
            ae_m = metrics.get("ae")
            if ae_m:
                if ae_m.get("overall_ae_pct") is not None:
                    print(f"  Any AE: {ae_m.get('overall_ae_pct')} %")
                if ae_m.get("serious_ae_pct") is not None:
                    print(f"  Serious AE: {ae_m.get('serious_ae_pct')} %")
                if ae_m.get("discontinuation_ae_pct") is not None:
                    print(f"  AE leading to discontinuation: {ae_m.get('discontinuation_ae_pct')} %")

        if doc.get("pubmed_references"):
            print("\nLinked PubMed articles:")
            for art in doc["pubmed_references"]:
                print(
                    f"  PMID {art.get('pmid')}: {art.get('title')} ({art.get('journal')}, {art.get('year')})"
                )


if __name__ == "__main__":
    main(sys.argv)
