#!/usr/bin/env python3
"""
Download and import routes data from OpenFlights.org
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
    from models.route import Route
    from dotenv import load_dotenv
    from tqdm import tqdm
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

# OpenFlights routes data URL
ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"
DATA_DIR = Path("data")
ROUTES_FILE = DATA_DIR / "routes.dat"

def download_routes_data():
    """Download routes.dat from OpenFlights.org with progress bar"""
    print("🌐 Downloading routes data from OpenFlights.org...")
    
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    try:
        # Get file size for progress bar
        response = requests.head(ROUTES_URL, timeout=10)
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress bar
        response = requests.get(ROUTES_URL, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(ROUTES_FILE, 'wb') as f:
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
        
        print(f"✅ Downloaded routes data to {ROUTES_FILE}")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Failed to download routes data: {e}")
        return False

def analyze_routes_data():
    """Analyze the routes.dat file structure using Polars"""
    if not ROUTES_FILE.exists():
        print(f"✗ Routes file not found: {ROUTES_FILE}")
        return None
    
    print("Analyzing routes data structure...")
    
    # OpenFlights routes.dat format (CSV without headers):
    # Airline, Airline ID, Source airport, Source airport ID, Destination airport, 
    # Destination airport ID, Codeshare, Stops, Equipment
    
    column_names = [
        "airline_code",
        "airline_id_openflights",
        "source_airport_code", 
        "source_airport_id_openflights",
        "destination_airport_code",
        "destination_airport_id_openflights",
        "codeshare",
        "stops",
        "equipment"
    ]
    
    try:
        # Read CSV with Polars
        df = pl.read_csv(
            ROUTES_FILE,
            has_header=False,
            new_columns=column_names,
            null_values=["\\N", ""],  # OpenFlights uses \N for NULL values
            encoding="utf8"
        )
        
        print(f"✓ Loaded {len(df)} routes from OpenFlights data")
        print(f"Columns: {df.columns}")
        print(f"Shape: {df.shape}")
        
        # Show sample data
        print("\nSample data:")
        print(df.head(3))
        
        # Data quality analysis
        print("\nData Quality Analysis:")
        print(f"- Total routes: {len(df)}")
        print(f"- Routes with airline codes: {df.filter(pl.col('airline_code').is_not_null() & (pl.col('airline_code') != '')).height}")
        print(f"- Routes with source airport codes: {df.filter(pl.col('source_airport_code').is_not_null() & (pl.col('source_airport_code') != '')).height}")
        print(f"- Routes with destination airport codes: {df.filter(pl.col('destination_airport_code').is_not_null() & (pl.col('destination_airport_code') != '')).height}")
        print(f"- Codeshare routes: {df.filter(pl.col('codeshare') == 'Y').height}")
        print(f"- Direct routes (0 stops): {df.filter(pl.col('stops') == 0).height}")
        print(f"- Routes with equipment info: {df.filter(pl.col('equipment').is_not_null() & (pl.col('equipment') != '')).height}")
        
        return df
        
    except Exception as e:
        print(f"✗ Failed to analyze routes data: {e}")
        return None

def validate_route_data(route_data):
    """Validate route data before creating Route record"""
    errors = []
    warnings = []
    
    # Check if we have at least airline and airport information
    airline_code = route_data.get('airline_code')
    source_code = route_data.get('source_airport_code')
    dest_code = route_data.get('destination_airport_code')
    
    if not airline_code or not isinstance(airline_code, str) or len(airline_code.strip()) == 0:
        errors.append("Airline code is required")
    
    if not source_code or not isinstance(source_code, str) or len(source_code.strip()) == 0:
        errors.append("Source airport code is required")
    
    if not dest_code or not isinstance(dest_code, str) or len(dest_code.strip()) == 0:
        errors.append("Destination airport code is required")
    
    # Validate airline ID
    airline_id = route_data.get('airline_id_openflights')
    if airline_id is not None:
        try:
            int(airline_id)
        except (ValueError, TypeError):
            warnings.append("Invalid airline OpenFlights ID")
    
    # Validate airport IDs
    source_id = route_data.get('source_airport_id_openflights')
    if source_id is not None:
        try:
            int(source_id)
        except (ValueError, TypeError):
            warnings.append("Invalid source airport OpenFlights ID")
    
    dest_id = route_data.get('destination_airport_id_openflights')
    if dest_id is not None:
        try:
            int(dest_id)
        except (ValueError, TypeError):
            warnings.append("Invalid destination airport OpenFlights ID")
    
    # Validate stops
    stops = route_data.get('stops')
    if stops is not None:
        try:
            stops_int = int(stops)
            if stops_int < 0:
                warnings.append("Stops cannot be negative")
        except (ValueError, TypeError):
            warnings.append("Invalid stops value")
    
    # Validate equipment length
    equipment = route_data.get('equipment')
    if equipment and len(str(equipment)) > 200:
        errors.append("Equipment must be 200 characters or less")
    
    return errors, warnings

def prepare_route_data(df):
    """Prepare route data for database insertion"""
    print("Preparing route data for database insertion...")
    
    prepared_df = df.select([
        pl.col("airline_code").str.strip_chars().alias("airline_code"),
        pl.col("airline_id_openflights").alias("airline_id_openflights"),
        pl.col("source_airport_code").str.strip_chars().alias("source_airport_code"),
        pl.col("source_airport_id_openflights").alias("source_airport_id_openflights"),
        pl.col("destination_airport_code").str.strip_chars().alias("destination_airport_code"),
        pl.col("destination_airport_id_openflights").alias("destination_airport_id_openflights"),
        pl.col("codeshare").alias("codeshare"),
        pl.col("stops").alias("stops"),
        pl.col("equipment").str.strip_chars().alias("equipment")
    ]).filter(
        # Filter criteria for valid route records:
        # Must have airline code, source airport code, and destination airport code
        (pl.col("airline_code").is_not_null()) &
        (pl.col("airline_code") != "") &
        (pl.col("source_airport_code").is_not_null()) &
        (pl.col("source_airport_code") != "") &
        (pl.col("destination_airport_code").is_not_null()) &
        (pl.col("destination_airport_code") != "")
    ).with_columns([
        # Clean up airline code
        pl.when(
            (pl.col("airline_code").is_not_null()) & 
            (pl.col("airline_code") != "") &
            (pl.col("airline_code").str.len_chars() <= 3)
        )
        .then(pl.col("airline_code").str.to_uppercase())
        .otherwise(None)
        .alias("airline_code"),
        
        # Clean up airport codes
        pl.when(
            (pl.col("source_airport_code").is_not_null()) & 
            (pl.col("source_airport_code") != "") &
            (pl.col("source_airport_code").str.len_chars() <= 4)
        )
        .then(pl.col("source_airport_code").str.to_uppercase())
        .otherwise(None)
        .alias("source_airport_code"),
        
        pl.when(
            (pl.col("destination_airport_code").is_not_null()) & 
            (pl.col("destination_airport_code") != "") &
            (pl.col("destination_airport_code").str.len_chars() <= 4)
        )
        .then(pl.col("destination_airport_code").str.to_uppercase())
        .otherwise(None)
        .alias("destination_airport_code"),
        
        # Convert codeshare to boolean
        pl.when(pl.col("codeshare") == "Y")
        .then(True)
        .otherwise(False)
        .alias("codeshare"),
        
        # Convert stops to integer (it's already an integer from CSV parsing)
        pl.when(pl.col("stops").is_not_null())
        .then(pl.col("stops"))
        .otherwise(0)
        .alias("stops"),
        
        # Clean up equipment field
        pl.when(
            (pl.col("equipment").is_not_null()) & 
            (pl.col("equipment") != "") &
            (pl.col("equipment").str.len_chars() <= 200)
        )
        .then(pl.col("equipment"))
        .otherwise(None)
        .alias("equipment"),
        
        # OpenFlights IDs are already integers from CSV parsing
        pl.col("airline_id_openflights"),
        pl.col("source_airport_id_openflights"),
        pl.col("destination_airport_id_openflights")
    ])
    
    print(f"✓ Prepared {len(prepared_df)} routes for database insertion")
    print(f"Data coverage:")
    print(f"  - Total routes: {len(prepared_df)}")
    print(f"  - Codeshare routes: {prepared_df.filter(pl.col('codeshare') == True).height}")
    print(f"  - Direct routes: {prepared_df.filter(pl.col('stops') == 0).height}")
    print(f"  - With equipment info: {prepared_df.filter(pl.col('equipment').is_not_null()).height}")
    print(f"  - With airline IDs: {prepared_df.filter(pl.col('airline_id_openflights').is_not_null()).height}")
    
    return prepared_df

def create_route_record(route_data):
    """Create Route record from route data with validation"""
    # Validate route data first
    errors, warnings = validate_route_data(route_data)
    if errors:
        return None, errors
    
    try:
        # Create Route record
        route = Route(
            airline_code=route_data['airline_code'],
            airline_id_openflights=route_data.get('airline_id_openflights'),
            source_airport_code=route_data['source_airport_code'],
            source_airport_id_openflights=route_data.get('source_airport_id_openflights'),
            destination_airport_code=route_data['destination_airport_code'],
            destination_airport_id_openflights=route_data.get('destination_airport_id_openflights'),
            codeshare=route_data.get('codeshare', False),
            stops=route_data.get('stops', 0),
            equipment=route_data.get('equipment'),
            data_source="OpenFlights"
        )
        
        return route, warnings
        
    except Exception as e:
        return None, [f"Error creating record: {str(e)}"]

def insert_routes_to_database(df):
    """Insert route data into the database with proper transaction handling"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available for database operations")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("Connected to database successfully!")
        
        with Session(db_manager.engine) as session:
            # Check existing routes count
            existing_routes = session.exec(select(Route)).all()
            existing_count = len(existing_routes)
            
            print(f"Found {existing_count} existing routes in database")
            
            # Convert Polars DataFrame to list of dictionaries
            routes_data = df.to_dicts()
            
            inserted_count = 0
            error_count = 0
            warning_count = 0
            batch_size = 1000  # Process in larger batches for routes
            
            print(f"Processing {len(routes_data)} routes in batches of {batch_size}...")
            
            # Process routes in batches for better transaction handling
            with tqdm(
                total=len(routes_data),
                desc="🛫 Inserting routes",
                unit="routes",
                colour='blue',
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} ({percentage:3.0f}%) [{elapsed}<{remaining}]'
            ) as pbar:
                for batch_start in range(0, len(routes_data), batch_size):
                    batch_end = min(batch_start + batch_size, len(routes_data))
                    batch_data = routes_data[batch_start:batch_end]
                    
                    # Process this batch with transaction handling
                    try:
                        batch_inserted = 0
                        batch_errors = 0
                        
                        for route_data in batch_data:
                            try:
                                # Create Route record with validation
                                route, issues = create_route_record(route_data)
                                
                                if route is None:
                                    if error_count < 10:  # Only show first 10 errors
                                        airline = route_data.get('airline_code', 'Unknown')
                                        source = route_data.get('source_airport_code', 'Unknown')
                                        dest = route_data.get('destination_airport_code', 'Unknown')
                                        print(f"✗ Validation failed for {airline} {source}->{dest}: {', '.join(issues)}")
                                    batch_errors += 1
                                    continue
                                
                                if issues:  # These are warnings
                                    warning_count += len(issues)
                                    if warning_count <= 10:  # Only show first 10 warnings
                                        airline = route.airline_code
                                        source = route.source_airport_code
                                        dest = route.destination_airport_code
                                        print(f"⚠ Warning for {airline} {source}->{dest}: {', '.join(issues)}")
                                
                                # Insert Route record
                                session.add(route)
                                batch_inserted += 1
                                
                            except Exception as e:
                                if batch_errors < 5:  # Only show first 5 errors per batch
                                    airline = route_data.get('airline_code', 'Unknown')
                                    source = route_data.get('source_airport_code', 'Unknown')
                                    dest = route_data.get('destination_airport_code', 'Unknown')
                                    print(f"✗ Error processing {airline} {source}->{dest}: {e}")
                                batch_errors += 1
                                continue
                        
                        # Commit the entire batch transaction
                        session.commit()
                        
                        # Update counters
                        inserted_count += batch_inserted
                        error_count += batch_errors
                        
                        # Update progress bar
                        pbar.update(len(batch_data))
                        pbar.set_postfix({
                            'Inserted': inserted_count,
                            'Errors': error_count
                        })
                            
                    except Exception as e:
                        # Rollback the entire batch on any error
                        session.rollback()
                        print(f"✗ Batch transaction failed (routes {batch_start}-{batch_end}): {e}")
                        error_count += len(batch_data)
                        pbar.update(len(batch_data))
                        continue
            
            print(f"✓ Database insertion completed!")
            print(f"- Inserted: {inserted_count} new routes")
            print(f"- Errors: {error_count} routes failed validation/insertion")
            print(f"- Warnings: {warning_count} data quality warnings")
            
            return True
            
    except Exception as e:
        print(f"✗ Database insertion failed: {e}")
        return False

