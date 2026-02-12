"""
Example 3: Download a single time series from the ONS API.

This script walks through every step needed to fetch actual data:
  1. Look up the dataset
  2. Resolve the latest version
  3. Request observations with specific dimension values
  4. Parse the response into a pandas DataFrame
  5. Save to CSV

Usage:
    python examples/03_download_timeseries.py

Change DATASET_ID and DIMENSIONS below to fetch different data.
"""

import requests
import pandas as pd
from pathlib import Path

ROOT_URL = "https://api.beta.ons.gov.uk/v1/"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# --- Configuration ---
# What dataset to query
DATASET_ID = "trade"

# Which edition to use (set to None for the default "time-series" edition)
EDITION = None

# Dimension values for our query.
# Every dimension must be specified. Use "*" for time to get the full series.
# Run 02_explore_dimensions.py first to discover valid values.
DIMENSIONS = {
    "time": "*",                                    # full time series
    "geography": "K02000001",                       # United Kingdom
    "countriesandterritories": "W1",                # Whole world
    "direction": "EX",                              # Exports
    "standardindustrialtradeclassification": "T",   # Total, all commodities
}

OUTPUT_FILENAME = "uk_total_exports.csv"


def get_edition_url(dataset_id, preferred_edition="time-series"):
    """
    Resolve the URL for the latest version of a dataset edition.

    Why is this needed? The ONS API doesn't let you query observations
    directly from a dataset ID. You need to find the specific
    edition -> version URL first.
    """
    response = requests.get(ROOT_URL + f"datasets/{dataset_id}")
    response.raise_for_status()
    data = response.json()

    fallback_url = data.get("links", {}).get("latest_version", {}).get("href")

    editions_url = data.get("links", {}).get("editions", {}).get("href")
    if not editions_url:
        return fallback_url

    ed_response = requests.get(editions_url)
    ed_response.raise_for_status()

    for item in ed_response.json().get("items", []):
        if item.get("edition") == preferred_edition:
            return item["links"]["latest_version"]["href"]

    return fallback_url


def download_observations(edition_url, dimensions):
    """
    Fetch observations from the API and return a pandas DataFrame.

    Each observation has:
      - A time period (id and human-readable label)
      - A numeric value
    """
    response = requests.get(edition_url + "/observations", params=dimensions)
    response.raise_for_status()
    data = response.json()

    rows = []
    for obs in data.get("observations", []):
        # The time dimension can be capitalised differently across datasets
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

        # Sort chronologically. ONS uses formats like "Nov-25" (Mon-YY)
        # which need careful parsing to avoid 1925 vs 2025 confusion.
        try:
            parsed = pd.to_datetime(df["period_label"], format="%b-%y")
            df = df.assign(_sort=parsed).sort_values("_sort").drop(columns="_sort")
        except Exception:
            try:
                parsed = pd.to_datetime(df["period_label"], format="mixed", dayfirst=False, errors="coerce")
                if parsed.notna().any():
                    df = df.assign(_sort=parsed).sort_values("_sort").drop(columns="_sort")
                else:
                    df = df.sort_values("period")
            except Exception:
                df = df.sort_values("period")

        df = df.reset_index(drop=True)

    return df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Resolve edition URL
    edition = EDITION or "time-series"
    print(f"Looking up dataset '{DATASET_ID}', edition '{edition}'...")
    edition_url = get_edition_url(DATASET_ID, edition)

    if not edition_url:
        print("ERROR: Could not resolve the edition URL.")
        print("Check the DATASET_ID and EDITION values.")
        return

    print(f"  Version URL: {edition_url}\n")

    # Step 2: Download observations
    print(f"Fetching observations...")
    df = download_observations(edition_url, DIMENSIONS)

    if df.empty:
        print("ERROR: No observations returned.")
        print("Check your DIMENSIONS — every dimension must be specified.")
        return

    # Step 3: Display and save
    print(f"\nGot {len(df)} observations.\n")
    print("First 5 rows:")
    print(df.head().to_string(index=False))
    print(f"\nLast 5 rows:")
    print(df.tail().to_string(index=False))

    output_path = OUTPUT_DIR / OUTPUT_FILENAME
    df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
