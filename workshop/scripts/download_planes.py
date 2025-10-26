#!/usr/bin/env python3
"""
Download and import aircraft data from OpenFlights.org
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
    from models.airplane_type import AirplaneType
    from dotenv import load_dotenv
    from tqdm import tqdm
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

# OpenFlights planes data URL
PLANES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat"
DATA_DIR = Path("data")
PLANES_FILE = DATA_DIR / "planes.dat"

def download_planes_data():
    """Download planes.dat from OpenFlights.org with progress bar"""
    print("🌐 Downloading aircraft data from OpenFlights.org...")
    
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    try:
        # Get file size for progress bar
        response = requests.head(PLANES_URL, timeout=10)
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress bar
        response = requests.get(PLANES_URL, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(PLANES_FILE, 'wb') as f:
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
        
        print(f"✅ Downloaded aircraft data to {PLANES_FILE}")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Failed to download aircraft data: {e}")
        return False

def analyze_planes_data():
    """Analyze the planes.dat file structure using Polars"""
    if not PLANES_FILE.exists():
        print(f"✗ Aircraft file not found: {PLANES_FILE}")
        return None
    
    print("Analyzing aircraft data structure...")
    
    # OpenFlights planes.dat format (CSV without headers):
    # Name, IATA code, ICAO code
    
    column_names = [
        "name",      # Full name of the aircraft
        "iata",      # IATA code (3 letters, can be \N)
        "icao"       # ICAO code (4 letters, can be \N)
    ]
    
    try:
        # Read CSV with Polars
        df = pl.read_csv(
            PLANES_FILE,
            has_header=False,
            new_columns=column_names,
            null_values=["\\N", ""],  # OpenFlights uses \N for NULL values
            encoding="utf8"
        )
        
        print(f"✓ Loaded {len(df)} aircraft types from OpenFlights data")
        print(f"Columns: {df.columns}")
        print(f"Shape: {df.shape}")
        
        # Show sample data
        print("\nSample data:")
        print(df.head(5))
        
        # Data quality analysis
        print("\nData Quality Analysis:")
        print(f"- Total aircraft types: {len(df)}")
        print(f"- Aircraft with IATA codes: {df.filter(pl.col('iata').is_not_null() & (pl.col('iata') != '')).height}")
        print(f"- Aircraft with ICAO codes: {df.filter(pl.col('icao').is_not_null() & (pl.col('icao') != '')).height}")
        print(f"- Aircraft with both codes: {df.filter((pl.col('iata').is_not_null() & (pl.col('iata') != '')) & (pl.col('icao').is_not_null() & (pl.col('icao') != ''))).height}")
        
        # Show some examples
        print("\nExamples:")
        boeing_747 = df.filter(pl.col('name').str.contains("Boeing 747"))
        if len(boeing_747) > 0:
            print("Boeing 747 variants:")
            for row in boeing_747.head(3).to_dicts():
                iata_display = f"IATA: {row['iata']}" if row['iata'] else "IATA: None"
                icao_display = f"ICAO: {row['icao']}" if row['icao'] else "ICAO: None"
                print(f"  {row['name']} - {iata_display}, {icao_display}")
        
        return df
        
    except Exception as e:
        print(f"✗ Failed to analyze aircraft data: {e}")
        return None

def validate_airplane_type_data(airplane_data):
    """Validate airplane type data before creating AirplaneType record"""
    errors = []
    warnings = []
    
    # Required fields validation
    name = airplane_data.get('name')
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        errors.append("Aircraft name is required")
    elif len(name.strip()) > 200:
        errors.append("Aircraft name must be 200 characters or less")
    
    # Optional field validation
    iata = airplane_data.get('iata')
    if iata and iata.strip():
        if not isinstance(iata, str) or len(iata.strip()) != 3:
            warnings.append("IATA code should be exactly 3 characters if provided")
        elif not iata.strip().isalnum():
            warnings.append("IATA code should contain only letters and numbers")
    
    icao = airplane_data.get('icao')
    if icao and icao.strip():
        if not isinstance(icao, str) or len(icao.strip()) != 4:
            warnings.append("ICAO code should be exactly 4 characters if provided")
        elif not icao.strip().isalnum():
            warnings.append("ICAO code should contain only letters and numbers")
    
    return errors, warnings

def prepare_airplane_type_data(df):
    """Prepare airplane type data for database insertion"""
    print("Preparing aircraft data for database insertion...")
    
    prepared_df = df.select([
        pl.col("name").str.strip_chars().alias("name"),
        pl.col("iata").str.strip_chars().alias("iata"),
        pl.col("icao").str.strip_chars().alias("icao")
    ]).filter(
        # Filter criteria for valid aircraft records:
        # 1. Must have name (required in AirplaneType model)
        (pl.col("name").is_not_null()) &
        (pl.col("name") != "") &
        (pl.col("name").str.len_chars() <= 200)
    ).with_columns([
        # Clean up IATA codes - set invalid codes to null
        pl.when(
            (pl.col("iata").is_not_null()) & 
            (pl.col("iata") != "") & 
            (pl.col("iata").str.len_chars() == 3) &
            (pl.col("iata").str.to_uppercase().str.contains(r"^[A-Z0-9]{3}$"))
        )
        .then(pl.col("iata").str.to_uppercase())
        .otherwise(None)
        .alias("iata"),
        
        # Clean up ICAO codes - set invalid codes to null
        pl.when(
            (pl.col("icao").is_not_null()) & 
            (pl.col("icao") != "") & 
            (pl.col("icao").str.len_chars() == 4) &
            (pl.col("icao").str.to_uppercase().str.contains(r"^[A-Z0-9]{4}$"))
        )
        .then(pl.col("icao").str.to_uppercase())
        .otherwise(None)
        .alias("icao")
    ])
    
    print(f"✓ Prepared {len(prepared_df)} aircraft types for database insertion")
    print(f"Data coverage:")
    print(f"  - Total aircraft types: {len(prepared_df)}")
    print(f"  - With IATA codes: {prepared_df.filter(pl.col('iata').is_not_null()).height}")
    print(f"  - With ICAO codes: {prepared_df.filter(pl.col('icao').is_not_null()).height}")
    print(f"  - With both codes: {prepared_df.filter((pl.col('iata').is_not_null()) & (pl.col('icao').is_not_null())).height}")
    
    return prepared_df

def create_airplane_type_record(airplane_data):
    """Create AirplaneType record from airplane data with validation"""
    # Validate airplane data first
    errors, warnings = validate_airplane_type_data(airplane_data)
    if errors:
        return None, errors
    
    try:
        # Create AirplaneType record
        airplane_type = AirplaneType(
            name=airplane_data['name'].strip(),
            iata=airplane_data.get('iata') if airplane_data.get('iata') else None,
            icao=airplane_data.get('icao') if airplane_data.get('icao') else None,
            data_source="OpenFlights"
        )
        
        return airplane_type, warnings
        
    except Exception as e:
        return None, [f"Error creating record: {str(e)}"]

def insert_airplane_types_to_database(df):
    """Insert airplane type data into the database with proper transaction handling"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available for database operations")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("Connected to database successfully!")
        
        with Session(db_manager.engine) as session:
            # Check existing airplane types to avoid duplicates
            existing_names = set()
            existing_airplane_types = session.exec(select(AirplaneType.name)).all()
            existing_names.update(existing_airplane_types)
            
            print(f"Found {len(existing_names)} existing aircraft types in database")
            
            # Convert Polars DataFrame to list of dictionaries
            airplane_types_data = df.to_dicts()
            
            inserted_count = 0
            skipped_count = 0
            error_count = 0
            warning_count = 0
            batch_size = 50  # Process in smaller batches for aircraft data
            
            print(f"Processing {len(airplane_types_data)} aircraft types in batches of {batch_size}...")
            
            # Process airplane types in batches for better transaction handling
            with tqdm(
                total=len(airplane_types_data),
                desc="✈️  Inserting aircraft",
                unit="aircraft",
                colour='blue',
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} ({percentage:3.0f}%) [{elapsed}<{remaining}]'
            ) as pbar:
                for batch_start in range(0, len(airplane_types_data), batch_size):
                    batch_end = min(batch_start + batch_size, len(airplane_types_data))
                    batch_data = airplane_types_data[batch_start:batch_end]
                    
                    # Process this batch with transaction handling
                    try:
                        batch_inserted = 0
                        batch_skipped = 0
                        batch_errors = 0
                        
                        for airplane_data in batch_data:
                            name = airplane_data.get('name')
                            
                            # Skip if airplane type already exists
                            if name and name in existing_names:
                                batch_skipped += 1
                                continue
                            
                            try:
                                # Create AirplaneType record with validation
                                airplane_type, issues = create_airplane_type_record(airplane_data)
                                
                                if airplane_type is None:
                                    if error_count < 10:  # Only show first 10 errors
                                        print(f"✗ Validation failed for {airplane_data.get('name', 'Unknown')}: {', '.join(issues)}")
                                    batch_errors += 1
                                    continue
                                
                                if issues:  # These are warnings
                                    warning_count += len(issues)
                                    if warning_count <= 10:  # Only show first 10 warnings
                                        print(f"⚠ Warning for {airplane_type.name}: {', '.join(issues)}")
                                
                                # Insert AirplaneType record
                                session.add(airplane_type)
                                session.flush()  # Get the type_id without committing the transaction
                                
                                if name:
                                    existing_names.add(name)  # Track to avoid duplicates in this batch
                                batch_inserted += 1
                                
                            except Exception as e:
                                if batch_errors < 5:  # Only show first 5 errors per batch
                                    print(f"✗ Error processing {airplane_data.get('name', 'Unknown')}: {e}")
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
                        print(f"✗ Batch transaction failed (aircraft {batch_start}-{batch_end}): {e}")
                        error_count += len(batch_data)
                        pbar.update(len(batch_data))
                        continue
            
            print(f"✓ Database insertion completed!")
            print(f"- Inserted: {inserted_count} new aircraft types")
            print(f"- Skipped: {skipped_count} existing aircraft types")
            print(f"- Errors: {error_count} aircraft types failed validation/insertion")
            print(f"- Warnings: {warning_count} data quality warnings")
            
            return True
            
    except Exception as e:
        print(f"✗ Database insertion failed: {e}")
        return False

