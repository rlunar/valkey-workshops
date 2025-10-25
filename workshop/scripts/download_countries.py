#!/usr/bin/env python3
"""
Download and import countries data from OpenFlights.org
"""

import sys
import os
import requests
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import polars as pl
    from sqlmodel import Session, select
    from models.database import DatabaseManager
    from models.country import Country
    from dotenv import load_dotenv
    from tqdm import tqdm
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

# OpenFlights countries data URL
COUNTRIES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/countries.dat"
DATA_DIR = Path("data")
COUNTRIES_FILE = DATA_DIR / "countries.dat"

def download_countries_data():
    """Download countries.dat from OpenFlights.org with progress bar"""
    print("🌐 Downloading countries data from OpenFlights.org...")
    
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    try:
        # Get file size for progress bar
        response = requests.head(COUNTRIES_URL, timeout=10)
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress bar
        response = requests.get(COUNTRIES_URL, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(COUNTRIES_FILE, 'wb') as f:
            with tqdm(
                desc="📥 Downloading",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                colour='green',
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        print(f"✅ Downloaded countries data to {COUNTRIES_FILE}")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Failed to download countries data: {e}")
        return False

def analyze_countries_data():
    """Analyze the countries.dat file structure using Polars"""
    if not COUNTRIES_FILE.exists():
        print(f"✗ Countries file not found: {COUNTRIES_FILE}")
        return None
    
    print("Analyzing countries data structure...")
    
    # OpenFlights countries.dat format (CSV without headers):
    # Name, ISO code, DAFIF code
    
    column_names = [
        "name",
        "iso_code", 
        "dafif_code"
    ]
    
    try:
        # Read CSV with Polars
        df = pl.read_csv(
            COUNTRIES_FILE,
            has_header=False,
            new_columns=column_names,
            null_values=["\\N", ""],  # OpenFlights uses \N for NULL values
            encoding="utf8"
        )
        
        print(f"✓ Loaded {len(df)} countries from OpenFlights data")
        print(f"Columns: {df.columns}")
        print(f"Shape: {df.shape}")
        
        # Show sample data
        print("\nSample data:")
        print(df.head(5))
        
        # Data quality analysis
        print("\nData Quality Analysis:")
        print(f"- Total countries: {len(df)}")
        print(f"- Countries with ISO codes: {df.filter(pl.col('iso_code').is_not_null()).height}")
        print(f"- Countries with DAFIF codes: {df.filter(pl.col('dafif_code').is_not_null()).height}")
        print(f"- Countries with both codes: {df.filter((pl.col('iso_code').is_not_null()) & (pl.col('dafif_code').is_not_null())).height}")
        
        return df
        
    except Exception as e:
        print(f"✗ Failed to analyze countries data: {e}")
        return None

def validate_country_data(country_data):
    """Validate country data before creating Country record"""
    errors = []
    warnings = []
    
    # Required fields validation
    name = country_data.get('name')
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        errors.append("Country name is required")
    elif len(name.strip()) > 200:
        errors.append("Country name must be 200 characters or less")
    
    # ISO code validation (optional but should be 2 characters if provided)
    iso_code = country_data.get('iso_code')
    if iso_code:
        if not isinstance(iso_code, str) or len(iso_code.strip()) != 2:
            errors.append("ISO code must be exactly 2 characters if provided")
        elif not iso_code.strip().isalpha():
            errors.append("ISO code must contain only letters")
    
    # DAFIF code validation (optional but should be 2 characters if provided)
    dafif_code = country_data.get('dafif_code')
    if dafif_code:
        if not isinstance(dafif_code, str) or len(dafif_code.strip()) != 2:
            warnings.append("DAFIF code should be exactly 2 characters if provided")
    
    # Check if country has at least one code
    if not iso_code and not dafif_code:
        warnings.append("Country has neither ISO nor DAFIF code")
    
    return errors, warnings

def prepare_country_data(df):
    """Prepare country data for database insertion"""
    print("Preparing country data for database insertion...")
    
    prepared_df = df.select([
        pl.col("name").str.strip_chars().alias("name"),
        pl.col("iso_code").str.strip_chars().alias("iso_code"),
        pl.col("dafif_code").str.strip_chars().alias("dafif_code")
    ]).filter(
        # Filter criteria for valid country records:
        # 1. Must have name (required in Country model)
        (pl.col("name").is_not_null()) &
        (pl.col("name") != "") &
        (pl.col("name").str.len_chars() <= 200)
    ).with_columns([
        # Clean up ISO codes - set invalid codes to null
        pl.when(
            (pl.col("iso_code").is_not_null()) & 
            (pl.col("iso_code") != "") & 
            (pl.col("iso_code").str.len_chars() == 2) &
            (pl.col("iso_code").str.to_uppercase().str.contains(r"^[A-Z]{2}$"))
        )
        .then(pl.col("iso_code").str.to_uppercase())
        .otherwise(None)
        .alias("iso_code"),
        
        # Clean up DAFIF codes - set invalid codes to null
        pl.when(
            (pl.col("dafif_code").is_not_null()) & 
            (pl.col("dafif_code") != "") & 
            (pl.col("dafif_code").str.len_chars() == 2)
        )
        .then(pl.col("dafif_code").str.to_uppercase())
        .otherwise(None)
        .alias("dafif_code")
    ])
    
    print(f"✓ Prepared {len(prepared_df)} countries for database insertion")
    print(f"Country data:")
    print(f"  - Total countries: {len(prepared_df)}")
    print(f"  - With ISO codes: {prepared_df.filter(pl.col('iso_code').is_not_null()).height}")
    print(f"  - With DAFIF codes: {prepared_df.filter(pl.col('dafif_code').is_not_null()).height}")
    print(f"  - With both codes: {prepared_df.filter((pl.col('iso_code').is_not_null()) & (pl.col('dafif_code').is_not_null())).height}")
    
    return prepared_df

def create_country_record(country_data):
    """Create Country record from country data with validation"""
    # Validate country data first
    errors, warnings = validate_country_data(country_data)
    if errors:
        return None, errors
    
    try:
        # Import ISO code mapping utility
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.iso_country_codes import get_iso_a3_from_iso_a2
        
        # Get ISO A3 code from ISO A2 code if available
        iso_a2 = country_data.get('iso_code')
        iso_a3 = None
        if iso_a2:
            iso_a3 = get_iso_a3_from_iso_a2(iso_a2.upper())
        
        # Create Country record
        country = Country(
            name=country_data['name'].strip(),
            iso_code=iso_a2.upper() if iso_a2 else None,
            iso_a3=iso_a3,
            dafif_code=country_data.get('dafif_code').upper() if country_data.get('dafif_code') else None,
            data_source="OpenFlights"
        )
        
        return country, warnings
        
    except Exception as e:
        return None, [f"Error creating record: {str(e)}"]

def insert_countries_to_database(df):
    """Insert country data into the database with proper transaction handling"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available for database operations")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("Connected to database successfully!")
        
        with Session(db_manager.engine) as session:
            # Check existing countries to avoid duplicates
            existing_names = set()
            existing_iso_codes = set()
            
            existing_countries = session.exec(select(Country)).all()
            for country in existing_countries:
                existing_names.add(country.name.lower())
                if country.iso_code:
                    existing_iso_codes.add(country.iso_code.upper())
            
            print(f"Found {len(existing_countries)} existing countries in database")
            
            # Convert Polars DataFrame to list of dictionaries
            countries_data = df.to_dicts()
            
            inserted_count = 0
            skipped_count = 0
            error_count = 0
            warning_count = 0
            
            print(f"Processing {len(countries_data)} countries...")
            
            for country_data in countries_data:
                name = country_data['name']
                iso_code = country_data.get('iso_code')
                
                # Skip if country already exists (by name or ISO code)
                if (name.lower() in existing_names or 
                    (iso_code and iso_code.upper() in existing_iso_codes)):
                    skipped_count += 1
                    continue
                
                try:
                    # Create Country record with validation
                    country, issues = create_country_record(country_data)
                    
                    if country is None:
                        if error_count < 10:  # Only show first 10 errors
                            print(f"✗ Validation failed for {name}: {', '.join(issues)}")
                        error_count += 1
                        continue
                    
                    if issues:  # These are warnings
                        warning_count += len(issues)
                        if warning_count <= 10:  # Only show first 10 warnings
                            print(f"⚠ Warning for {name}: {', '.join(issues)}")
                    
                    # Insert Country record
                    session.add(country)
                    session.commit()
                    
                    # Track to avoid duplicates
                    existing_names.add(name.lower())
                    if iso_code:
                        existing_iso_codes.add(iso_code.upper())
                    
                    inserted_count += 1
                    
                except Exception as e:
                    session.rollback()
                    if error_count < 5:  # Only show first 5 errors
                        print(f"✗ Error processing {name}: {e}")
                    error_count += 1
                    continue
            
            print(f"✓ Database insertion completed!")
            print(f"- Inserted: {inserted_count} new countries")
            print(f"- Skipped: {skipped_count} existing countries")
            print(f"- Errors: {error_count} countries failed validation/insertion")
            print(f"- Warnings: {warning_count} data quality warnings")
            
            return True
            
    except Exception as e:
        print(f"✗ Database insertion failed: {e}")
        return False

def show_database_stats():
    """Show statistics about countries in the database"""
    if not DEPENDENCIES_AVAILABLE:
        return
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        with Session(db_manager.engine) as session:
            # Count total countries
            total_countries = session.exec(select(Country)).all()
            total = len(total_countries)
            
            if total == 0:
                print("📊 Database Statistics: No countries found")
                return
            
            # Count countries with codes
            with_iso = len([c for c in total_countries if c.iso_code])
            with_dafif = len([c for c in total_countries if c.dafif_code])
            with_both = len([c for c in total_countries if c.iso_code and c.dafif_code])
            
            print(f"📊 Database Statistics:")
            print(f"  Total countries: {total:,}")
            print(f"  With ISO codes: {with_iso:,}")
            print(f"  With DAFIF codes: {with_dafif:,}")
            print(f"  With both codes: {with_both:,}")
            
            # Show sample countries
            sample_countries = total_countries[:5]
            print(f"\nSample countries:")
            for country in sample_countries:
                iso_display = f"({country.iso_code})" if country.iso_code else "(no ISO)"
                dafif_display = f"[{country.dafif_code}]" if country.dafif_code else "[no DAFIF]"
                print(f"  {country.name} {iso_display} {dafif_display}")
                
    except Exception as e:
        print(f"✗ Failed to get database statistics: {e}")

def main():
    """Main function to download and import countries data"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    print("🌍 OpenFlights Countries Data Import")
    print("=" * 35)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        print("You can still download and analyze data without database connection")
        
        # Offer to continue without database import
        try:
            response = input("\nContinue with download and analysis only? (y/N): ").strip().lower()
            if response != 'y':
                return False
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return False
    
    # Step 1: Download data
    if not COUNTRIES_FILE.exists():
        if not download_countries_data():
            return False
    else:
        print(f"✓ Countries data already exists: {COUNTRIES_FILE}")
    
    # Step 2: Analyze data
    df = analyze_countries_data()
    if df is None:
        return False
    
    # Step 3: Prepare data
    prepared_df = prepare_country_data(df)
    if len(prepared_df) == 0:
        print("✗ No suitable country data found")
        return False
    
    # Step 4: Insert into database (if .env exists)
    if os.path.exists('.env'):
        print(f"\nFound {len(prepared_df):,} countries ready for import")
        
        # Ask user what to do
        print("What would you like to do?")
        print("  y = Import countries into database")
        print("  s = Show current database statistics only")
        
        choice = input("\nChoice (y/s): ").strip().lower()
        
        if choice == 's':
            show_database_stats()
            return True
        elif choice == 'y':
            print("Importing countries into database...")
            if not insert_countries_to_database(prepared_df):
                return False
            print("\n" + "=" * 50)
            show_database_stats()
            print("\n🎉 Country data import completed successfully!")
        else:
            print("Invalid choice. Showing statistics only.")
            show_database_stats()
    else:
        print(f"\n✓ Data analysis completed! {len(prepared_df)} countries ready for import")
        print("Configure .env file and run again to import into database")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)