#!/usr/bin/env python3
"""
Show statistics about downloaded airports data
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
AIRPORTS_FILE = DATA_DIR / "airports.dat"

def show_airports_statistics():
    """Show detailed statistics about the airports data"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    if not AIRPORTS_FILE.exists():
        print(f"Airports data not found: {AIRPORTS_FILE}")
        print("Run: uv run python scripts/download_airports.py")
        return False
    
    print("OpenFlights Airports Data Statistics")
    print("=" * 36)
    
    # Load data
    column_names = [
        "airport_id_openflights", "name", "city", "country", "iata", "icao",
        "latitude", "longitude", "altitude", "timezone_offset", "dst", 
        "timezone_name", "type", "source"
    ]
    
    df = pl.read_csv(
        AIRPORTS_FILE,
        has_header=False,
        new_columns=column_names,
        null_values=["\\N", ""],
        encoding="utf8"
    )
    
    print(f"Total airports in dataset: {len(df)}")
    print(f"Data file size: {AIRPORTS_FILE.stat().st_size / 1024:.1f} KB")
    
    # Basic statistics
    print(f"\nBasic Statistics:")
    print(f"- Airports with IATA codes: {df.filter(pl.col('iata').is_not_null()).height:,}")
    print(f"- Airports with ICAO codes: {df.filter(pl.col('icao').is_not_null()).height:,}")
    print(f"- Airports with both IATA and ICAO: {df.filter((pl.col('iata').is_not_null()) & (pl.col('icao').is_not_null())).height:,}")
    
    # Geographic distribution
    print(f"\nGeographic Distribution:")
    print(f"- Unique countries: {df['country'].n_unique()}")
    print(f"- Unique cities: {df['city'].n_unique()}")
    
    # Top countries by airport count
    print(f"\nTop 10 Countries by Airport Count:")
    top_countries = df.group_by("country").agg(pl.count().alias("count")).sort("count", descending=True).head(10)
    for row in top_countries.iter_rows():
        country, count = row
        print(f"  {country}: {count:,}")
    
    # Airport types
    print(f"\nAirport Types:")
    types = df.group_by("type").agg(pl.count().alias("count")).sort("count", descending=True)
    for row in types.iter_rows():
        type_name, count = row
        print(f"  {type_name}: {count:,}")
    
    # Data sources
    print(f"\nData Sources:")
    sources = df.group_by("source").agg(pl.count().alias("count")).sort("count", descending=True)
    for row in sources.iter_rows():
        source, count = row
        print(f"  {source}: {count:,}")
    
    # Altitude statistics
    altitude_stats = df.select(pl.col("altitude")).filter(pl.col("altitude").is_not_null())
    if len(altitude_stats) > 0:
        print(f"\nAltitude Statistics:")
        print(f"- Airports with altitude data: {len(altitude_stats):,}")
        print(f"- Highest airport: {altitude_stats.max().item():.0f} ft")
        print(f"- Lowest airport: {altitude_stats.min().item():.0f} ft")
        print(f"- Average altitude: {altitude_stats.mean().item():.0f} ft")
    
    # Sample of interesting airports
    print(f"\nSample Major International Airports:")
    major_airports = df.filter(
        pl.col("iata").is_in(["JFK", "LAX", "LHR", "CDG", "NRT", "SIN", "DXB", "FRA"])
    ).select(["iata", "icao", "name", "city", "country"])
    
    for row in major_airports.iter_rows():
        iata, icao, name, city, country = row
        print(f"  {iata}/{icao}: {name}, {city}, {country}")
    
    return True

if __name__ == "__main__":
    success = show_airports_statistics()
    sys.exit(0 if success else 1)