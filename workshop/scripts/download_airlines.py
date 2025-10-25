#!/usr/bin/env python3
"""
Download and import airlines data from OpenFlights.org
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
    from models.airline import Airline
    from dotenv import load_dotenv
    from tqdm import tqdm
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

# OpenFlights airlines data URL
AIRLINES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"
DATA_DIR = Path("data")
AIRLINES_FILE = DATA_DIR / "airlines.dat"

def download_airlines_data():
    """Download airlines.dat from OpenFlights.org with progress bar"""
    print("🌐 Downloading airlines data from OpenFlights.org...")
    
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    try:
        # Get file size for progress bar
        response = requests.head(AIRLINES_URL, timeout=10)
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress bar
        response = requests.get(AIRLINES_URL, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(AIRLINES_FILE, 'wb') as f:
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
        
        print(f"✅ Downloaded airlines data to {AIRLINES_FILE}")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Failed to download airlines data: {e}")
        return False

def analyze_airlines_data():
    """Analyze the airlines.dat file structure using Polars"""
    if not AIRLINES_FILE.exists():
        print(f"✗ Airlines file not found: {AIRLINES_FILE}")
        return None
    
    print("Analyzing airlines data structure...")
    
    # OpenFlights airlines.dat format (CSV without headers):
    # Airline ID, Name, Alias, IATA, ICAO, Callsign, Country, Active
    
    column_names = [
        "airline_id_openflights",  # OpenFlights ID (different from our DB ID)
        "name",
        "alias", 
        "iata",
        "icao",
        "callsign",
        "country",
        "active"
    ]
    
    try:
        # Read CSV with Polars
        df = pl.read_csv(
            AIRLINES_FILE,
            has_header=False,
            new_columns=column_names,
            null_values=["\\N", ""],  # OpenFlights uses \N for NULL values
            encoding="utf8"
        )
        
        print(f"✓ Loaded {len(df)} airlines from OpenFlights data")
        print(f"Columns: {df.columns}")
        print(f"Shape: {df.shape}")
        
        # Show sample data
        print("\nSample data:")
        print(df.head(3))
        
        # Data quality analysis
        print("\nData Quality Analysis:")
        print(f"- Total airlines: {len(df)}")
        print(f"- Airlines with IATA codes: {df.filter(pl.col('iata').is_not_null() & (pl.col('iata') != '')).height}")
        print(f"- Airlines with ICAO codes: {df.filter(pl.col('icao').is_not_null() & (pl.col('icao') != '')).height}")
        print(f"- Active airlines: {df.filter(pl.col('active') == 'Y').height}")
        print(f"- Inactive airlines: {df.filter(pl.col('active') == 'N').height}")
        print(f"- Unique countries: {df.filter(pl.col('country').is_not_null())['country'].n_unique()}")
        
        return df
        
    except Exception as e:
        print(f"✗ Failed to analyze airlines data: {e}")
        return None

def validate_airline_data(airline_data):
    """Validate airline data before creating Airline record"""
    errors = []
    warnings = []
    
    # Required fields validation
    name = airline_data.get('name')
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        errors.append("Airline name is required")
    elif len(name.strip()) > 200:
        errors.append("Airline name must be 200 characters or less")
    
    # Optional field validation
    iata = airline_data.get('iata')
    if iata and iata.strip():
        if not isinstance(iata, str) or len(iata.strip()) != 2:
            warnings.append("IATA code should be exactly 2 characters if provided")
        elif not iata.strip().isalpha():
            warnings.append("IATA code should contain only letters")
    
    icao = airline_data.get('icao')
    if icao and icao.strip():
        if not isinstance(icao, str) or len(icao.strip()) != 3:
            warnings.append("ICAO code should be exactly 3 characters if provided")
        elif not icao.strip().isalnum():
            warnings.append("ICAO code should contain only letters and numbers")
    
    # Other field validation
    alias = airline_data.get('alias')
    if alias and len(str(alias)) > 200:
        errors.append("Alias must be 200 characters or less")
    
    callsign = airline_data.get('callsign')
    if callsign and len(str(callsign)) > 100:
        errors.append("Callsign must be 100 characters or less")
    
    country = airline_data.get('country')
    if country and len(str(country)) > 100:
        errors.append("Country must be 100 characters or less")
    
    # OpenFlights ID validation
    openflights_id = airline_data.get('airline_id_openflights')
    if openflights_id is not None:
        try:
            int(openflights_id)
        except (ValueError, TypeError):
            errors.append("OpenFlights ID must be a valid integer")
    
    return errors, warnings

def prepare_airline_data(df):
    """Prepare airline data for database insertion"""
    print("Preparing airline data for database insertion...")
    
    prepared_df = df.select([
        pl.col("airline_id_openflights").alias("openflights_id"),
        pl.col("name").str.strip_chars().alias("name"),
        pl.col("alias").str.strip_chars().alias("alias"),
        pl.col("iata").str.strip_chars().alias("iata"),
        pl.col("icao").str.strip_chars().alias("icao"),
        pl.col("callsign").str.strip_chars().alias("callsign"),
        pl.col("country").str.strip_chars().alias("country"),
        pl.col("active").alias("active")
    ]).filter(
        # Filter criteria for valid airline records:
        # 1. Must have name (required in Airline model)
        (pl.col("name").is_not_null()) &
        (pl.col("name") != "") &
        (pl.col("name").str.len_chars() <= 200)
    ).with_columns([
        # Clean up IATA codes - set invalid codes to null
        pl.when(
            (pl.col("iata").is_not_null()) & 
            (pl.col("iata") != "") & 
            (pl.col("iata").str.len_chars() == 2) &
            (pl.col("iata").str.to_uppercase().str.contains(r"^[A-Z]{2}$"))
        )
        .then(pl.col("iata").str.to_uppercase())
        .otherwise(None)
        .alias("iata"),
        
        # Clean up ICAO codes - set invalid codes to null
        pl.when(
            (pl.col("icao").is_not_null()) & 
            (pl.col("icao") != "") & 
            (pl.col("icao").str.len_chars() == 3) &
            (pl.col("icao").str.to_uppercase().str.contains(r"^[A-Z0-9]{3}$"))
        )
        .then(pl.col("icao").str.to_uppercase())
        .otherwise(None)
        .alias("icao"),
        
        # Clean up other text fields
        pl.when(
            (pl.col("alias").is_not_null()) & 
            (pl.col("alias") != "") &
            (pl.col("alias").str.len_chars() <= 200)
        )
        .then(pl.col("alias"))
        .otherwise(None)
        .alias("alias"),
        
        pl.when(
            (pl.col("callsign").is_not_null()) & 
            (pl.col("callsign") != "") &
            (pl.col("callsign").str.len_chars() <= 100)
        )
        .then(pl.col("callsign"))
        .otherwise(None)
        .alias("callsign"),
        
        pl.when(
            (pl.col("country").is_not_null()) & 
            (pl.col("country") != "") &
            (pl.col("country").str.len_chars() <= 100)
        )
        .then(pl.col("country"))
        .otherwise(None)
        .alias("country"),
        
        # Convert active flag to boolean
        pl.when(pl.col("active") == "Y")
        .then(True)
        .when(pl.col("active") == "N")
        .then(False)
        .otherwise(None)
        .alias("active")
    ])
    
    print(f"✓ Prepared {len(prepared_df)} airlines for database insertion")
    print(f"Data coverage:")
    print(f"  - Total airlines: {len(prepared_df)}")
    print(f"  - With IATA codes: {prepared_df.filter(pl.col('iata').is_not_null()).height}")
    print(f"  - With ICAO codes: {prepared_df.filter(pl.col('icao').is_not_null()).height}")
    print(f"  - Active airlines: {prepared_df.filter(pl.col('active') == True).height}")
    print(f"  - With callsigns: {prepared_df.filter(pl.col('callsign').is_not_null()).height}")
    print(f"  - With countries: {prepared_df.filter(pl.col('country').is_not_null()).height}")
    
    return prepared_df

def create_airline_record(airline_data):
    """Create Airline record from airline data with validation"""
    # Validate airline data first
    errors, warnings = validate_airline_data(airline_data)
    if errors:
        return None, errors
    
    try:
        # Create Airline record
        airline = Airline(
            name=airline_data['name'].strip(),
            alias=airline_data.get('alias') if airline_data.get('alias') else None,
            iata=airline_data.get('iata') if airline_data.get('iata') else None,
            icao=airline_data.get('icao') if airline_data.get('icao') else None,
            callsign=airline_data.get('callsign') if airline_data.get('callsign') else None,
            country=airline_data.get('country') if airline_data.get('country') else None,
            active=airline_data.get('active', True),
            openflights_id=int(airline_data['openflights_id']) if airline_data.get('openflights_id') is not None else None,
            data_source="OpenFlights"
        )
        
        return airline, warnings
        
    except Exception as e:
        return None, [f"Error creating record: {str(e)}"]

def insert_airlines_to_database(df):
    """Insert airline data into the database with proper transaction handling"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available for database operations")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("Connected to database successfully!")
        
        with Session(db_manager.engine) as session:
            # Check existing airlines to avoid duplicates
            existing_openflights_ids = set()
            existing_airlines = session.exec(select(Airline.openflights_id)).all()
            existing_openflights_ids.update([id for id in existing_airlines if id is not None])
            
            print(f"Found {len(existing_openflights_ids)} existing airlines in database")
            
            # Convert Polars DataFrame to list of dictionaries
            airlines_data = df.to_dicts()
            
            inserted_count = 0
            skipped_count = 0
            error_count = 0
            warning_count = 0
            batch_size = 100  # Process in batches for better transaction management
            
            print(f"Processing {len(airlines_data)} airlines in batches of {batch_size}...")
            
            # Process airlines in batches for better transaction handling
            with tqdm(
                total=len(airlines_data),
                desc="✈️  Inserting airlines",
                unit="airlines",
                colour='blue',
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} ({percentage:3.0f}%) [{elapsed}<{remaining}]'
            ) as pbar:
                for batch_start in range(0, len(airlines_data), batch_size):
                    batch_end = min(batch_start + batch_size, len(airlines_data))
                    batch_data = airlines_data[batch_start:batch_end]
                    
                    # Process this batch with transaction handling
                    try:
                        batch_inserted = 0
                        batch_skipped = 0
                        batch_errors = 0
                        
                        for airline_data in batch_data:
                            openflights_id = airline_data.get('openflights_id')
                            
                            # Skip if airline already exists
                            if openflights_id and openflights_id in existing_openflights_ids:
                                batch_skipped += 1
                                continue
                            
                            try:
                                # Create Airline record with validation
                                airline, issues = create_airline_record(airline_data)
                                
                                if airline is None:
                                    if error_count < 10:  # Only show first 10 errors
                                        print(f"✗ Validation failed for {airline_data.get('name', 'Unknown')}: {', '.join(issues)}")
                                    batch_errors += 1
                                    continue
                                
                                if issues:  # These are warnings
                                    warning_count += len(issues)
                                    if warning_count <= 10:  # Only show first 10 warnings
                                        print(f"⚠ Warning for {airline.name}: {', '.join(issues)}")
                                
                                # Insert Airline record
                                session.add(airline)
                                session.flush()  # Get the airline_id without committing the transaction
                                
                                if openflights_id:
                                    existing_openflights_ids.add(openflights_id)  # Track to avoid duplicates in this batch
                                batch_inserted += 1
                                
                            except Exception as e:
                                if batch_errors < 5:  # Only show first 5 errors per batch
                                    print(f"✗ Error processing {airline_data.get('name', 'Unknown')}: {e}")
                                batch_errors += 1
                                continue
                        
                        # Commit the entire batch transaction
                        session.commit()
                        
                        # Update counters
                        inserted_count += batch_inserted
                        skipped_count += batch_skipped
                        error_count += batch_errors
                        
                        # Update progress bar
                        pbar.update(len(batch_data))
                        pbar.set_postfix({
                            'Inserted': inserted_count,
                            'Skipped': skipped_count, 
                            'Errors': error_count
                        })
                            
                    except Exception as e:
                        # Rollback the entire batch on any error
                        session.rollback()
                        print(f"✗ Batch transaction failed (airlines {batch_start}-{batch_end}): {e}")
                        error_count += len(batch_data)
                        pbar.update(len(batch_data))
                        continue
            
            print(f"✓ Database insertion completed!")
            print(f"- Inserted: {inserted_count} new airlines")
            print(f"- Skipped: {skipped_count} existing airlines")
            print(f"- Errors: {error_count} airlines failed validation/insertion")
            print(f"- Warnings: {warning_count} data quality warnings")
            
            return True
            
    except Exception as e:
        print(f"✗ Database insertion failed: {e}")
        return False