def show_database_stats():
    """Show statistics about aircraft types in the database"""
    if not DEPENDENCIES_AVAILABLE:
        return
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        with Session(db_manager.engine) as session:
            # Count total aircraft types
            total_airplane_types = session.exec(select(AirplaneType)).all()
            total = len(total_airplane_types)
            
            if total == 0:
                print("📊 Database Statistics: No aircraft types found")
                return
            
            # Count aircraft types with various attributes
            with_iata = len([a for a in total_airplane_types if a.iata])
            with_icao = len([a for a in total_airplane_types if a.icao])
            with_both = len([a for a in total_airplane_types if a.iata and a.icao])
            
            print(f"📊 Database Statistics:")
            print(f"  Total aircraft types: {total:,}")
            print(f"  With IATA codes: {with_iata:,}")
            print(f"  With ICAO codes: {with_icao:,}")
            print(f"  With both codes: {with_both:,}")
            
            # Show sample aircraft types
            sample_airplane_types = session.exec(select(AirplaneType).limit(10)).all()
            
            print(f"\nSample aircraft types:")
            for airplane_type in sample_airplane_types:
                iata_display = f"IATA: {airplane_type.iata}" if airplane_type.iata else "IATA: None"
                icao_display = f"ICAO: {airplane_type.icao}" if airplane_type.icao else "ICAO: None"
                print(f"  {airplane_type.name} - {iata_display}, {icao_display}")
                
    except Exception as e:
        print(f"✗ Failed to get database statistics: {e}")

