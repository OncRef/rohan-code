import json
import subprocess
import sys
from pathlib import Path
from typing import Tuple

import altair as alt
import pandas as pd
import streamlit as st

OUTPUT_DIR = Path("liver_pipeline_outputs")
MANIFEST_PATH = OUTPUT_DIR / "liver_latest_manifest.json"


def load_latest_data() -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    if not MANIFEST_PATH.exists():
        return pd.DataFrame(), pd.DataFrame(), {}

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    eff_path = Path(manifest.get("efficacy_csv", ""))
    saf_path = Path(manifest.get("safety_csv", ""))

    df_eff = pd.read_csv(eff_path) if eff_path.exists() else pd.DataFrame()
    df_saf = pd.read_csv(saf_path) if saf_path.exists() else pd.DataFrame()
    return df_eff, df_saf, manifest


def to_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def classify_liver_subtype(condition_text: str) -> str:
    text = str(condition_text or "").lower()
    if "hepatocellular" in text or " hcc" in text:
        return "Hepatocellular carcinoma"
    if "cholangiocarcinoma" in text or "biliary" in text:
        return "Cholangiocarcinoma / biliary"
    if "metast" in text:
        return "Liver metastases"
    if "transplant" in text:
        return "Transplant-related"
    if "cirrhosis" in text or "steatosis" in text or "fatty liver" in text:
        return "Cirrhosis / fatty liver"
    if "hepatoblastoma" in text:
        return "Hepatoblastoma"
    return "Other liver"