def show_database_stats():
    """Show statistics about routes in the database"""
    if not DEPENDENCIES_AVAILABLE:
        return
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        with Session(db_manager.engine) as session:
            # Count total routes
            total_routes = session.exec(select(Route)).all()
            total = len(total_routes)
            
            if total == 0:
                print("📊 Database Statistics: No routes found")
                return
            
            # Count routes with various attributes
            codeshare_routes = len([r for r in total_routes if r.codeshare])
            direct_routes = len([r for r in total_routes if r.stops == 0])
            with_equipment = len([r for r in total_routes if r.equipment])
            
            print(f"📊 Database Statistics:")
            print(f"  Total routes: {total:,}")
            print(f"  Codeshare routes: {codeshare_routes:,}")
            print(f"  Direct routes: {direct_routes:,}")
            print(f"  With equipment info: {with_equipment:,}")
            
            # Show sample routes
            sample_routes = session.exec(select(Route).limit(5)).all()
            
            print(f"\nSample routes:")
            for route in sample_routes:
                codeshare_display = " (Codeshare)" if route.codeshare else ""
                stops_display = f" ({route.stops} stops)" if route.stops > 0 else " (Direct)"
                equipment_display = f" [{route.equipment}]" if route.equipment else ""
                print(f"  {route.airline_code}: {route.source_airport_code} → {route.destination_airport_code}{codeshare_display}{stops_display}{equipment_display}")
                
    except Exception as e:
        print(f"✗ Failed to get database statistics: {e}")

