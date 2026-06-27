#!/usr/bin/env python3
"""
World Athletics Competition Rankings Combiner
Combines yearly CSV datasets in data/ that match a search term into a single CSV or JSON.

Usage:
    python combine.py <search_term> [output_file] [options]

Examples:
    python combine.py Rehlingen
    python combine.py Rehlingen rehlingen.json
    python combine.py "Diamond League" -j
"""

import sys
import os
import csv
import glob
import re
import json
import argparse


def clean_filename(term: str, extension: str = "csv") -> str:
    """Converts a search term into a safe lowercase snake_case filename."""
    # Convert to lowercase
    s = term.lower()
    # Replace non-alphanumeric characters with underscores
    s = re.sub(r'[^a-z0-9]+', '_', s)
    # Remove leading/trailing underscores
    s = s.strip('_')
    return f"{s}.{extension}"


def combine_records(search_term: str, output_path: str, data_dir: str = "data", force_json: bool = False) -> None:
    """Scans all CSV datasets in data_dir, extracts matching rows, and compiles them to CSV or JSON."""
    if not os.path.exists(data_dir):
        print(f"Error: Source directory '{data_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
    if not csv_files:
        print(f"Error: No CSV files found in '{data_dir}/'.", file=sys.stderr)
        sys.exit(1)

    # Determine format: JSON if output file ends with .json or if force_json is True
    is_json = output_path.lower().endswith(".json") or force_json
    format_type = "JSON" if is_json else "CSV"

    print("=" * 60)
    print(f" World Athletics rankings filter & combine utility ({format_type})")
    print("=" * 60)
    print(f"Search Term : '{search_term}'")
    print(f"Output File : '{output_path}'")
    print(f"Source Dir  : '{data_dir}/'")
    print("=" * 60)
    print("Scanning datasets...")

    search_term_lower = search_term.lower()
    all_rows = []
    headers = []

    for file_path in csv_files:
        try:
            with open(file_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not headers and reader.fieldnames:
                    headers = reader.fieldnames
                
                for row in reader:
                    competition_name = row.get("competition", "")
                    if search_term_lower in competition_name.lower():
                        all_rows.append(row)
        except Exception as e:
            print(f"Warning: Failed to process file {file_path}: {e}", file=sys.stderr)

    if not all_rows:
        print(f"\nNo records matched the search term '{search_term}'.")
        sys.exit(0)

    try:
        if is_json:
            # Save as JSON format
            with open(output_path, mode="w", encoding="utf-8") as out_f:
                json.dump(all_rows, out_f, indent=2, ensure_ascii=False)
        else:
            # Save as CSV format
            if not headers:
                print("Error: Could not determine CSV headers from source files.", file=sys.stderr)
                sys.exit(1)
            with open(output_path, mode="w", newline="", encoding="utf-8") as out_f:
                writer = csv.DictWriter(out_f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(all_rows)
                
        print(f"\nSuccess! Found and compiled {len(all_rows)} matching records into '{output_path}'")
    except Exception as e:
        print(f"Error: Failed to write to '{output_path}': {e}", file=sys.stderr)
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter yearly World Athletics datasets by search term and combine them into a single CSV or JSON file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python combine.py Rehlingen                         # Saves to rehlingen.csv
  python combine.py Rehlingen -j                      # Saves to rehlingen.json
  python combine.py Rehlingen rehlingen.json          # Saves to rehlingen.json (autodetected)
  python combine.py "Diamond League" dl_dataset.csv  # Saves to dl_dataset.csv
"""
    )
    parser.add_argument(
        "search_term",
        type=str,
        help="The term to search for in competition names (case-insensitive)."
    )
    parser.add_argument(
        "output_file",
        type=str,
        nargs="?",
        help="Optional. Custom output path. Defaults to safe search_term with .csv or .json extension."
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Force the output to JSON format."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    
    # Determine the target file extension
    ext = "json" if args.json else "csv"
    
    # Generate default output file name if not provided
    if not args.output_file:
        output_file = clean_filename(args.search_term, ext)
    else:
        output_file = args.output_file

    combine_records(args.search_term, output_file, force_json=args.json)


if __name__ == "__main__":
    main()
