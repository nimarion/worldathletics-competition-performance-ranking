# World Athletics Competition Performance Rankings Scraper

A robust, type-hinted, and modular Python tool designed to scrape the competition performance rankings table from World Athletics and export it into a clean, backend-ready CSV file.

Included is an automated **GitHub Actions pipeline** that runs daily to keep the data updated.

---

## Features

- **Multi-page Scraper:** Automatically detects pagination and scrapes all available ranking pages.
- **Backend-Ready CSV:** Generates camelCase headers for immediate ingestion into database/backend systems (e.g., MongoDB, PostgreSQL, REST APIs).
- **Descriptive Identifiers:** Extracts the actual **Competition ID** and **Competition URL** from the page's interactive row markers.
- **Enterprise-Grade Resilience:** Configured with robust session management featuring a custom user-agent, automatic request throttling (polite delays), and exponential backoff retries for transient network/server glitches (like `502`, `503`, or `504` errors).
- **Scheduled GitHub Action:** Automatically scrapes the latest rankings once a day and commits the updated dataset back to the repository.

---

## Data Schema (camelCase)

| Column Header | Description | Example |
| :--- | :--- | :--- |
| `place` | The overall rank of the competition. | `1` |
| `competitionId` | The unique ID of the competition. | `658567` |
| `competition` | Name and location of the event. | `"Wanda Diamond League, China Textile City..."` |
| `country` | Three-letter country code of the venue. | `CHN` |
| `startDate` | Event start date. | `16 MAY 2026` |
| `endDate` | Event end date. | `16 MAY 2026` |
| `partScore` | Participation Score (athlete quality). | `6470` |
| `participationScorePlace` | Ranking by Participation Score. | `3` |
| `resultScore` | Result Score (performance marks achieved). | `88474` |
| `resultScorePlace` | Ranking by Result Score. | `1` |
| `competitionScore` | Total overall ranking score. | `94944` |
| `competitionUrl` | Direct World Athletics URL to the competition details. | `https://worldathletics.org/...` |

---

## Installation & Setup

Ensure you have **Python 3.9+** installed.

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd worldathletics-performance-ranking
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

You can run the scraper directly from the command line using the Python interpreter inside your virtual environment.

### Basic Usage

Scrape all available pages for the default view and save them to the default `data/<current_year>.csv` (e.g., `data/2026.csv`):
```bash
python scrape_rankings.py
```

### Advanced Filtering Examples

* **Limit pages (for quick testing/safety):**
  ```bash
  python scrape_rankings.py --max-pages 2
  ```

* **Filter by a specific year:**
  ```bash
  python scrape_rankings.py --year 2025
  ```

* **Filter by competition type (e.g., Championships):**
  ```bash
  python scrape_rankings.py --type championships
  ```

* **Sort by Result Score:**
  ```bash
  python scrape_rankings.py --sort resultScore
  ```

* **Specify a custom output path:**
  ```bash
  python scrape_rankings.py --output my_custom_output.csv
  ```

* **Enable detailed debugging logs:**
  ```bash
  python scrape_rankings.py --debug
  ```

---

## Command Line Arguments

| Short Flag | Long Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `-y` | `--year` | `int` | `None` | Year of rankings to retrieve (e.g., `2025`). |
| `-t` | `--type` | `str` | `None` | Competition type (e.g., `championships`, `indoor`, `marathon`). |
| `-s` | `--sort` | `str` | `competitionScore` | Score type to sort by (`competitionScore`, `participationScore`, `resultScore`). |
| `-o` | `--output` | `str` | *Auto-generated* | Custom output CSV file path. |
| `-d` | `--delay` | `float` | `1.0` | Throttling delay (in seconds) between requests. |
| `-m` | `--max-pages`| `int` | `None` | Max limit on pages to fetch. |
| | `--debug` | `flag`| *Disabled* | Show internal debug requests/logs. |

---

## GitHub Actions Pipeline

The repository includes a GitHub Actions workflow in `.github/workflows/scrape.yml` configured to:
1. **Run Daily:** Executes automatically once a day at `00:00 UTC` using GitHub cron.
2. **On-Demand Dispatch:** Can be manually triggered at any time from the **Actions** tab on GitHub.
3. **Automated Data Sync:** Runs the scraper, automatically checks for diffs, and commits/pushes updated CSV rankings directly back to the `main` branch (using `github-actions[bot]`).

---

## Filtering & Combining Datasets

A generic utility script `combine.py` is included in the project root to help you filter and consolidate records from all yearly files into a single, unified CSV or JSON file based on a specific location or competition name query.

### Usage
```bash
python combine.py <search_term> [output_file] [options]
```

### Options
* `-j`, `--json`   Force the output format to JSON.

### Examples
* **Combine all Rehlingen competitions (defaults to CSV):**
  ```bash
  python combine.py Rehlingen
  ```
  *(This will scan all files inside `data/` and automatically compile matching records into `rehlingen.csv`)*

* **Combine all Rehlingen competitions in JSON format (using the `-j` flag):**
  ```bash
  python combine.py Rehlingen -j
  ```
  *(This will automatically compile matching records into `rehlingen.json`)*

* **Combine all Rehlingen competitions into a custom JSON file (autodetected by extension):**
  ```bash
  python combine.py Rehlingen rehlingen_custom.json
  ```

* **Combine all Diamond League competitions into a custom file name:**
  ```bash
  python combine.py "Diamond League" diamond_league.csv
  ```
