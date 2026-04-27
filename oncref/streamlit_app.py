import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from ctgov_pubmed_poc import build_trial_document
from nct_pubmed_classifier import index_pubmed_for_ncts


# Minimal mapping from regimen/arm label to generic and brand names.
# For a full product, you would maintain this in your own drug catalog
# and join by a stable drug ID instead of hard-coding here.
DRUG_NAME_MAP: Dict[str, Dict[str, str]] = {
    "TAS-102": {"generic": "trifluridine/tipiracil", "brand": "Lonsurf"},
    "Placebo": {"generic": "placebo", "brand": "placebo"},
}


def lookup_drug_names(arm_label: str) -> Tuple[str | None, str | None]:
    """Return (generic_name, brand_name) for a given arm/regimen label, if known.

    Falls back to None/None when we don't have a mapping yet.
    """

    info = DRUG_NAME_MAP.get(arm_label, {})
    return info.get("generic"), info.get("brand")


def efficacy_rows(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten efficacy metrics (OS, PFS, ORR) into per-arm rows."""

    rows: List[Dict[str, Any]] = []
    metrics = doc.get("metrics", {}) or {}
    freshness_flag = doc.get("pubmed_newer_than_ctgov")
    if freshness_flag is True:
        freshness_label = "PubMed newer than CT.gov"
    elif freshness_flag is False:
        freshness_label = "CT.gov as recent or newer"
    else:
        freshness_label = None
    for arm_name, m in metrics.items():
        os_m = m.get("os") or {}
        pfs_m = m.get("pfs") or {}
        orr_m = m.get("orr") or {}
        generic_name, brand_name = lookup_drug_names(arm_name)
        rows.append(
            {
                "Trial (NCT)": doc.get("nct_id"),
                "Condition": doc.get("condition"),
                "Arm": arm_name,
                "Generic name": generic_name,
                "Brand name": brand_name,
                "Interventions": ", ".join(doc.get("interventions", [])),
                "Freshness flag": freshness_label,
                "OS median": os_m.get("median"),
                "OS 95% CI low": (os_m.get("ci") or [None, None])[0],
                "OS 95% CI high": (os_m.get("ci") or [None, None])[1],
                "OS N": os_m.get("n"),
                "OS unit": os_m.get("unit"),
                "PFS median": pfs_m.get("median"),
                "PFS 95% CI low": (pfs_m.get("ci") or [None, None])[0],
                "PFS 95% CI high": (pfs_m.get("ci") or [None, None])[1],
                "PFS N": pfs_m.get("n"),
                "PFS unit": pfs_m.get("unit"),
                "ORR %": orr_m.get("orr_pct"),
            }
        )
    return rows


def safety_rows(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten safety metrics (AEs) into per-arm rows."""

    rows: List[Dict[str, Any]] = []
    metrics = doc.get("metrics", {}) or {}
    for arm_name, m in metrics.items():
        ae_m = m.get("ae") or {}
        if not ae_m:
            continue
        generic_name, brand_name = lookup_drug_names(arm_name)
        rows.append(
            {
                "Trial (NCT)": doc.get("nct_id"),
                "Condition": doc.get("condition"),
                "Arm": arm_name,
                "Generic name": generic_name,
                "Brand name": brand_name,
                "Any AE %": ae_m.get("overall_ae_pct"),
                "Serious AE %": ae_m.get("serious_ae_pct"),
                "AE leading to discontinuation %": ae_m.get("discontinuation_ae_pct"),
            }
        )
    return rows


def get_ncbi_credentials() -> Tuple[str | None, str | None]:
    """Resolve NCBI credentials from env vars first, then Streamlit secrets."""

    email = os.getenv("NCBI_EMAIL")
    api_key = os.getenv("NCBI_API_KEY")

    # st.secrets is optional and may not exist in local runs without secrets.toml.
    try:
        if not email:
            email = st.secrets.get("NCBI_EMAIL")
        if not api_key:
            api_key = st.secrets.get("NCBI_API_KEY")
    except Exception:  # noqa: BLE001
        pass

    return email, api_key


def find_latest_mapped_drug_file() -> Path | None:
    """Return the newest mapped drug CSV if available."""

    files = sorted(Path(".").glob("OncRef.Drugs_updated_mapped_*.csv"))
    files = [f for f in files if not f.name.endswith("_primary_counts.csv")]
    return files[-1] if files else None


def extract_nct_ids(value: Any) -> List[str]:
    """Extract normalized NCT IDs from free-text strings."""

    if value is None:
        return []
    text = str(value).upper()
    return sorted(set(re.findall(r"NCT\d{8}", text)))


def build_primary_cancer_drug_mapping(mapped_df: pd.DataFrame) -> Dict[str, Dict[str, List[str]]]:
    """Build mapping: primary_cancer_type -> generic_name -> [NCT IDs]."""

    mapping: Dict[str, Dict[str, set[str]]] = {}
    for _, row in mapped_df.iterrows():
        cancer_type = str(row.get("primary_cancer_type") or "").strip()
        drug_name = str(row.get("generic_name") or "").strip()
        if not cancer_type or not drug_name:
            continue

        ncts = extract_nct_ids(row.get("ncts"))
        if not ncts:
            continue

        mapping.setdefault(cancer_type, {})
        mapping[cancer_type].setdefault(drug_name, set())
        mapping[cancer_type][drug_name].update(ncts)

    return {
        ctype: {drug: sorted(ids) for drug, ids in sorted(drug_map.items())}
        for ctype, drug_map in sorted(mapping.items())
    }


def render_visualizations(df_eff: pd.DataFrame | None, df_saf: pd.DataFrame | None) -> None:
    """Render opinionated insight charts plus configurable custom charts."""

    st.subheader("Insights")

    has_eff = df_eff is not None and not df_eff.empty
    has_saf = df_saf is not None and not df_saf.empty
    if not has_eff and not has_saf:
        st.info("No data available for visualizations.")
        return

    # ---------- Insight charts (prebuilt, clinically meaningful) ----------
    if has_eff:
        eff = df_eff.copy()
        eff["OS median"] = pd.to_numeric(eff["OS median"], errors="coerce")
        eff["PFS median"] = pd.to_numeric(eff["PFS median"], errors="coerce")
        eff["ORR %"] = pd.to_numeric(eff["ORR %"], errors="coerce")
        eff["OS 95% CI low"] = pd.to_numeric(eff["OS 95% CI low"], errors="coerce")
        eff["OS 95% CI high"] = pd.to_numeric(eff["OS 95% CI high"], errors="coerce")
        eff["PFS 95% CI low"] = pd.to_numeric(eff["PFS 95% CI low"], errors="coerce")
        eff["PFS 95% CI high"] = pd.to_numeric(eff["PFS 95% CI high"], errors="coerce")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            med_os = eff["OS median"].median(skipna=True)
            st.metric("Median OS across arms", f"{med_os:.2f}" if pd.notna(med_os) else "NA")
        with col_b:
            med_pfs = eff["PFS median"].median(skipna=True)
            st.metric("Median PFS across arms", f"{med_pfs:.2f}" if pd.notna(med_pfs) else "NA")
        with col_c:
            med_orr = eff["ORR %"].median(skipna=True)
            st.metric("Median ORR across arms", f"{med_orr:.1f}%" if pd.notna(med_orr) else "NA")

        os_pfs_df = eff.dropna(subset=["OS median", "PFS median"])
        if not os_pfs_df.empty:
            st.markdown("#### OS and PFS per regimen")
            # Dumbbell layout remains informative even with a single regimen.
            os_pfs_df = os_pfs_df.copy()
            os_pfs_df["Regimen"] = os_pfs_df["Arm"] + " | " + os_pfs_df["Trial (NCT)"].astype(str)
            long_df = os_pfs_df.melt(
                id_vars=["Regimen", "Trial (NCT)", "Arm", "ORR %"],
                value_vars=["PFS median", "OS median"],
                var_name="Metric",
                value_name="Median",
            )

            rules = (
                alt.Chart(os_pfs_df)
                .mark_rule(color="#9ca3af", strokeWidth=2)
                .encode(
                    y=alt.Y("Regimen:N", title="Regimen"),
                    x=alt.X("PFS median:Q", title="Median time"),
                    x2="OS median:Q",
                    tooltip=["Trial (NCT)", "Arm", "PFS median", "OS median", "ORR %"],
                )
            )

            points = (
                alt.Chart(long_df)
                .mark_circle(size=120, opacity=0.9)
                .encode(
                    y=alt.Y("Regimen:N", title="Regimen"),
                    x=alt.X("Median:Q", title="Median time"),
                    color=alt.Color("Metric:N", title="Metric", scale=alt.Scale(range=["#0f766e", "#b45309"])),
                    tooltip=["Trial (NCT)", "Arm", "Metric", "Median", "ORR %"],
                )
            )

            st.altair_chart((rules + points).properties(height=360), use_container_width=True)

        if eff[["Arm", "ORR %"]].dropna(subset=["ORR %"]).shape[0] > 0:
            st.markdown("#### ORR by regimen")
            orr_chart = (
                alt.Chart(eff.dropna(subset=["ORR %"]))
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                .encode(
                    x=alt.X("Arm:N", sort="-y", title="Arm"),
                    y=alt.Y("ORR %:Q", title="ORR %"),
                    color=alt.Color("Arm:N", legend=None),
                    tooltip=["Trial (NCT)", "Arm", "ORR %"],
                )
                .properties(height=320)
            )
            st.altair_chart(orr_chart, use_container_width=True)

        # Heatmap: normalized efficacy metrics by arm to compare profiles quickly.
        heat_cols = ["OS median", "PFS median", "ORR %"]
        heat_src = eff[["Arm", "Trial (NCT)"] + heat_cols].copy()
        for c in heat_cols:
            cmin = heat_src[c].min(skipna=True)
            cmax = heat_src[c].max(skipna=True)
            if pd.notna(cmin) and pd.notna(cmax) and cmax != cmin:
                heat_src[c] = (heat_src[c] - cmin) / (cmax - cmin)
            else:
                heat_src[c] = pd.NA
        heat_long = heat_src.melt(id_vars=["Arm", "Trial (NCT)"], value_vars=heat_cols, var_name="Metric", value_name="Score")
        heat_long = heat_long.dropna(subset=["Score"])
        if not heat_long.empty:
            st.markdown("#### Regimen efficacy profile (normalized heatmap)")
            heatmap = (
                alt.Chart(heat_long)
                .mark_rect()
                .encode(
                    x=alt.X("Metric:N", title="Metric"),
                    y=alt.Y("Arm:N", title="Arm"),
                    color=alt.Color("Score:Q", title="Relative score", scale=alt.Scale(scheme="teals")),
                    tooltip=["Trial (NCT)", "Arm", "Metric", alt.Tooltip("Score:Q", format=".2f")],
                )
                .properties(height=320)
            )
            st.altair_chart(heatmap, use_container_width=True)

    if has_eff and has_saf:
        merged = pd.merge(
            df_eff,
            df_saf[["Trial (NCT)", "Arm", "Serious AE %", "Any AE %", "AE leading to discontinuation %"]],
            on=["Trial (NCT)", "Arm"],
            how="inner",
        )
        merged["ORR %"] = pd.to_numeric(merged["ORR %"], errors="coerce")
        merged["Serious AE %"] = pd.to_numeric(merged["Serious AE %"], errors="coerce")
        merged["Any AE %"] = pd.to_numeric(merged["Any AE %"], errors="coerce")
        merged["PFS median"] = pd.to_numeric(merged["PFS median"], errors="coerce")
        tradeoff_df = merged.dropna(subset=["ORR %", "Serious AE %"])
        if not tradeoff_df.empty:
            st.markdown("#### Efficacy-safety tradeoff")
            bubble = (
                alt.Chart(tradeoff_df)
                .mark_circle(opacity=0.75)
                .encode(
                    x=alt.X("Serious AE %:Q", title="Serious AE % (lower is better)"),
                    y=alt.Y("ORR %:Q", title="ORR % (higher is better)"),
                    size=alt.Size("PFS median:Q", title="PFS median", scale=alt.Scale(range=[70, 900])),
                    color=alt.Color("Arm:N", title="Arm"),
                    tooltip=[
                        "Trial (NCT)",
                        "Arm",
                        "ORR %",
                        "Serious AE %",
                        "Any AE %",
                        "PFS median",
                    ],
                )
                .properties(height=380)
            )
            st.altair_chart(bubble, use_container_width=True)

    st.caption("These charts are intentionally curated to highlight meaningful efficacy and safety comparisons.")


st.set_page_config(page_title="Oncology Trial Analytics POC", layout="wide")

st.title("Oncology Trial Analytics POC")

mapped_file = find_latest_mapped_drug_file()
mapped_df: pd.DataFrame | None = None
if mapped_file is not None:
    try:
        candidate_df = pd.read_csv(mapped_file, low_memory=False)
        required_cols = {"primary_cancer_type", "generic_name", "ncts"}
        if required_cols.issubset(set(candidate_df.columns)):
            mapped_df = candidate_df
    except Exception:  # noqa: BLE001
        mapped_df = None

# Try to load auto-discovered mapping from cancer type -> drug -> [NCT IDs].
mapping_path = Path("cancer_drug_nct_mapping.json")
cancer_mapping: Dict[str, Dict[str, List[str]]] = {}
if mapping_path.exists():
    with mapping_path.open("r", encoding="utf-8") as f:
        cancer_mapping = json.load(f)

if mapped_df is not None:
    primary_mapping = build_primary_cancer_drug_mapping(mapped_df)
    if not primary_mapping:
        st.warning(
            f"Mapped file found ({mapped_file.name}) but no rows have both generic drug name and NCT IDs."
        )
    else:
        st.write(
            f"Using mapped drug file: {mapped_file.name}. Select a primary cancer type, then compare exactly two drugs "
            "from the same cancer type across efficacy/safety metrics."
        )

        cancer_types = sorted(primary_mapping.keys())
        selected_cancer_type = st.selectbox("Primary cancer type", cancer_types)

        drugs_for_cancer = primary_mapping.get(selected_cancer_type, {})
        drug_options = sorted(drugs_for_cancer.keys())
        selected_drugs = st.multiselect(
            "Select exactly 2 drugs to compare",
            drug_options,
            default=drug_options[:2],
            help="Choose two drugs under this primary cancer type.",
        )

        if st.button("Compare selected drugs"):
            if len(selected_drugs) != 2:
                st.error("Please select exactly 2 drugs for comparison.")
            else:
                nct_to_selected_drugs: Dict[str, List[str]] = {}
                for drug in selected_drugs:
                    for nct in drugs_for_cancer.get(drug, []):
                        nct_to_selected_drugs.setdefault(nct, []).append(drug)

                nct_ids = sorted(nct_to_selected_drugs.keys())

                if not nct_ids:
                    st.error("No NCT IDs found for the selected cancer type and drugs.")
                else:
                    eff_rows: List[Dict[str, Any]] = []
                    saf_rows: List[Dict[str, Any]] = []
                    docs: List[Dict[str, Any]] = []
                    for nct in nct_ids:
                        with st.spinner(f"Fetching {nct} ..."):
                            try:
                                doc = build_trial_document(nct)
                            except Exception as exc:  # noqa: BLE001
                                st.error(f"Error fetching {nct}: {exc}")
                                continue
                        docs.append(doc)
                        eff_rows.extend(efficacy_rows(doc))
                        saf_rows.extend(safety_rows(doc))

                    if not eff_rows and not saf_rows:
                        st.warning("No metrics available to display.")
                    else:
                        df_eff_all = pd.DataFrame(eff_rows) if eff_rows else None
                        df_saf_all = pd.DataFrame(saf_rows) if saf_rows else None

                        def nct_drug_label(nct: Any) -> str:
                            if nct is None:
                                return ""
                            names = nct_to_selected_drugs.get(str(nct), [])
                            return " | ".join(sorted(set(names)))

                        if df_eff_all is not None and not df_eff_all.empty and "Trial (NCT)" in df_eff_all.columns:
                            df_eff_all["Selected Drug(s)"] = df_eff_all["Trial (NCT)"].apply(nct_drug_label)
                        if df_saf_all is not None and not df_saf_all.empty and "Trial (NCT)" in df_saf_all.columns:
                            df_saf_all["Selected Drug(s)"] = df_saf_all["Trial (NCT)"].apply(nct_drug_label)

                        def arm_mentions_selected(arm_value: Any) -> bool:
                            arm_text = str(arm_value or "").lower()
                            return any(drug.lower() in arm_text for drug in selected_drugs)

                        if df_eff_all is not None and not df_eff_all.empty and "Arm" in df_eff_all.columns:
                            df_eff_all["Arm matches selected drugs"] = df_eff_all["Arm"].apply(arm_mentions_selected)
                        if df_saf_all is not None and not df_saf_all.empty and "Arm" in df_saf_all.columns:
                            df_saf_all["Arm matches selected drugs"] = df_saf_all["Arm"].apply(arm_mentions_selected)

                        st.markdown("### Filters (selected cancer type and trial arms)")
                        st.caption(
                            f"Primary cancer type: {selected_cancer_type} | Drugs: {selected_drugs[0]} vs {selected_drugs[1]}"
                        )
                        include_all_arms = st.checkbox(
                            "Include non-matching trial arms (e.g., control/placebo)",
                            value=False,
                            help="When unchecked, tables/charts prioritize arms whose label mentions one of the selected drugs.",
                        )

                        selected_arms: List[str] = []
                        if df_eff_all is not None and not df_eff_all.empty:
                            if not include_all_arms and "Arm matches selected drugs" in df_eff_all.columns:
                                filtered_eff_for_options = df_eff_all[df_eff_all["Arm matches selected drugs"]]
                            else:
                                filtered_eff_for_options = df_eff_all

                            if filtered_eff_for_options.empty:
                                filtered_eff_for_options = df_eff_all

                            arm_options = sorted(filtered_eff_for_options["Arm"].dropna().unique())
                            if arm_options:
                                selected_arms = st.multiselect(
                                    "Trial arms to display",
                                    arm_options,
                                    default=arm_options,
                                    help="Optional arm-level filter after selecting the two drugs.",
                                )

                        tab_eff, tab_saf, tab_pubs, tab_viz = st.tabs(["Efficacy", "Safety", "Publications", "Visualizations"])

                        if eff_rows:
                            with tab_eff:
                                st.subheader("Efficacy metrics per drug/arm")
                                df_eff = df_eff_all.copy()
                                if not include_all_arms and "Arm matches selected drugs" in df_eff.columns:
                                    df_eff = df_eff[df_eff["Arm matches selected drugs"]]
                                if selected_arms:
                                    df_eff = df_eff[df_eff["Arm"].isin(selected_arms)]
                                sort_cols = [c for c in ["Selected Drug(s)", "Trial (NCT)", "Arm"] if c in df_eff.columns]
                                if sort_cols:
                                    df_eff = df_eff.sort_values(sort_cols)
                                st.dataframe(df_eff, use_container_width=True)
                        else:
                            with tab_eff:
                                st.info("No efficacy metrics available for these NCT IDs.")

                        if saf_rows:
                            with tab_saf:
                                st.subheader("Safety metrics per drug/arm")
                                df_saf = df_saf_all.copy()
                                if not include_all_arms and "Arm matches selected drugs" in df_saf.columns:
                                    df_saf = df_saf[df_saf["Arm matches selected drugs"]]
                                if selected_arms and "Arm" in df_saf.columns:
                                    df_saf = df_saf[df_saf["Arm"].isin(selected_arms)]
                                sort_cols = [c for c in ["Selected Drug(s)", "Trial (NCT)", "Arm"] if c in df_saf.columns]
                                if sort_cols:
                                    df_saf = df_saf.sort_values(sort_cols)
                                st.dataframe(df_saf, use_container_width=True)
                        else:
                            with tab_saf:
                                st.info("No safety metrics available for these NCT IDs.")

                        with tab_pubs:
                            st.subheader("PubMed publications by NCT")
                            unique_ncts = sorted({doc.get("nct_id") for doc in docs if doc.get("nct_id")})
                            if not unique_ncts:
                                st.info("No NCT IDs available to query PubMed.")
                            else:
                                email, api_key = get_ncbi_credentials()
                                if not email:
                                    st.info(
                                        "Set NCBI_EMAIL / NCBI_API_KEY via environment variables or "
                                        ".streamlit/secrets.toml to enable PubMed primary/non-primary classification."
                                    )
                                else:
                                    with st.spinner("Indexing PubMed articles for these NCT IDs ..."):
                                        try:
                                            df_pubs = index_pubmed_for_ncts(unique_ncts, email=email, api_key=api_key)
                                        except Exception as exc:  # noqa: BLE001
                                            df_pubs = pd.DataFrame()
                                            st.error(f"Error querying PubMed: {exc}")

                                    if df_pubs is None or df_pubs.empty:
                                        st.info("No PubMed articles found for these NCT IDs.")
                                    else:
                                        cols = [
                                            "NCT Number",
                                            "PMID",
                                            "Date",
                                            "Journal",
                                            "Title",
                                            "Label",
                                            "Matched Keywords",
                                            "Match Source",
                                        ]
                                        existing_cols = [c for c in cols if c in df_pubs.columns]
                                        st.dataframe(df_pubs[existing_cols], use_container_width=True)

                        with tab_viz:
                            df_eff_viz = df_eff_all.copy() if df_eff_all is not None else None
                            df_saf_viz = df_saf_all.copy() if df_saf_all is not None else None
                            if not include_all_arms:
                                if df_eff_viz is not None and "Arm matches selected drugs" in df_eff_viz.columns:
                                    df_eff_viz = df_eff_viz[df_eff_viz["Arm matches selected drugs"]]
                                if df_saf_viz is not None and "Arm matches selected drugs" in df_saf_viz.columns:
                                    df_saf_viz = df_saf_viz[df_saf_viz["Arm matches selected drugs"]]
                            if selected_arms:
                                if df_eff_viz is not None and "Arm" in df_eff_viz.columns:
                                    df_eff_viz = df_eff_viz[df_eff_viz["Arm"].isin(selected_arms)]
                                if df_saf_viz is not None and "Arm" in df_saf_viz.columns:
                                    df_saf_viz = df_saf_viz[df_saf_viz["Arm"].isin(selected_arms)]
                            render_visualizations(df_eff_viz, df_saf_viz)

                        with st.expander("Raw trial documents (debug)"):
                            st.json(docs)

elif cancer_mapping:
    st.write(
        "Select a cancer type and drugs to compare. The app will look up "
        "their NCT IDs from ClinicalTrials.gov and fetch metrics automatically."
    )

    cancer_types = sorted(cancer_mapping.keys())
    selected_cancer = st.selectbox("Cancer type", cancer_types)

    drugs_for_cancer = cancer_mapping.get(selected_cancer, {})
    drug_options = sorted(drugs_for_cancer.keys())
    selected_drugs = st.multiselect(
        "Drugs / regimens to compare",
        drug_options,
        default=drug_options[:2],
        help="Pick 2–3 drugs for this cancer type.",
    )

    if st.button("Fetch metrics"):
        nct_ids: List[str] = []
        for drug in selected_drugs:
            nct_ids.extend(drugs_for_cancer.get(drug, []))
        # De-duplicate
        nct_ids = sorted(set(nct_ids))

        if not nct_ids:
            st.error("No NCT IDs found for the selected cancer type and drugs.")
        else:
            eff_rows: List[Dict[str, Any]] = []
            saf_rows: List[Dict[str, Any]] = []
            docs: List[Dict[str, Any]] = []
            for nct in nct_ids:
                with st.spinner(f"Fetching {nct} ..."):
                    try:
                        doc = build_trial_document(nct)
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Error fetching {nct}: {exc}")
                        continue
                docs.append(doc)
                eff_rows.extend(efficacy_rows(doc))
                saf_rows.extend(safety_rows(doc))

        if not eff_rows and not saf_rows:
            st.warning("No metrics available to display.")
        else:
            # Build DataFrames once
            df_eff_all = pd.DataFrame(eff_rows) if eff_rows else None
            df_saf_all = pd.DataFrame(saf_rows) if saf_rows else None

            # Filters by arm/drug only; cancer type is already selected above.
            st.markdown("### Filters (drugs / arms)")

            selected_arms: List[str] = []
            if df_eff_all is not None and not df_eff_all.empty:
                arm_options = sorted(df_eff_all["Arm"].dropna().unique())
                if arm_options:
                    selected_arms = st.multiselect(
                        "Drugs / arms to display",
                        arm_options,
                        default=arm_options,
                        help="Pick which trial arms to show in the tables.",
                    )

            tab_eff, tab_saf, tab_pubs, tab_viz = st.tabs(["Efficacy", "Safety", "Publications", "Visualizations"])

            if eff_rows:
                with tab_eff:
                    st.subheader("Efficacy metrics per drug/arm")
                    df_eff = df_eff_all.copy()
                    if selected_arms:
                        df_eff = df_eff[df_eff["Arm"].isin(selected_arms)]
                    st.dataframe(df_eff, use_container_width=True)
                    st.caption(
                        "Overall Survival (OS) and Progression-free Survival (PFS) are shown as median "
                        "time with a 95% confidence interval (low, high) and N per arm. ORR is the "
                        "overall response rate percentage if reported. Use the filters above to "
                        "compare two drugs within the same cancer type."
                    )
            else:
                with tab_eff:
                    st.info("No efficacy metrics available for these NCT IDs.")

            if saf_rows:
                with tab_saf:
                    st.subheader("Safety metrics per drug/arm")
                    df_saf = df_saf_all.copy()
                    if selected_arms and "Arm" in df_saf.columns:
                        df_saf = df_saf[df_saf["Arm"].isin(selected_arms)]
                    st.dataframe(df_saf, use_container_width=True)
                    st.caption(
                        "Safety tab summarizes the percentage of patients with any adverse event (AE), "
                        "serious AEs, and AEs leading to treatment discontinuation per arm, filtered "
                        "by cancer type and selected drugs above."
                    )
            else:
                with tab_saf:
                    st.info("No safety metrics available for these NCT IDs.")

            # Publications tab: show PubMed articles and primary/subtype labels per NCT
            with tab_pubs:
                st.subheader("PubMed publications by NCT")
                unique_ncts = sorted({doc.get("nct_id") for doc in docs if doc.get("nct_id")})
                if not unique_ncts:
                    st.info("No NCT IDs available to query PubMed.")
                else:
                    email, api_key = get_ncbi_credentials()
                    if not email:
                        st.info(
                            "Set NCBI_EMAIL / NCBI_API_KEY via environment variables or "
                            ".streamlit/secrets.toml to enable PubMed primary/non-primary classification."
                        )
                    else:
                        with st.spinner("Indexing PubMed articles for these NCT IDs ..."):
                            try:
                                df_pubs = index_pubmed_for_ncts(unique_ncts, email=email, api_key=api_key)
                            except Exception as exc:  # noqa: BLE001
                                df_pubs = pd.DataFrame()
                                st.error(f"Error querying PubMed: {exc}")

                        if df_pubs is None or df_pubs.empty:
                            st.info("No PubMed articles found for these NCT IDs.")
                        else:
                            # Keep the most relevant columns for the UI
                            cols = [
                                "NCT Number",
                                "PMID",
                                "Date",
                                "Journal",
                                "Title",
                                "Label",
                                "Matched Keywords",
                                "Match Source",
                            ]
                            existing_cols = [c for c in cols if c in df_pubs.columns]
                            st.dataframe(df_pubs[existing_cols], use_container_width=True)

                            st.caption(
                                "Each NCT can have multiple PubMed articles. One is tagged as 'Primary' "
                                "(earliest non-review). Others are labeled by subtype (Interim, Final, "
                                "Subgroup, QOL, etc.) based on title/abstract keywords."
                            )

            with tab_viz:
                df_eff_viz = df_eff_all.copy() if df_eff_all is not None else None
                df_saf_viz = df_saf_all.copy() if df_saf_all is not None else None
                if selected_arms:
                    if df_eff_viz is not None and "Arm" in df_eff_viz.columns:
                        df_eff_viz = df_eff_viz[df_eff_viz["Arm"].isin(selected_arms)]
                    if df_saf_viz is not None and "Arm" in df_saf_viz.columns:
                        df_saf_viz = df_saf_viz[df_saf_viz["Arm"].isin(selected_arms)]
                render_visualizations(df_eff_viz, df_saf_viz)

            # Optional: show raw JSON for debugging / exploration
            with st.expander("Raw trial documents (debug)"):
                st.json(docs)
else:
    # Fallback: manual NCT input if mapping file is not present.
    st.write(
        "Mapping file 'cancer_drug_nct_mapping.json' not found. "
        "You can still test by entering NCT IDs manually."
    )

    nct_input = st.text_input(
        "NCT IDs (comma-separated)",
        value="NCT01607957",
        help="Example: NCT01607957, NCT01234567",
    )

    if st.button("Fetch metrics"):
        nct_ids = [x.strip().upper() for x in nct_input.split(",") if x.strip()]
        if not nct_ids:
            st.error("Please enter at least one NCT ID.")
        else:
            eff_rows: List[Dict[str, Any]] = []
            saf_rows: List[Dict[str, Any]] = []
            docs: List[Dict[str, Any]] = []
            for nct in nct_ids:
                if not nct.startswith("NCT"):
                    st.warning(f"Skipping invalid NCT ID: {nct}")
                    continue
                with st.spinner(f"Fetching {nct} ..."):
                    try:
                        doc = build_trial_document(nct)
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Error fetching {nct}: {exc}")
                        continue
                docs.append(doc)
                eff_rows.extend(efficacy_rows(doc))
                saf_rows.extend(safety_rows(doc))

            if not eff_rows and not saf_rows:
                st.warning("No metrics available to display.")
            else:
                df_eff_all = pd.DataFrame(eff_rows) if eff_rows else None
                df_saf_all = pd.DataFrame(saf_rows) if saf_rows else None

                st.markdown("### Filters (cancer type and drugs)")

                selected_condition = None
                selected_arms: List[str] = []

                if df_eff_all is not None and not df_eff_all.empty:
                    cond_options = sorted(df_eff_all["Condition"].dropna().unique())
                    if cond_options:
                        selected_condition = st.selectbox(
                            "Cancer type", cond_options, help="Trials will be filtered to this cancer type."
                        )

                    arm_options = sorted(df_eff_all["Arm"].dropna().unique())
                    if arm_options:
                        selected_arms = st.multiselect(
                            "Drugs / arms to compare",
                            arm_options,
                            default=arm_options,
                            help="Pick the regimens (arms) you want to compare within this cancer type.",
                        )

                tab_eff, tab_saf, tab_pubs, tab_viz = st.tabs(["Efficacy", "Safety", "Publications", "Visualizations"])

                if eff_rows:
                    with tab_eff:
                        st.subheader("Efficacy metrics per drug/arm")
                        df_eff = df_eff_all.copy()
                        if selected_condition is not None:
                            df_eff = df_eff[df_eff["Condition"] == selected_condition]
                        if selected_arms:
                            df_eff = df_eff[df_eff["Arm"].isin(selected_arms)]
                        st.dataframe(df_eff, use_container_width=True)
                else:
                    with tab_eff:
                        st.info("No efficacy metrics available for these NCT IDs.")

                if saf_rows:
                    with tab_saf:
                        st.subheader("Safety metrics per drug/arm")
                        df_saf = df_saf_all.copy()
                        if selected_condition is not None and "Condition" in df_saf.columns:
                            df_saf = df_saf[df_saf["Condition"] == selected_condition]
                        if selected_arms and "Arm" in df_saf.columns:
                            df_saf = df_saf[df_saf["Arm"].isin(selected_arms)]
                        st.dataframe(df_saf, use_container_width=True)
                else:
                    with tab_saf:
                        st.info("No safety metrics available for these NCT IDs.")

                # Publications tab for manual NCT mode
                with tab_pubs:
                    st.subheader("PubMed publications by NCT")
                    unique_ncts = sorted({doc.get("nct_id") for doc in docs if doc.get("nct_id")})
                    if not unique_ncts:
                        st.info("No NCT IDs available to query PubMed.")
                    else:
                        email, api_key = get_ncbi_credentials()
                        if not email:
                            st.info(
                                "Set NCBI_EMAIL / NCBI_API_KEY via environment variables or "
                                ".streamlit/secrets.toml to enable PubMed primary/non-primary classification."
                            )
                        else:
                            with st.spinner("Indexing PubMed articles for these NCT IDs ..."):
                                try:
                                    df_pubs = index_pubmed_for_ncts(unique_ncts, email=email, api_key=api_key)
                                except Exception as exc:  # noqa: BLE001
                                    df_pubs = pd.DataFrame()
                                    st.error(f"Error querying PubMed: {exc}")

                            if df_pubs is None or df_pubs.empty:
                                st.info("No PubMed articles found for these NCT IDs.")
                            else:
                                cols = [
                                    "NCT Number",
                                    "PMID",
                                    "Date",
                                    "Journal",
                                    "Title",
                                    "Label",
                                    "Matched Keywords",
                                    "Match Source",
                                ]
                                existing_cols = [c for c in cols if c in df_pubs.columns]
                                st.dataframe(df_pubs[existing_cols], use_container_width=True)

                                st.caption(
                                    "Each NCT can have multiple PubMed articles. One is tagged as 'Primary' "
                                    "(earliest non-review). Others are labeled by subtype (Interim, Final, "
                                    "Subgroup, QOL, etc.) based on title/abstract keywords."
                                )

                with tab_viz:
                    df_eff_viz = df_eff_all.copy() if df_eff_all is not None else None
                    df_saf_viz = df_saf_all.copy() if df_saf_all is not None else None
                    if selected_condition is not None:
                        if df_eff_viz is not None and "Condition" in df_eff_viz.columns:
                            df_eff_viz = df_eff_viz[df_eff_viz["Condition"] == selected_condition]
                        if df_saf_viz is not None and "Condition" in df_saf_viz.columns:
                            df_saf_viz = df_saf_viz[df_saf_viz["Condition"] == selected_condition]
                    if selected_arms:
                        if df_eff_viz is not None and "Arm" in df_eff_viz.columns:
                            df_eff_viz = df_eff_viz[df_eff_viz["Arm"].isin(selected_arms)]
                        if df_saf_viz is not None and "Arm" in df_saf_viz.columns:
                            df_saf_viz = df_saf_viz[df_saf_viz["Arm"].isin(selected_arms)]
                    render_visualizations(df_eff_viz, df_saf_viz)

                with st.expander("Raw trial documents (debug)"):
                    st.json(docs)
