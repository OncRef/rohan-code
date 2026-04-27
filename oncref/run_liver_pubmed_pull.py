import csv
import glob
import os
import subprocess
import sys
from pathlib import Path

import requests


def main() -> None:
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {"query.term": "Liver Neoplasms", "pageSize": 50}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    studies = r.json().get("studies", [])

    ncts = []
    for s in studies:
        nct = ((s.get("protocolSection") or {}).get("identificationModule") or {}).get("nctId")
        if nct and nct not in ncts:
            ncts.append(nct)
        if len(ncts) >= 20:
            break

    with open("NCTs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["NCT"])
        for n in ncts:
            w.writerow([n])

    print(f"Wrote liver NCTs.csv with {len(ncts)} NCT IDs")
    print("Sample:", ncts[:5])

    env = os.environ.copy()
    secrets_path = Path(".streamlit/secrets.toml")
    if secrets_path.exists():
        try:
            import tomllib

            with open(secrets_path, "rb") as f:
                secrets = tomllib.load(f)
            if secrets.get("NCBI_EMAIL"):
                env["NCBI_EMAIL"] = secrets["NCBI_EMAIL"]
            if secrets.get("NCBI_API_KEY"):
                env["NCBI_API_KEY"] = secrets["NCBI_API_KEY"]
            print("Loaded NCBI credentials from .streamlit/secrets.toml")
        except Exception as exc:  # noqa: BLE001
            print(f"Could not read secrets.toml: {exc}")

    subprocess.run([sys.executable, "pubmed_pubs-checker_pull.py"], check=True, env=env)

    files = sorted(glob.glob("nct_pubmed_indexed_*.csv"))
    if files:
        print("LATEST_OUTPUT_FILE:", files[-1])


if __name__ == "__main__":
    main()
