#!/usr/bin/env python3
"""
Show statistics about downloaded countries data
"""

import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import polars as pl
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

DATA_DIR = Path("data")
COUNTRIES_FILE = DATA_DIR / "countries.dat"

def show_countries_statistics():
    """Show detailed statistics about the countries data"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    if not COUNTRIES_FILE.exists():
        print(f"Countries data not found: {COUNTRIES_FILE}")
        print("Run: uv run python scripts/download_countries.py")
        return False
    
    print("OpenFlights Countries Data Statistics")
    print("=" * 37)
    
    # Load data
    column_names = ["name", "iso_code", "dafif_code"]
    
    df = pl.read_csv(
        COUNTRIES_FILE,
        has_header=False,
        new_columns=column_names,
        null_values=["\\N", ""],
        encoding="utf8"
    )
    
    print(f"Total countries in dataset: {len(df)}")
    print(f"Data file size: {COUNTRIES_FILE.stat().st_size / 1024:.1f} KB")
    
    # Basic statistics
    print(f"\nBasic Statistics:")
    print(f"- Countries with ISO codes: {df.filter(pl.col('iso_code').is_not_null()).height:,}")
    print(f"- Countries with DAFIF codes: {df.filter(pl.col('dafif_code').is_not_null()).height:,}")
    print(f"- Countries with both codes: {df.filter((pl.col('iso_code').is_not_null()) & (pl.col('dafif_code').is_not_null())).height:,}")
    print(f"- Countries with neither code: {df.filter((pl.col('iso_code').is_null()) & (pl.col('dafif_code').is_null())).height:,}")
    
    # Countries with only one type of code
    only_iso = df.filter((pl.col('iso_code').is_not_null()) & (pl.col('dafif_code').is_null())).height
    only_dafif = df.filter((pl.col('iso_code').is_null()) & (pl.col('dafif_code').is_not_null())).height
    print(f"- Countries with only ISO code: {only_iso:,}")
    print(f"- Countries with only DAFIF code: {only_dafif:,}")
    
    # Sample countries by category
    print(f"\nSample Countries by Category:")
    
    # Countries with both codes
    both_codes = df.filter(
        (pl.col('iso_code').is_not_null()) & (pl.col('dafif_code').is_not_null())
    ).head(5)
    print(f"\nCountries with both ISO and DAFIF codes:")
    for row in both_codes.iter_rows():
        name, iso, dafif = row
        print(f"  {name} (ISO: {iso}, DAFIF: {dafif})")
    
    # Countries with only ISO codes
    only_iso_countries = df.filter(
        (pl.col('iso_code').is_not_null()) & (pl.col('dafif_code').is_null())
    ).head(5)
    if len(only_iso_countries) > 0:
        print(f"\nCountries with only ISO codes:")
        for row in only_iso_countries.iter_rows():
            name, iso, dafif = row
            print(f"  {name} (ISO: {iso})")
    
    # Countries with only DAFIF codes
    only_dafif_countries = df.filter(
        (pl.col('iso_code').is_null()) & (pl.col('dafif_code').is_not_null())
    ).head(5)
    if len(only_dafif_countries) > 0:
        print(f"\nCountries with only DAFIF codes:")
        for row in only_dafif_countries.iter_rows():
            name, iso, dafif = row
            print(f"  {name} (DAFIF: {dafif})")
    
    # Countries with neither code
    no_codes = df.filter(
        (pl.col('iso_code').is_null()) & (pl.col('dafif_code').is_null())
    )
    if len(no_codes) > 0:
        print(f"\nCountries with no codes:")
        for row in no_codes.head(5).iter_rows():
            name, iso, dafif = row
            print(f"  {name}")
    
    # Sample of well-known countries
    print(f"\nSample Major Countries:")
    major_countries = df.filter(
        pl.col("iso_code").is_in(["US", "GB", "DE", "FR", "JP", "AU", "CA", "CN", "IN", "BR"])
    ).select(["name", "iso_code", "dafif_code"])
    
    for row in major_countries.iter_rows():
        name, iso, dafif = row
        dafif_display = f", DAFIF: {dafif}" if dafif else ""
        print(f"  {name} (ISO: {iso}{dafif_display})")
    
    # Longest and shortest country names
    print(f"\nCountry Name Length Statistics:")
    name_lengths = df.with_columns(pl.col("name").str.len_chars().alias("name_length"))
    longest = name_lengths.sort("name_length", descending=True).head(3)
    shortest = name_lengths.sort("name_length").head(3)
    
    print(f"Longest country names:")
    for row in longest.iter_rows():
        name, iso, dafif, length = row
        print(f"  {name} ({length} characters)")
    
    print(f"Shortest country names:")
    for row in shortest.iter_rows():
        name, iso, dafif, length = row
        print(f"  {name} ({length} characters)")
    
    return True

if __name__ == "__main__":
    success = show_countries_statistics()
    sys.exit(0 if success else 1)