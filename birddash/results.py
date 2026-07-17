"""Loading and aggregation of BirdNET result CSVs.

Framework-agnostic data access. The Streamlit layer wraps `load_results` in a
cache; the FastAPI layer will call it directly (or, from Phase 6, this is
replaced by database queries).
"""

import glob
import os

import pandas as pd


def load_results(results_dir) -> pd.DataFrame:
    """Concatenate all per-recording BirdNET result CSVs in a directory.

    Skips the BirdNET analysis-params sidecar and empty files. Returns an
    empty DataFrame if no results are present.
    """
    all_dfs = []
    for f in glob.glob(f"{results_dir}/*.csv"):
        if "params" in os.path.basename(f).lower():
            continue
        df = pd.read_csv(f)
        if len(df) > 0:
            all_dfs.append(df)
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()