def show_database_stats():
    """Show statistics about airlines in the database"""
    if not DEPENDENCIES_AVAILABLE:
        return
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        with Session(db_manager.engine) as session:
            # Count total airlines
            total_airlines = session.exec(select(Airline)).all()
            total = len(total_airlines)
            
            if total == 0:
                print("📊 Database Statistics: No airlines found")
                return
            
            # Count airlines with various attributes
            with_iata = len([a for a in total_airlines if a.iata])
            with_icao = len([a for a in total_airlines if a.icao])
            active_airlines = len([a for a in total_airlines if a.active])
            with_callsign = len([a for a in total_airlines if a.callsign])
            with_country = len([a for a in total_airlines if a.country])
            
            print(f"📊 Database Statistics:")
            print(f"  Total airlines: {total:,}")
            print(f"  With IATA codes: {with_iata:,}")
            print(f"  With ICAO codes: {with_icao:,}")
            print(f"  Active airlines: {active_airlines:,}")
            print(f"  With callsigns: {with_callsign:,}")
            print(f"  With countries: {with_country:,}")
            
            # Show sample airlines
            sample_airlines = session.exec(select(Airline).limit(5)).all()
            
            print(f"\nSample airlines:")
            for airline in sample_airlines:
                iata_display = f"({airline.iata})" if airline.iata else "(no IATA)"
                icao_display = f"[{airline.icao}]" if airline.icao else "[no ICAO]"
                status = "Active" if airline.active else "Inactive"
                country_display = f" - {airline.country}" if airline.country else ""
                print(f"  {iata_display} {icao_display} {airline.name} ({status}){country_display}")
                
    except Exception as e:
        print(f"✗ Failed to get database statistics: {e}")