def render_kpis(df_eff: pd.DataFrame, df_saf: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Trials", int(df_eff["Trial (NCT)"].nunique()) if not df_eff.empty else 0)
    with c2:
        st.metric("Arms", int(df_eff["Arm"].nunique()) if not df_eff.empty else 0)
    with c3:
        med_os = df_eff["OS median"].median(skipna=True) if "OS median" in df_eff.columns else None
        st.metric("Median OS", f"{med_os:.2f}" if pd.notna(med_os) else "NA")
    with c4:
        med_ae = df_saf["Serious AE %"].median(skipna=True) if "Serious AE %" in df_saf.columns else None
        st.metric("Median Serious AE %", f"{med_ae:.1f}%" if pd.notna(med_ae) else "NA")


def render_insights(df_eff: pd.DataFrame, df_saf: pd.DataFrame) -> None:
    st.subheader("Liver Trial Insights")

    if df_eff.empty:
        st.info("No efficacy data found in latest pipeline output.")
        return

    top_orr = (
        df_eff.dropna(subset=["ORR %"])
        .sort_values("ORR %", ascending=False)
        .head(15)
    )
    if not top_orr.empty:
        st.markdown("#### Top ORR arms")
        chart = (
            alt.Chart(top_orr)
            .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
            .encode(
                x=alt.X("ORR %:Q", title="ORR %"),
                y=alt.Y("Arm:N", sort="-x", title="Arm"),
                color=alt.Color("Trial (NCT):N", title="Trial"),
                tooltip=["Trial (NCT)", "Arm", "ORR %", "OS median", "PFS median"],
            )
            .properties(height=420)
        )
        st.altair_chart(chart, use_container_width=True)

    os_pfs = df_eff.dropna(subset=["OS median", "PFS median"]).copy()
    if not os_pfs.empty:
        st.markdown("#### OS vs PFS per arm (dumbbell)")
        os_pfs["ArmTrial"] = os_pfs["Arm"] + " | " + os_pfs["Trial (NCT)"]
        long_df = os_pfs.melt(
            id_vars=["ArmTrial", "Trial (NCT)", "Arm", "ORR %"],
            value_vars=["PFS median", "OS median"],
            var_name="Metric",
            value_name="Median",
        )
        rules = (
            alt.Chart(os_pfs)
            .mark_rule(color="#94a3b8", strokeWidth=2)
            .encode(
                y=alt.Y("ArmTrial:N", title="Arm | Trial"),
                x=alt.X("PFS median:Q", title="Median time"),
                x2="OS median:Q",
                tooltip=["Trial (NCT)", "Arm", "PFS median", "OS median", "ORR %"],
            )
        )
        points = (
            alt.Chart(long_df)
            .mark_circle(size=100)
            .encode(
                y=alt.Y("ArmTrial:N", title="Arm | Trial"),
                x=alt.X("Median:Q", title="Median time"),
                color=alt.Color("Metric:N", scale=alt.Scale(range=["#0f766e", "#b45309"])),
                tooltip=["Trial (NCT)", "Arm", "Metric", "Median", "ORR %"],
            )
        )
        st.altair_chart((rules + points).properties(height=480), use_container_width=True)

    if not df_saf.empty:
        merged = pd.merge(
            df_eff,
            df_saf[["Trial (NCT)", "Arm", "Serious AE %", "Any AE %"]],
            on=["Trial (NCT)", "Arm"],
            how="inner",
        )
        bubble_df = merged.dropna(subset=["ORR %", "Serious AE %", "PFS median"])
        if not bubble_df.empty:
            st.markdown("#### Efficacy-Safety tradeoff")
            bubble = (
                alt.Chart(bubble_df)
                .mark_circle(opacity=0.75)
                .encode(
                    x=alt.X("Serious AE %:Q", title="Serious AE % (lower better)"),
                    y=alt.Y("ORR %:Q", title="ORR % (higher better)"),
                    size=alt.Size("PFS median:Q", scale=alt.Scale(range=[60, 900]), title="PFS median"),
                    color=alt.Color("Arm:N", title="Arm"),
                    tooltip=["Trial (NCT)", "Arm", "ORR %", "Serious AE %", "Any AE %", "PFS median"],
                )
                .properties(height=420)
            )
            st.altair_chart(bubble, use_container_width=True)

    # Trial duration chart: start date to completion date
    if "Trial start date" in df_eff.columns and "Trial completion date" in df_eff.columns:
        duration_df = df_eff[["Trial (NCT)", "Trial start date", "Trial completion date"]].drop_duplicates().copy()
        duration_df["Trial start date"] = pd.to_datetime(duration_df["Trial start date"], errors="coerce")
        duration_df["Trial completion date"] = pd.to_datetime(duration_df["Trial completion date"], errors="coerce")
        duration_df = duration_df.dropna(subset=["Trial start date", "Trial completion date"])
        duration_df = duration_df[duration_df["Trial completion date"] >= duration_df["Trial start date"]]
        if not duration_df.empty:
            duration_df["Duration (months)"] = (
                (duration_df["Trial completion date"] - duration_df["Trial start date"]).dt.days / 30.44
            )
            duration_df = duration_df.sort_values("Duration (months)", ascending=False).head(40)

            st.markdown("#### Trial duration (start to completion)")
            duration_chart = (
                alt.Chart(duration_df)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("Duration (months):Q", title="Duration (months)"),
                    y=alt.Y("Trial (NCT):N", sort="-x", title="Trial (NCT)"),
                    color=alt.Color("Duration (months):Q", title="Duration", scale=alt.Scale(scheme="goldgreen")),
                    tooltip=["Trial (NCT)", "Trial start date", "Trial completion date", alt.Tooltip("Duration (months):Q", format=".1f")],
                )
                .properties(height=500)
            )
            st.altair_chart(duration_chart, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Liver NCT Comparison Pipeline", layout="wide")
    st.title("Liver Cancer NCT Comparison Pipeline")
    st.caption("Standalone POC: separate from existing app/code paths.")

    with st.sidebar:
        st.markdown("### Pipeline")
        run_mode = st.radio("Run mode", ["Capped", "All available"], index=0)
        max_trials = st.slider("Max liver trials", min_value=20, max_value=5000, value=300, step=20)
        if run_mode == "All available":
            st.caption("All available mode passes --max-trials 0 to the pipeline.")
        if st.button("Run / Refresh Liver Pipeline"):
            max_trials_arg = 0 if run_mode == "All available" else max_trials
            cmd = [
                sys.executable,
                "liver_nct_pipeline.py",
                "--max-trials",
                str(max_trials_arg),
                "--out-dir",
                str(OUTPUT_DIR),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                st.success("Pipeline completed.")
            else:
                st.error("Pipeline failed.")
                st.code(result.stderr or result.stdout)

    df_eff, df_saf, manifest = load_latest_data()

    if not manifest:
        st.info("No liver pipeline output found yet. Use sidebar button: Run / Refresh Liver Pipeline.")
        return

    st.markdown("### Latest Run")
    st.json(manifest)

    df_eff = to_numeric(df_eff, ["OS median", "PFS median", "ORR %", "OS N", "PFS N"])
    df_saf = to_numeric(df_saf, ["Any AE %", "Serious AE %", "AE leading to discontinuation %"])

    if "Condition" in df_eff.columns:
        df_eff["Liver subtype"] = df_eff["Condition"].fillna("").apply(classify_liver_subtype)
    if "Condition" in df_saf.columns:
        df_saf["Liver subtype"] = df_saf["Condition"].fillna("").apply(classify_liver_subtype)

    subtype_options = ["All"]
    if "Liver subtype" in df_eff.columns:
        subtype_options += sorted(df_eff["Liver subtype"].dropna().unique().tolist())
    selected_subtype = st.selectbox("Filter by liver subtype", subtype_options)

    if selected_subtype != "All":
        if "Liver subtype" in df_eff.columns:
            df_eff = df_eff[df_eff["Liver subtype"] == selected_subtype]
        if "Liver subtype" in df_saf.columns:
            df_saf = df_saf[df_saf["Liver subtype"] == selected_subtype]

    render_kpis(df_eff, df_saf)

    tab_eff, tab_saf, tab_insights = st.tabs(["Efficacy Table", "Safety Table", "Insights"])

    with tab_eff:
        st.dataframe(df_eff, use_container_width=True)

    with tab_saf:
        st.dataframe(df_saf, use_container_width=True)

    with tab_insights:
        render_insights(df_eff, df_saf)


if __name__ == "__main__":
    main()
