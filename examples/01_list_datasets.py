"""
Example 1: List all available datasets on the ONS API.

This script fetches every dataset from the API (handling pagination)
and saves a summary to a CSV file. Run this first to see what data
is available.

Usage:
    python examples/01_list_datasets.py
"""

import requests
import pandas as pd
from pathlib import Path

ROOT_URL = "https://api.beta.ons.gov.uk/v1/"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def get_all_datasets():
    """
    Fetch metadata for every dataset on the ONS API.

    The API returns results in pages, so we loop through pages
    until we've collected them all.
    """
    datasets = []
    offset = 0
    limit = 50  # max items per page

    print("Fetching dataset catalogue from the ONS API...\n")

    while True:
        response = requests.get(
            ROOT_URL + "datasets",
            params={"offset": offset, "limit": limit},
        )
        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        if not items:
            break  # no more pages

        datasets.extend(items)
        offset += len(items)

    print(f"Found {len(datasets)} datasets.\n")
    return datasets


def summarise(datasets):
    """Turn the raw JSON into a clean table."""
    rows = []
    for ds in datasets:
        rows.append({
            "id": ds.get("id", ""),
            "title": ds.get("title", ""),
            "description": ds.get("description", "")[:200],
            "publisher": ds.get("publisher", {}).get("name", ""),
            "keywords": ", ".join(ds.get("keywords", [])),
        })
    return pd.DataFrame(rows)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = get_all_datasets()
    df = summarise(datasets)

    # Print to console
    print(f"{'ID':<45} Title")
    print("-" * 100)
    for _, row in df.iterrows():
        print(f"{row['id']:<45} {row['title']}")

    # Save to CSV
    output_path = OUTPUT_DIR / "dataset_catalogue.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