def main():
    """Main function to download and import routes data"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    print("🛫 OpenFlights Routes Data Import")
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
    if not ROUTES_FILE.exists():
        if not download_routes_data():
            return False
    else:
        print(f"✓ Routes data already exists: {ROUTES_FILE}")
    
    # Step 2: Analyze data
    df = analyze_routes_data()
    if df is None:
        return False
    
    # Step 3: Prepare data
    prepared_df = prepare_route_data(df)
    if len(prepared_df) == 0:
        print("✗ No suitable route data found")
        return False
    
    # Step 4: Insert into database (if .env exists)
    if os.path.exists('.env'):
        print(f"\nFound {len(prepared_df):,} routes ready for import")
        
        # Ask user what to do
        print("What would you like to do?")
        print("  y = Import routes into database")
        print("  s = Show current database statistics only")
        
        choice = input("\nChoice (y/s): ").strip().lower()
        
        if choice == 's':
            show_database_stats()
            return True
        elif choice == 'y':
            print("Importing routes into database...")
            if not insert_routes_to_database(prepared_df):
                return False
            print("\n" + "=" * 50)
            show_database_stats()
            print("\n🎉 Routes data import completed successfully!")
        else:
            print("Invalid choice. Showing statistics only.")
            show_database_stats()
    else:
        print(f"\n✓ Data analysis completed! {len(prepared_df)} routes ready for import")
        print("Configure .env file and run again to import into database")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)