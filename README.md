# A Practical Guide to the UK ONS API in Python

A tutorial for accessing UK economic and social data from the **Office for National Statistics (ONS) API** using Python.

This guide is written for economists, researchers, analysts, and students who want to pull ONS data directly into Python — no web scraping, no manual CSV downloads. It assumes basic Python knowledge but **no software engineering background**.

Created by [@AscendedYield](https://x.com/AscendedYield)

---

## Table of Contents

1. [What Is the ONS API?](#1-what-is-the-ons-api)
2. [Before You Start](#2-before-you-start)
3. [How the API Is Structured](#3-how-the-api-is-structured)
4. [Step-by-Step: Your First API Call](#4-step-by-step-your-first-api-call)
5. [Understanding Dimensions](#5-understanding-dimensions)
6. [Downloading a Time Series](#6-downloading-a-time-series)
7. [Batch Downloading Multiple Series](#7-batch-downloading-multiple-series)
8. [Limitations and Gotchas](#8-limitations-and-gotchas)
9. [When to Use (and Not Use) This API](#9-when-to-use-and-not-use-this-api)
10. [Alternative Data Sources](#10-alternative-data-sources)
11. [Reference](#11-reference)

---

## 1. What Is the ONS API?

The [Office for National Statistics](https://www.ons.gov.uk/) is the UK's largest independent producer of official statistics. They publish data on GDP, inflation, employment, trade, population, housing, and much more.

The ONS provides a **public API** (Application Programming Interface) that lets you request this data programmatically — meaning you can write a Python script that fetches the latest GDP figures, rather than navigating the website and downloading spreadsheets by hand.

**Key facts:**
- The API is **free** and requires **no authentication** (no API key, no sign-up)
- The base URL is: `https://api.beta.ons.gov.uk/v1/`
- It returns data in **JSON** format
- It has been in **beta** since its launch (more on this in [Limitations](#8-limitations-and-gotchas))

---

## 2. Before You Start

### Install Python

If you don't have Python installed, download it from [python.org](https://www.python.org/downloads/). Version 3.9 or later is recommended.

### Install the required libraries

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux) and run:

```bash
pip install requests pandas
```

That's it. Only two libraries are needed:
- **requests** — for making HTTP calls to the API
- **pandas** — for organising the data into tables (DataFrames)

Or, if you've cloned this repository:

```bash
pip install -r requirements.txt
```

### Test that it works

Open a Python interpreter or Jupyter notebook and run:

```python
import requests

r = requests.get("https://api.beta.ons.gov.uk/v1/datasets")
print(r.status_code)  # Should print: 200
```

If you see `200`, the API is reachable and you're ready to go.

---

## 3. How the API Is Structured

This is the most important section. The ONS API has a **hierarchical structure** that you need to understand before you can fetch any data. Think of it like navigating folders on your computer:

```
Dataset
  └── Edition
        └── Version
              ├── Dimensions (the "filters" for your query)
              └── Observations (the actual data points)
```

### Datasets

A **dataset** is a broad collection of related data. For example:
- `labour-market` — UK employment and unemployment statistics
- `trade` — Trade in goods by country and commodity
- `cpih01` — Consumer Prices Index including housing costs
- `gdp-to-four-decimal-places` — Monthly GDP estimate

There are currently around 300+ datasets available, though many are Census 2021 cross-tabulations rather than the economic time series you might expect.

### Editions

An **edition** is a variant or release of a dataset. Most economic datasets have a `time-series` edition that contains the full historical series. However, some datasets (notably the labour market) use **numbered editions** like `PWT24` for different release vintages.

This is a quirk of the API — there is no universal convention. You often need to inspect what editions exist.

### Versions

Each edition has one or more **versions**. When the ONS updates a dataset, they typically publish a new version under the same edition. The API provides a `latest_version` link, so you usually don't need to worry about this.

### Dimensions

**Dimensions** are the filters that define which slice of data you want. This is where most of the complexity lives.

For example, the `labour-market` dataset has these dimensions:
| Dimension | Example values |
|---|---|
| `agegroups` | `16+`, `16-64`, `16-24`, `25-34`, ... |
| `economicactivity` | `in-employment`, `unemployed`, `economically-inactive` |
| `geography` | `K02000001` (United Kingdom) |
| `seasonaladjustment` | `seasonal-adjustment`, `non-seasonal-adjustment` |
| `sex` | `all-adults`, `men`, `women` |
| `unitofmeasure` | `rates`, `levels` |
| `time` | `jan-mar-2024`, `feb-apr-2024`, ... |

To fetch observations, you must specify a value for **every** dimension. The only exception is that you can set one dimension to `*` (wildcard) to get all values — typically you'll wildcard `time` to get the full time series.

### Observations

**Observations** are the actual data points returned once you've specified all your dimensions. Each observation has a time period and a numeric value.

---

## 4. Step-by-Step: Your First API Call

Let's start by listing all available datasets. This is the simplest possible API call.

```python
import requests

# The base URL for all API calls
ROOT = "https://api.beta.ons.gov.uk/v1/"

# Fetch the first page of datasets
response = requests.get(ROOT + "datasets", params={"limit": 50, "offset": 0})
data = response.json()

# Print the first 10 dataset titles
for item in data["items"][:10]:
    print(f'{item["id"]:<40} {item["title"]}')
```

The API uses **pagination** — it returns results in pages. The `limit` parameter controls how many results per page, and `offset` controls where to start. To get all datasets, you need to loop until no more results are returned.

See [examples/01_list_datasets.py](examples/01_list_datasets.py) for a complete script that fetches all datasets and saves them to a CSV file.

---

## 5. Understanding Dimensions

Before you can download any data, you need to know what dimensions a dataset has, and what values are valid for each one.

Here's how to inspect the dimensions of a dataset:

```python
import requests

ROOT = "https://api.beta.ons.gov.uk/v1/"

# Step 1: Get the dataset and find the latest version URL
dataset = requests.get(ROOT + "datasets/trade").json()
edition_url = dataset["links"]["latest_version"]["href"]

# Step 2: Get the list of dimensions
dims_response = requests.get(edition_url + "/dimensions")
dimensions = dims_response.json()["items"]

for dim in dimensions:
    print(f'\nDimension: {dim["name"]}')

    # Step 3: Get valid options for this dimension
    dim_id = dim["links"]["options"]["id"]
    opts_response = requests.get(
        f'{edition_url}/dimensions/{dim_id}/options',
        params={"limit": 10}
    )
    options = opts_response.json()["items"]

    for opt in options:
        print(f'  {opt["option"]}: {opt.get("label", "")}')
```

This will show you every dimension and its valid values, so you know exactly what to pass when requesting observations.

**Important:** You must provide a value for **every** dimension. If you miss one, the API returns a `400 Bad Request` error. The error message will tell you which dimension is missing, but it's easy to get tripped up by this.

See [examples/02_explore_dimensions.py](examples/02_explore_dimensions.py) for a reusable script that explores any dataset's dimensions.

---

## 6. Downloading a Time Series

Now let's put it all together and download actual data. We'll fetch UK total trade exports as a time series.

```python
import requests
import pandas as pd

ROOT = "https://api.beta.ons.gov.uk/v1/"

# Step 1: Resolve the latest version URL
dataset = requests.get(ROOT + "datasets/trade").json()
edition_url = dataset["links"]["latest_version"]["href"]

# Step 2: Request observations with specific dimensions
#   - Set 'time' to '*' to get the full time series
#   - All other dimensions must have a specific value
params = {
    "time": "*",                                  # all time periods
    "geography": "K02000001",                     # United Kingdom
    "countriesandterritories": "W1",              # Whole world
    "direction": "EX",                            # Exports
    "standardindustrialtradeclassification": "T",  # Total, all commodities
}

response = requests.get(edition_url + "/observations", params=params)
data = response.json()

# Step 3: Parse the observations into a DataFrame
rows = []
for obs in data["observations"]:
    time_info = obs["dimensions"]["Time"]
    rows.append({
        "period": time_info["id"],
        "label": time_info["label"],
        "value": float(obs["observation"]),
    })

df = pd.DataFrame(rows).sort_values("period")
print(df.tail(10))
```

See [examples/03_download_timeseries.py](examples/03_download_timeseries.py) for a complete, reusable version with error handling and CSV export.

---

## 7. Batch Downloading Multiple Series

Once you understand the pattern, you can define a list of series to download in bulk. Each series is just a dataset ID plus a set of dimension values.

```python
SERIES = [
    ("trade", "UK Total Exports", {
        "countriesandterritories": "W1",
        "direction": "EX",
        "geography": "K02000001",
        "standardindustrialtradeclassification": "T",
    }),
    ("trade", "UK Total Imports", {
        "countriesandterritories": "W1",
        "direction": "IM",
        "geography": "K02000001",
        "standardindustrialtradeclassification": "T",
    }),
    # ... add more series here
]
```

See [examples/04_batch_download.py](examples/04_batch_download.py) for a full working example that downloads labour market, GDP, and trade data, saving each series as a separate CSV.

---

## 8. Limitations

The ONS API works, but it has significant rough edges. Being aware of these will save you a lot of frustration.

### 8.1 It's a permanent beta

The API URL is `api.beta.ons.gov.uk` — it has been in beta since launch, with no announced timeline for a stable release. This means:
- Breaking changes can happen without warning
- There are no formal uptime guarantees
- Feature requests and bug fixes are not prioritised in the way you'd expect from a production API

### 8.2 Data freshness is inconsistent

This is the single biggest practical issue. **Some datasets are kept up to date; others are months or years behind the actual ONS publications.**

As of early 2026, here is the state of several key macro datasets:

| Dataset | API release date | How current |
|---|---|---|
| Monthly GDP estimate | Jan 2026 | Up to date |
| Trade in goods | Jan 2026 | Up to date |
| CPIH (inflation) | Jan 2026 | Up to date |
| Retail sales index | Jan 2026 | Up to date |
| **UK Labour Market** | **Jun 2025** | **~8 months behind** |
| **Regional GDP (annual)** | **May 2023** | **~2.5 years behind** |
| **Regional GDP (quarterly)** | **May 2023** | **~2.5 years behind** |

The ONS publishes labour market bulletins every month, but the API data lags far behind. The same data is available via the ONS website — it just doesn't get pushed to the API promptly.

**Always check when a dataset was last updated before relying on it.** You can do this by inspecting the `release_date` field on the version endpoint.

### 8.3 The edition system is confusing

Most datasets use a single `time-series` edition. But some (notably the labour market) split data across numbered editions like `PWT20`, `PWT22`, `PWT23`, `PWT24`. These edition codes are not documented, there's no standard naming convention, and there's no convenience endpoint to just say "give me the latest edition."

In practice, you need to list all editions for a dataset and pick the most recent one yourself.

### 8.4 You must specify every dimension

Unlike APIs such as FRED where you just pass a series ID, the ONS API requires you to explicitly specify a value for **every** dimension. If you miss one, you get a `400 Bad Request`. The error message tells you which dimension is missing, but:
- There's no way to know in advance which dimensions are required without querying them first
- This means a minimum of 3-4 API calls just to understand the shape of a dataset before you can fetch any data

### 8.5 Dimension codes are not always intuitive

Geography codes like `K02000001` (United Kingdom) or `UK0` (England) are internal ONS codes. Industry classifications use codes like `A--T` for "all sectors." You need to query the dimension options to discover these — they are not listed in the main documentation.

### 8.6 Documentation is sparse

The [ONS developer hub](https://developer.ons.gov.uk/) provides a basic overview but lacks:
- Complete Python examples (only JavaScript snippets are provided)
- A full reference of all datasets and their dimensions
- Explanation of the edition naming conventions
- Guidance on which datasets are actively maintained

### 8.7 No push notifications

There is no webhook or notification system. If you need to know when new data is published, you have to poll the API periodically and check version dates yourself.

### 8.8 Pagination is manual

The API returns paginated results (default 20 items per page). You must handle pagination yourself using `limit` and `offset` parameters, and there is no cursor-based pagination.

### 8.9 No calculated fields

The API returns raw index values or levels. If you want growth rates, year-on-year changes, or seasonally adjusted figures that aren't already in the dataset, you need to compute them yourself. Some datasets include multiple `unitofmeasure` options (rates vs levels), but many do not.

---

## 9. When to Use (and Not Use) This API

### Use the ONS API when:
- You need **monthly GDP**, **trade**, **CPIH**, or **retail sales** data — these are well maintained
- You want to **automate** a data pipeline that refreshes regularly
- You want **granular dimension control** (e.g., trade with a specific country, by commodity)
- You need data in a **machine-readable format** without manual downloads

### Consider alternatives when:
- You need **labour market data** with the latest release — the API often lags by months
- You need **regional GDP** — the API version is years behind
- You just want a **single headline number** quickly — the ONS website is faster
- You want a **simple series ID lookup** like FRED provides
- You need **historical revisions** or **vintage data** — the API only provides the latest version

---

## 10. Alternative Data Sources

If the ONS API doesn't meet your needs, these alternatives cover much of the same data:

| Source | URL | Notes |
|---|---|---|
| **FRED** (Federal Reserve) | [fred.stlouisfed.org](https://fred.stlouisfed.org/) | Carries many ONS series with simple series IDs. Free API key required. Often more up to date than the ONS API for UK data. |
| **ONS website** | [ons.gov.uk](https://www.ons.gov.uk/) | Always has the latest release. Data available as downloadable XLSX/CSV files. Not an API, but reliable. |
| **IMF DataMapper** | [imf.org/external/datamapper](https://www.imf.org/external/datamapper/) | Good for cross-country comparisons. Free, no authentication. |
| **World Bank** | [data.worldbank.org](https://data.worldbank.org/) | Comprehensive international data with a clean API. |
| **Bank of England** | [bankofengland.co.uk/statistics](https://www.bankofengland.co.uk/statistics) | Interest rates, monetary aggregates, financial stability data. Has its own statistical API. |
| **Eurostat** | [ec.europa.eu/eurostat](https://ec.europa.eu/eurostat) | EU-wide data including pre-Brexit UK series. |

---

## 11. Reference

### API Base URL

```
https://api.beta.ons.gov.uk/v1/
```

### Key Endpoints

| Endpoint | Description |
|---|---|
| `GET /datasets` | List all datasets (paginated) |
| `GET /datasets/{id}` | Metadata for one dataset |
| `GET /datasets/{id}/editions` | List editions of a dataset |
| `GET /datasets/{id}/editions/{edition}/versions/{version}` | Specific version metadata |
| `GET {version_url}/dimensions` | List dimensions for a version |
| `GET {version_url}/dimensions/{dim}/options` | Valid values for one dimension |
| `GET {version_url}/observations?dim1=val1&dim2=val2&...` | Fetch data points |

### Common Geography Codes

| Code | Meaning |
|---|---|
| `K02000001` | United Kingdom |
| `K03000001` | Great Britain |
| `K04000001` | England and Wales |
| `UK0` | England (used in regional GDP datasets) |
| `UKL` | Wales |
| `UKM` | Scotland |
| `UKN` | Northern Ireland |

### Common Dimension Patterns

| Dimension | Typical values |
|---|---|
| `time` | `*` (wildcard for full series), or specific periods like `Jan-24`, `2023-q1`, `2023` |
| `geography` | See geography codes above |
| `seasonaladjustment` | `seasonal-adjustment`, `non-seasonal-adjustment` |
| `unitofmeasure` | `rates`, `levels` |

### Useful Dataset IDs for Macro Research

| ID | Title | API freshness |
|---|---|---|
| `gdp-to-four-decimal-places` | Monthly GDP estimate (UK) | Current |
| `trade` | Trade in goods by country/commodity | Current |
| `cpih01` | Consumer Prices Index (CPIH) | Current |
| `retail-sales-index` | Retail sales index | Current |
| `labour-market` | UK Labour Market | Delayed |
| `regional-gdp-by-year` | Annual regional GDP | Stale |
| `regional-gdp-by-quarter` | Quarterly regional GDP | Stale |
| `output-in-the-construction-industry` | Construction output | Check |
| `uk-spending-on-cards` | Card spending indicators | Check |
| `index-private-housing-rental-prices` | Rental prices | Check |

---

## Licence

This tutorial and the example scripts are released under the [MIT Licence](LICENCE).

ONS data accessed via the API is published under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