def main():
    """Main function to download and import airlines data"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    print("✈️  OpenFlights Airlines Data Import")
    print("=" * 40)
    
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
    if not AIRLINES_FILE.exists():
        if not download_airlines_data():
            return False
    else:
        print(f"✓ Airlines data already exists: {AIRLINES_FILE}")
    
    # Step 2: Analyze data
    df = analyze_airlines_data()
    if df is None:
        return False
    
    # Step 3: Prepare data
    prepared_df = prepare_airline_data(df)
    if len(prepared_df) == 0:
        print("✗ No suitable airline data found")
        return False
    
    # Step 4: Insert into database (if .env exists)
    if os.path.exists('.env'):
        print(f"\nFound {len(prepared_df):,} airlines ready for import")
        
        # Ask user what to do
        print("What would you like to do?")
        print("  y = Import airlines into database")
        print("  s = Show current database statistics only")
        
        choice = input("\nChoice (y/s): ").strip().lower()
        
        if choice == 's':
            show_database_stats()
            return True
        elif choice == 'y':
            print("Importing airlines into database...")
            if not insert_airlines_to_database(prepared_df):
                return False
            print("\n" + "=" * 50)
            show_database_stats()
            print("\n🎉 Airlines data import completed successfully!")
        else:
            print("Invalid choice. Showing statistics only.")
            show_database_stats()
    else:
        print(f"\n✓ Data analysis completed! {len(prepared_df)} airlines ready for import")
        print("Configure .env file and run again to import into database")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)