"""
Example 4: Batch download multiple ONS time series.

This script shows how to define a collection of series and download
them all at once, saving each to its own CSV file plus a metadata
summary. This is useful for building a personal data library or
an automated pipeline.

Usage:
    python examples/04_batch_download.py
"""

import requests
import time
import re
import pandas as pd
from pathlib import Path

ROOT_URL = "https://api.beta.ons.gov.uk/v1/"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


# -----------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------

def get_json(url, params=None, retries=3):
    """Make a GET request with retries. Returns parsed JSON or None."""
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # wait 1s, 2s, 4s...
            else:
                print(f"  FAILED after {retries} attempts: {e}")
                return None


def label_to_filename(label):
    """Convert a human label like 'GDP growth (QoQ)' to 'gdp_growth_qoq'."""
    s = label.lower()
    s = s.replace("%", "pct").replace("&", "and").replace("/", "_")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def get_edition_url(dataset_id, preferred_edition="time-series"):
    """Resolve the latest version URL for a dataset edition."""
    data = get_json(ROOT_URL + f"datasets/{dataset_id}")
    if not data:
        return None

    fallback = data.get("links", {}).get("latest_version", {}).get("href")

    editions_url = data.get("links", {}).get("editions", {}).get("href")
    if not editions_url:
        return fallback

    editions = get_json(editions_url)
    if not editions:
        return fallback

    for item in editions.get("items", []):
        if item.get("edition") == preferred_edition:
            return item.get("links", {}).get("latest_version", {}).get("href")

    return fallback


def get_observations(edition_url, dimensions):
    """Fetch observations and return a sorted DataFrame."""
    data = get_json(edition_url + "/observations", params=dimensions)
    if not data:
        return pd.DataFrame()

    rows = []
    for obs in data.get("observations", []):
        time_dim = (
            obs.get("dimensions", {}).get("Time")
            or obs.get("dimensions", {}).get("time")
        )
        if not time_dim:
            continue
        rows.append({
            "period": time_dim.get("id", ""),
            "period_label": time_dim.get("label", ""),
            "value": obs.get("observation"),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        # Sort chronologically
        def parse_period(s):
            try:
                return pd.to_datetime(s, format="%b-%y")
            except Exception:
                pass
            try:
                return pd.to_datetime(s, format="mixed", dayfirst=False)
            except Exception:
                return pd.NaT

        parsed = df["period_label"].apply(parse_period)
        if parsed.notna().any():
            df = df.assign(_sort=parsed).sort_values("_sort").drop(columns="_sort")
        else:
            df = df.sort_values("period")
        df = df.reset_index(drop=True)

    return df


# -----------------------------------------------------------------------
# Define the series you want to download
# -----------------------------------------------------------------------
# Each entry is a tuple of:
#   (dataset_id, human_label, dimension_overrides, edition_or_None)
#
# - dimension_overrides: the values for each dimension (time is always "*")
# - edition: which edition to use. None means "time-series" (the default).
#   Some datasets like labour-market use numbered editions (e.g. "PWT24").
#
# To find valid dimension values for a dataset, run:
#   python examples/02_explore_dimensions.py
# -----------------------------------------------------------------------

SERIES = [
    # --- Monthly GDP (current on the API) ---
    ("gdp-to-four-decimal-places", "Monthly GDP index - all sectors", {
        "geography": "K02000001",
        "unofficialstandardindustrialclassification": "A--T",
    }, None),

    ("gdp-to-four-decimal-places", "Monthly GDP index - services", {
        "geography": "K02000001",
        "unofficialstandardindustrialclassification": "G--T",
    }, None),

    ("gdp-to-four-decimal-places", "Monthly GDP index - production", {
        "geography": "K02000001",
        "unofficialstandardindustrialclassification": "B--E",
    }, None),

    # --- Trade (current on the API) ---
    ("trade", "UK total exports", {
        "countriesandterritories": "W1",
        "direction": "EX",
        "geography": "K02000001",
        "standardindustrialtradeclassification": "T",
    }, None),

    ("trade", "UK total imports", {
        "countriesandterritories": "W1",
        "direction": "IM",
        "geography": "K02000001",
        "standardindustrialtradeclassification": "T",
    }, None),

    ("trade", "UK exports to EU", {
        "countriesandterritories": "B5",
        "direction": "EX",
        "geography": "K02000001",
        "standardindustrialtradeclassification": "T",
    }, None),

    ("trade", "UK imports from EU", {
        "countriesandterritories": "B5",
        "direction": "IM",
        "geography": "K02000001",
        "standardindustrialtradeclassification": "T",
    }, None),

    # --- Labour Market (uses PWT24 edition; note: can lag by months) ---
    ("labour-market", "Employment rate 16+ SA", {
        "economicactivity": "in-employment",
        "agegroups": "16+",
        "seasonaladjustment": "seasonal-adjustment",
        "sex": "all-adults",
        "unitofmeasure": "rates",
        "geography": "K02000001",
    }, "PWT24"),

    ("labour-market", "Unemployment rate 16+ SA", {
        "economicactivity": "unemployed",
        "agegroups": "16+",
        "seasonaladjustment": "seasonal-adjustment",
        "sex": "all-adults",
        "unitofmeasure": "rates",
        "geography": "K02000001",
    }, "PWT24"),
]


# -----------------------------------------------------------------------
# Main download loop
# -----------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    metadata = []
    errors = []
    edition_cache = {}

    print(f"Downloading {len(SERIES)} ONS series...\n")

    for i, (dataset_id, label, overrides, edition) in enumerate(SERIES, 1):
        print(f"  [{i:2d}/{len(SERIES)}] {label}...", end=" ")

        try:
            # Resolve edition URL (cached to avoid repeated lookups)
            cache_key = (dataset_id, edition or "time-series")
            if cache_key not in edition_cache:
                url = get_edition_url(dataset_id, edition or "time-series")
                if not url:
                    raise ValueError(f"Could not resolve edition for '{dataset_id}'")
                edition_cache[cache_key] = url

            edition_url = edition_cache[cache_key]

            # Build query: overrides + time wildcard
            dims = dict(overrides)
            dims["time"] = "*"

            # Download
            df = get_observations(edition_url, dims)
            if df.empty:
                raise ValueError("No observations returned")

            # Save
            fname = label_to_filename(label) + ".csv"
            df.to_csv(OUTPUT_DIR / fname, index=False)
            print(f"OK  ({len(df)} observations)")

            metadata.append({
                "dataset_id": dataset_id,
                "filename": fname,
                "label": label,
                "edition_url": edition_url,
                "obs_count": len(df),
                "period_start": df["period"].iloc[0],
                "period_end": df["period"].iloc[-1],
            })

        except Exception as e:
            errors.append((dataset_id, label, str(e)))
            print(f"FAILED: {e}")

    # Save metadata index
    if metadata:
        meta_df = pd.DataFrame(metadata)
        meta_df.to_csv(OUTPUT_DIR / "_metadata.csv", index=False)

    # Summary
    print(f"\nDone. {len(metadata)} series saved to {OUTPUT_DIR}/")
    if errors:
        print(f"\n{len(errors)} series failed:")
        for ds_id, label, err in errors:
            print(f"  {ds_id}: {label} - {err}")


if __name__ == "__main__":
    main()
