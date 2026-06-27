#!/usr/bin/env python3
"""
World Athletics Competition Performance Rankings Scraper
A highly robust, type-hinted, and modular tool to scrape and export rankings data.
Designed for both interactive CLI usage and automated headless workflows (e.g., GitHub Actions).
"""

import sys
import time
import argparse
import csv
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from bs4 import BeautifulSoup

# Configure logging with clean format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("scraper")


@dataclass
class ScraperConfig:
    """Configuration options for the World Athletics scraper."""
    year: Optional[int] = None
    competition_type: Optional[str] = None
    sort_by: str = "competitionScore"
    output_path: Optional[str] = None
    delay: float = 1.0
    max_pages: Optional[int] = None
    retries: int = 3
    backoff_factor: float = 1.0


class WorldAthleticsScraper:
    """Scraper for extracting competition performance rankings from World Athletics."""

    BASE_URL = "https://worldathletics.org/records/competition-performance-rankings"

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session = self._create_robust_session()

    def _create_robust_session(self) -> requests.Session:
        """Creates a requests.Session with connection pooling, headers, and automatic retries."""
        session = requests.Session()
        
        # Configure polite but realistic browser headers
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://worldathletics.org/"
        })

        # Retry strategy for transient network errors (e.g., 502, 503, 504)
        retry_strategy = Retry(
            total=self.config.retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def fetch_page_html(self, page: int) -> Optional[str]:
        """Fetches the HTML source for a specific page with the current filters applied."""
        params: Dict[str, Any] = {"page": page}
        
        if self.config.year:
            params["year"] = self.config.year
        if self.config.competition_type:
            params["competitionType"] = self.config.competition_type
        # Default is competitionScore; server rejects explicitly passing 'competitionScore' as sortBy parameter value
        if self.config.sort_by and self.config.sort_by != "competitionScore":
            params["sortBy"] = self.config.sort_by

        # Polite delay before non-initial requests
        if page > 1 and self.config.delay > 0:
            time.sleep(self.config.delay)

        try:
            logger.debug(f"Requesting URL: {self.BASE_URL} with params: {params}")
            response = self.session.get(self.BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {page}: {e}")
            return None

    def extract_total_pages(self, html_content: str) -> Optional[int]:
        """Parses the page HTML to find the maximum pagination limit."""
        soup = BeautifulSoup(html_content, "html.parser")
        pagination_div = soup.find("div", class_="cpr-pagination")
        if not pagination_div:
            return None

        # Look for the last page link button
        last_page_btn = pagination_div.find("a", class_="btn--pag-last")
        if last_page_btn and last_page_btn.get("data-page"):
            try:
                return int(last_page_btn.get("data-page"))
            except ValueError:
                pass

        # Fallback: scan for all numeric page links
        number_btns = pagination_div.find_all("a", class_="btn--number")
        pages = []
        for btn in number_btns:
            page_val = btn.get("data-page")
            if page_val:
                try:
                    pages.append(int(page_val))
                except ValueError:
                    pass
        if pages:
            return max(pages)

        return None

    def parse_rankings(self, html_content: str) -> List[Dict[str, str]]:
        """Parses the records-table from the HTML content and returns structured rows."""
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", class_="records-table")
        if not table:
            return []

        rows = table.find_all("tr")
        parsed_data = []

        for row in rows:
            # Skip the table header row
            if row.find("th"):
                continue

            cells = row.find_all("td")
            if len(cells) not in (10, 11):
                continue

            # Standardized helper to clean up cell whitespaces and inner tags
            def get_cell_text(cell) -> str:
                return " ".join(cell.get_text().split())

            place = get_cell_text(cells[0])
            competition = get_cell_text(cells[1])
            country = get_cell_text(cells[2])
            start_date = get_cell_text(cells[3])
            end_date = get_cell_text(cells[4])
            part_score = get_cell_text(cells[5])
            ps_place = get_cell_text(cells[6])
            result_score = get_cell_text(cells[7])
            rs_place = get_cell_text(cells[8])
            comp_score = get_cell_text(cells[10] if len(cells) == 11 else cells[9])

            # Parse competition ID and URL from the row's interactive data-href
            data_href = row.get("data-href", "")
            competition_id = ""
            competition_url = ""
            if data_href:
                parts = [p for p in data_href.split("/") if p]
                if parts:
                    competition_id = parts[-1]
                competition_url = f"https://worldathletics.org{data_href}"

            parsed_data.append({
                "place": place,
                "competitionId": competition_id,
                "competition": competition,
                "country": country,
                "startDate": start_date,
                "endDate": end_date,
                "partScore": part_score,
                "participationScorePlace": ps_place,
                "resultScore": result_score,
                "resultScorePlace": rs_place,
                "competitionScore": comp_score,
                "competitionUrl": competition_url
            })

        return parsed_data

    def run(self) -> List[Dict[str, str]]:
        """Orchestrates the multi-page scraping flow and returns all scraped data."""
        all_rankings: List[Dict[str, str]] = []
        page = 1
        total_pages: Optional[int] = None

        logger.info("Initializing World Athletics ranking extraction...")
        
        while True:
            # Check maximum pages limit
            if self.config.max_pages and page > self.config.max_pages:
                logger.info(f"Reached user safety page limit of: {self.config.max_pages}")
                break

            total_pages_str = f" of {total_pages}" if total_pages else ""
            logger.info(f"Retrieving page {page}{total_pages_str}...")

            html_content = self.fetch_page_html(page)
            if not html_content:
                logger.warning(f"Aborting early due to request failure on page {page}.")
                break

            # Discover total pages dynamically from the first page's pagination
            if page == 1:
                total_pages = self.extract_total_pages(html_content)
                if total_pages:
                    logger.info(f"Dynamically discovered {total_pages} pages to scrape.")
                else:
                    logger.info("Pagination not detected or single-page dataset; scraping on-demand.")

            # Parse records
            page_rankings = self.parse_rankings(html_content)
            if not page_rankings:
                logger.info(f"No additional data rows found on page {page}. Stopping.")
                break

            logger.info(f"Successfully extracted {len(page_rankings)} records from page {page}.")
            all_rankings.extend(page_rankings)

            # Check if we've reached the maximum dynamically discovered page
            if total_pages and page >= total_pages:
                logger.info(f"Finished scraping last dynamic page: {total_pages}")
                break

            page += 1

        return all_rankings


def save_to_csv(data: List[Dict[str, str]], file_path: str) -> None:
    """Saves the list of parsed rankings dictionaries into a clean CSV file."""
    headers = [
        "place", "competitionId", "competition", "country", "startDate", "endDate",
        "partScore", "participationScorePlace", "resultScore", "resultScorePlace", "competitionScore", "competitionUrl"
    ]

    try:
        with open(file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()
            for record in data:
                writer.writerow(record)
        logger.info(f"Dataset successfully compiled and saved to '{file_path}'")
    except IOError as e:
        logger.error(f"Failed to write dataset to CSV file '{file_path}': {e}")
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape World Athletics Competition Performance Rankings into a CSV file."
    )
    parser.add_argument(
        "-y", "--year",
        type=int,
        help="Filter rankings by a specific year (e.g., 2026, 2025)."
    )
    parser.add_argument(
        "-t", "--type",
        type=str,
        dest="competition_type",
        help="Filter by competition type (e.g., championships, invitational-open, indoor, combined-events, road-running, marathon)."
    )
    parser.add_argument(
        "-s", "--sort",
        type=str,
        choices=["competitionScore", "participationScore", "resultScore"],
        default="competitionScore",
        help="Sort rankings by score type. Choices: competitionScore, participationScore, resultScore. Default is competitionScore."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Custom output CSV filename path."
    )
    parser.add_argument(
        "-d", "--delay",
        type=float,
        default=1.0,
        help="Polite request throttling delay in seconds. Default is 1.0."
    )
    parser.add_argument(
        "-m", "--max-pages",
        type=int,
        help="Safety limit on max pages to extract."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable internal debugging messages."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Establish default target CSV output filename if omitted
    if not args.output:
        if args.year:
            args.output = f"data/{args.year}.csv"
        else:
            import datetime
            current_year = datetime.datetime.now().year
            args.output = f"data/{current_year}.csv"

    # Compile Configuration and execute Scraper
    config = ScraperConfig(
        year=args.year,
        competition_type=args.competition_type,
        sort_by=args.sort,
        output_path=args.output,
        delay=args.delay,
        max_pages=args.max_pages
    )

    scraper = WorldAthleticsScraper(config)
    
    try:
        rankings = scraper.run()
        if not rankings:
            logger.error("No record data retrieved. Double check parameters and connection.")
            sys.exit(1)

        logger.info(f"Scraping phase finished. Total records collected: {len(rankings)}")
        save_to_csv(rankings, args.output)

    except KeyboardInterrupt:
        logger.info("\nScraping execution halted manually by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
