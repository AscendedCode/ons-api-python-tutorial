"""
Example 2: Explore the dimensions of any ONS dataset.

Before you can download data, you need to know what dimensions
(filters) a dataset has, and what values are valid for each one.
This script shows you everything you need to know to build a query.

Usage:
    python examples/02_explore_dimensions.py

Change DATASET_ID below to explore a different dataset.
"""

import requests

ROOT_URL = "https://api.beta.ons.gov.uk/v1/"

# Change this to explore a different dataset.
# Some interesting options:
#   "trade"                      - Trade in goods by country & commodity
#   "labour-market"              - Employment, unemployment, inactivity
#   "gdp-to-four-decimal-places" - Monthly GDP estimate
#   "cpih01"                     - Consumer Prices Index (CPIH)
#   "retail-sales-index"         - Retail sales
DATASET_ID = "trade"


def get_latest_version_url(dataset_id):
    """
    Find the URL of the latest version for a dataset.

    Most datasets have a single 'time-series' edition. Some (like
    the labour market) have numbered editions. This function tries
    to find the latest version regardless.
    """
    print(f"Looking up dataset: {dataset_id}")
    response = requests.get(ROOT_URL + f"datasets/{dataset_id}")
    response.raise_for_status()
    data = response.json()

    print(f"  Title: {data.get('title', '?')}")

    # Check what editions exist
    editions_url = data.get("links", {}).get("editions", {}).get("href")
    if editions_url:
        ed_response = requests.get(editions_url)
        ed_response.raise_for_status()
        editions = ed_response.json().get("items", [])

        print(f"  Available editions: {[e.get('edition') for e in editions]}")

        # Prefer 'time-series' if it exists; otherwise take the last one listed
        for edition in editions:
            if edition.get("edition") == "time-series":
                return edition["links"]["latest_version"]["href"]

        # Fall back to the last edition (usually the most recent)
        if editions:
            return editions[-1]["links"]["latest_version"]["href"]

    # Fall back to the direct latest_version link
    return data.get("links", {}).get("latest_version", {}).get("href")


def explore_dimensions(version_url):
    """
    List all dimensions and their valid values for a dataset version.

    This is the key step before downloading data — you need to know
    what values to pass for each dimension.
    """
    print(f"\nVersion URL: {version_url}\n")

    response = requests.get(version_url + "/dimensions")
    response.raise_for_status()
    dimensions = response.json().get("items", [])

    all_dimensions = {}

    for dim in dimensions:
        name = dim.get("name", "")
        label = dim.get("label", name)
        dim_id = dim.get("links", {}).get("options", {}).get("id", name)

        # Fetch all valid options for this dimension
        opts_response = requests.get(
            f"{version_url}/dimensions/{dim_id}/options",
            params={"limit": 200},
        )
        opts_response.raise_for_status()
        opts_data = opts_response.json()

        options = {}
        for item in opts_data.get("items", []):
            options[item.get("option")] = item.get("label", "")

        total = opts_data.get("total_count", len(options))
        all_dimensions[name] = options

        # Print a summary
        print(f"Dimension: {name} ({label})")
        print(f"  {total} valid option(s):")
        for i, (opt_id, opt_label) in enumerate(options.items()):
            if i >= 10:
                print(f"  ... and {total - 10} more")
                break
            print(f"    {opt_id}: {opt_label}")
        print()

    return all_dimensions


def main():
    version_url = get_latest_version_url(DATASET_ID)
    if not version_url:
        print("Could not find a version URL for this dataset.")
        return

    dimensions = explore_dimensions(version_url)

    # Print a template query you could use
    print("=" * 60)
    print("Template query parameters (using first option for each):\n")
    print("params = {")
    for name, options in dimensions.items():
        if name.lower() == "time":
            print(f'    "{name}": "*",  # wildcard = full time series')
        elif options:
            first_key = next(iter(options))
            first_label = options[first_key]
            print(f'    "{name}": "{first_key}",  # {first_label}')
    print("}")


if __name__ == "__main__":
    main()