def main():
    """Main function to download and import aircraft data"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download and import aircraft data from OpenFlights.org')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output (default: progress bar only)')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Auto-confirm import without prompting')
    args = parser.parse_args()
    
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    if args.verbose:
        print("✈️  OpenFlights Aircraft Data Import")
        print("=" * 40)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        if args.verbose:
            print("⚠ .env file not found")
            print("Copy .env.example to .env and configure your database settings")
            print("You can still download and analyze data without database connection")
        
        if not args.yes:
            # Offer to continue without database import
            try:
                response = input("\nContinue with download and analysis only? (y/N): ").strip().lower()
                if response != 'y':
                    return False
            except KeyboardInterrupt:
                print("\nOperation cancelled")
                return False
    
    # Step 1: Download data
    if not PLANES_FILE.exists():
        if not download_planes_data():
            return False
    else:
        if args.verbose:
            print(f"✓ Aircraft data already exists: {PLANES_FILE}")
    
    # Step 2: Analyze data
    if args.verbose:
        df = analyze_planes_data()
    else:
        # Silent analysis for non-verbose mode
        try:
            column_names = ["name", "iata", "icao"]
            df = pl.read_csv(
                PLANES_FILE,
                has_header=False,
                new_columns=column_names,
                null_values=["\\N", ""],
                encoding="utf8"
            )
        except Exception as e:
            print(f"❌ Failed to analyze aircraft data: {e}")
            return False
    
    if df is None:
        return False
    
    # Step 3: Prepare data
    if args.verbose:
        prepared_df = prepare_airplane_type_data(df)
    else:
        # Silent preparation for non-verbose mode
        prepared_df = df.select([
            pl.col("name").str.strip_chars().alias("name"),
            pl.col("iata").str.strip_chars().alias("iata"),
            pl.col("icao").str.strip_chars().alias("icao")
        ]).filter(
            (pl.col("name").is_not_null()) &
            (pl.col("name") != "") &
            (pl.col("name").str.len_chars() <= 200)
        )
    
    if len(prepared_df) == 0:
        print("❌ No suitable aircraft data found")
        return False
    
    # Step 4: Insert into database (if .env exists)
    if os.path.exists('.env'):
        if args.verbose:
            print(f"\nFound {len(prepared_df):,} aircraft types ready for import")
        
        if args.yes:
            # Auto-import
            if args.verbose:
                print("Importing aircraft types into database...")
            if not insert_airplane_types_to_database(prepared_df):
                return False
        else:
            # Ask user what to do
            if args.verbose:
                print("What would you like to do?")
                print("  y = Import aircraft types into database")
                print("  s = Show current database statistics only")
                
                choice = input("\nChoice (y/s): ").strip().lower()
            else:
                choice = input("Import aircraft types into database? (y/N): ").strip().lower()
            
            if choice == 's' and args.verbose:
                show_database_stats()
                return True
            elif choice == 'y':
                if args.verbose:
                    print("Importing aircraft types into database...")
                if not insert_airplane_types_to_database(prepared_df):
                    return False
            else:
                if args.verbose:
                    print("Invalid choice. Showing statistics only.")
                    show_database_stats()
                else:
                    print("Operation cancelled")
                return True
        
        if args.verbose:
            print("\n" + "=" * 50)
            show_database_stats()
            print("\n🎉 Aircraft data import completed successfully!")
        else:
            print("✅ Aircraft types imported successfully!")
    else:
        if args.verbose:
            print(f"\n✓ Data analysis completed! {len(prepared_df)} aircraft types ready for import")
            print("Configure .env file and run again to import into database")
        else:
            print("❌ .env file not found - configure database settings")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)