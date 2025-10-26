#!/usr/bin/env python3
"""
Download and import airports data from OpenFlights.org
"""

import sys
import os
import requests
import argparse
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import polars as pl
    from sqlmodel import Session, select
    from models.database import DatabaseManager
    from models import Airport, AirportGeo, Country
    from models.airport import AirportType
    from models.airport_geo import DSTType
    from dotenv import load_dotenv
    from tqdm import tqdm
    from decimal import Decimal
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

# OpenFlights airports data URL
AIRPORTS_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
DATA_DIR = Path("data")
AIRPORTS_FILE = DATA_DIR / "airports.dat"

def download_airports_data():
    """Download airports.dat from OpenFlights.org with progress bar"""
    print("🌐 Downloading airports data from OpenFlights.org...")
    
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    try:
        # Get file size for progress bar
        response = requests.head(AIRPORTS_URL, timeout=10)
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress bar
        response = requests.get(AIRPORTS_URL, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(AIRPORTS_FILE, 'wb') as f:
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
        
        print(f"✅ Downloaded airports data to {AIRPORTS_FILE}")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Failed to download airports data: {e}")
        return False

def analyze_airports_data(verbose=False):
    """Analyze the airports.dat file structure using Polars"""
    if not AIRPORTS_FILE.exists():
        print(f"✗ Airports file not found: {AIRPORTS_FILE}")
        return None
    
    if verbose:
        print("Analyzing airports data structure...")
    
    # OpenFlights airports.dat format (CSV without headers):
    # Airport ID, Name, City, Country, IATA, ICAO, Latitude, Longitude, 
    # Altitude, Timezone, DST, Tz database time zone, Type, Source
    
    column_names = [
        "airport_id_openflights",  # OpenFlights ID (different from our DB ID)
        "name",
        "city", 
        "country",
        "iata",
        "icao",
        "latitude",
        "longitude",
        "altitude",
        "timezone_offset",
        "dst",
        "timezone_name",
        "type",
        "source"
    ]
    
    try:
        # Read CSV with Polars
        df = pl.read_csv(
            AIRPORTS_FILE,
            has_header=False,
            new_columns=column_names,
            null_values=["\\N", ""],  # OpenFlights uses \N for NULL values
            encoding="utf8"
        )
        
        print(f"✓ Loaded {len(df)} airports from OpenFlights data")
        
        if verbose:
            print(f"Columns: {df.columns}")
            print(f"Shape: {df.shape}")
            
            # Show sample data
            print("\nSample data:")
            print(df.head(3))
            
            # Data quality analysis
            print("\nData Quality Analysis:")
            print(f"- Total airports: {len(df)}")
            print(f"- Airports with IATA codes: {df.filter(pl.col('iata').is_not_null()).height}")
            print(f"- Airports with ICAO codes: {df.filter(pl.col('icao').is_not_null()).height}")
            print(f"- Unique countries: {df['country'].n_unique()}")
            print(f"- Airport types: {df['type'].value_counts()}")
            
            # Filter for airports (exclude heliports, seaplane bases, etc.)
            airports_only = df.filter(pl.col('type') == 'airport')
            print(f"- Airports only (excluding heliports, etc.): {len(airports_only)}")
        
        return df
        
    except Exception as e:
        print(f"✗ Failed to analyze airports data: {e}")
        return None

def validate_core_airport_data(airport_data):
    """Validate core airport data before creating Airport record"""
    errors = []
    
    # Required fields validation
    icao = airport_data.get('icao')
    if not icao or not isinstance(icao, str) or len(icao.strip()) != 4:
        errors.append("ICAO code must be exactly 4 characters")
    elif not icao.strip().isalnum():
        errors.append("ICAO code must contain only letters and numbers")
    
    name = airport_data.get('name')
    if not name or not isinstance(name, str) or len(name.strip()) == 0:
        errors.append("Airport name is required")
    elif len(name.strip()) > 200:
        errors.append("Airport name must be 200 characters or less")
    
    # Optional field validation
    iata = airport_data.get('iata')
    if iata:
        if not isinstance(iata, str) or len(iata.strip()) != 3:
            errors.append("IATA code must be exactly 3 characters if provided")
    # Note: IATA codes are typically all letters, but some may have numbers
    
    # Airport type validation
    airport_type = airport_data.get('airport_type', '').lower()
    valid_types = [e.value for e in AirportType]
    if airport_type and airport_type not in valid_types:
        errors.append(f"Invalid airport type: {airport_type}. Valid types: {', '.join(valid_types)}")
    
    # Data source validation
    data_source = airport_data.get('data_source')
    if data_source and len(str(data_source)) > 50:
        errors.append("Data source must be 50 characters or less")
    
    # OpenFlights ID validation
    openflights_id = airport_data.get('openflights_id')
    if openflights_id is not None:
        try:
            int(openflights_id)
        except (ValueError, TypeError):
            errors.append("OpenFlights ID must be a valid integer")
    
    return errors

def validate_geographic_data(airport_data):
    """Validate geographic data before creating AirportGeo record"""
    errors = []
    warnings = []
    
    # City and country validation
    city = airport_data.get('city')
    if city and len(str(city)) > 100:
        errors.append("City name must be 100 characters or less")
    
    country = airport_data.get('country')
    if country and len(str(country)) > 100:
        errors.append("Country name must be 100 characters or less")
    
    # Coordinate validation
    latitude = airport_data.get('latitude')
    longitude = airport_data.get('longitude')
    
    if latitude is not None:
        try:
            lat_val = float(latitude)
            if not -90 <= lat_val <= 90:
                errors.append(f"Latitude must be between -90 and 90, got {lat_val}")
            # Check for obviously invalid coordinates (0,0 is suspicious for airports)
            if lat_val == 0.0 and longitude is not None and float(longitude) == 0.0:
                warnings.append("Coordinates (0,0) may indicate missing data")
        except (ValueError, TypeError):
            errors.append(f"Invalid latitude value: {latitude}")
    
    if longitude is not None:
        try:
            lon_val = float(longitude)
            if not -180 <= lon_val <= 180:
                errors.append(f"Longitude must be between -180 and 180, got {lon_val}")
        except (ValueError, TypeError):
            errors.append(f"Invalid longitude value: {longitude}")
    
    # Validate coordinate pairs - if one is provided, both should be
    if (latitude is not None) != (longitude is not None):
        warnings.append("Incomplete coordinate pair - both latitude and longitude should be provided")
    
    # Altitude validation
    altitude = airport_data.get('altitude')
    if altitude is not None:
        try:
            alt_val = int(altitude)
            if alt_val < -1500:  # Below Dead Sea level
                warnings.append(f"Very low altitude: {alt_val} feet")
            elif alt_val > 20000:  # Above reasonable airport altitude
                warnings.append(f"Very high altitude: {alt_val} feet")
        except (ValueError, TypeError):
            errors.append(f"Invalid altitude value: {altitude}")
    
    # Timezone offset validation
    timezone_offset = airport_data.get('timezone_offset')
    if timezone_offset is not None:
        try:
            tz_val = float(timezone_offset)
            if not -12 <= tz_val <= 14:  # Valid timezone range
                errors.append(f"Timezone offset must be between -12 and 14, got {tz_val}")
            # Check for half-hour and quarter-hour offsets
            if tz_val % 0.25 != 0:
                warnings.append(f"Unusual timezone offset: {tz_val} (not a quarter-hour increment)")
        except (ValueError, TypeError):
            errors.append(f"Invalid timezone offset value: {timezone_offset}")
    
    # DST validation
    dst = airport_data.get('dst')
    if dst:
        valid_dst_values = [e.value for e in DSTType]
        if dst not in valid_dst_values:
            errors.append(f"Invalid DST value: {dst}. Valid values: {', '.join(valid_dst_values)}")
    
    # Timezone name validation
    timezone_name = airport_data.get('timezone_name')
    if timezone_name and len(str(timezone_name)) > 50:
        errors.append("Timezone name must be 50 characters or less")
    
    return errors, warnings

def prepare_airport_data(df, verbose=False):
    """Prepare airport data for database insertion with normalized schema"""
    if verbose:
        print("Preparing airport data for normalized database insertion...")
    
    # Split data preparation into core airport data and geographic data
    prepared_df = df.select([
        # Core airport fields (for Airport table)
        pl.col("airport_id_openflights").alias("openflights_id"),
        pl.col("iata").str.strip_chars().alias("iata"),
        pl.col("icao").str.strip_chars().alias("icao"), 
        pl.col("name").str.strip_chars().alias("name"),
        pl.col("type").str.strip_chars().alias("airport_type"),
        pl.col("source").str.strip_chars().alias("data_source"),
        
        # Geographic fields (for AirportGeo table)
        pl.col("city").str.strip_chars().alias("city"),
        pl.col("country").str.strip_chars().alias("country"),
        pl.col("latitude").alias("latitude"),
        pl.col("longitude").alias("longitude"),
        pl.col("altitude").alias("altitude"),
        pl.col("timezone_offset").alias("timezone_offset"),
        pl.col("dst").str.strip_chars().alias("dst"),
        pl.col("timezone_name").str.strip_chars().alias("timezone_name")
    ]).filter(
        # Filter criteria for valid airport records:
        # 1. Must have ICAO code (required in Airport model)
        # 2. Must have name (required in Airport model)  
        # 3. Prefer airports over other types (heliports, seaplane bases, etc.)
        (pl.col("icao").is_not_null()) &
        (pl.col("icao") != "") &
        (pl.col("icao").str.len_chars() == 4) &  # ICAO must be exactly 4 characters
        (pl.col("name").is_not_null()) &
        (pl.col("name") != "") &
        (pl.col("airport_type") == "airport")
    ).with_columns([
        # Clean up IATA codes - set invalid codes to null
        pl.when(
            (pl.col("iata").is_not_null()) & 
            (pl.col("iata") != "") & 
            (pl.col("iata").str.len_chars() == 3)
        )
        .then(pl.col("iata").str.to_uppercase())
        .otherwise(None)
        .alias("iata"),
        
        # Ensure ICAO codes are uppercase
        pl.col("icao").str.to_uppercase().alias("icao"),
        
        # Clean up geographic text fields
        pl.when(
            (pl.col("city").is_not_null()) & 
            (pl.col("city") != "") &
            (pl.col("city").str.len_chars() <= 100)
        )
        .then(pl.col("city"))
        .otherwise(None)
        .alias("city"),
        
        pl.when(
            (pl.col("country").is_not_null()) & 
            (pl.col("country") != "") &
            (pl.col("country").str.len_chars() <= 100)
        )
        .then(pl.col("country"))
        .otherwise(None)
        .alias("country"),
        
        # Clean up timezone and DST fields
        pl.when(
            (pl.col("timezone_name").is_not_null()) & 
            (pl.col("timezone_name") != "") &
            (pl.col("timezone_name").str.len_chars() <= 50)
        )
        .then(pl.col("timezone_name"))
        .otherwise(None)
        .alias("timezone_name"),
        
        pl.when(
            (pl.col("dst").is_not_null()) & 
            (pl.col("dst") != "") &
            (pl.col("dst").str.len_chars() == 1)
        )
        .then(pl.col("dst").str.to_uppercase())
        .otherwise(None)
        .alias("dst"),
        
        # Validate numeric fields
        pl.when(
            (pl.col("latitude").is_not_null()) &
            (pl.col("latitude").is_between(-90, 90))
        )
        .then(pl.col("latitude"))
        .otherwise(None)
        .alias("latitude"),
        
        pl.when(
            (pl.col("longitude").is_not_null()) &
            (pl.col("longitude").is_between(-180, 180))
        )
        .then(pl.col("longitude"))
        .otherwise(None)
        .alias("longitude"),
        
        pl.when(
            (pl.col("altitude").is_not_null()) &
            (pl.col("altitude").is_between(-2000, 25000))  # Reasonable altitude range
        )
        .then(pl.col("altitude"))
        .otherwise(None)
        .alias("altitude"),
        
        pl.when(
            (pl.col("timezone_offset").is_not_null()) &
            (pl.col("timezone_offset").is_between(-12, 14))
        )
        .then(pl.col("timezone_offset"))
        .otherwise(None)
        .alias("timezone_offset")
    ])
    
    print(f"✓ Prepared {len(prepared_df)} airports for normalized database insertion")
    
    if verbose:
        print(f"Core airport data:")
        print(f"  - Total airports: {len(prepared_df)}")
        print(f"  - With IATA codes: {prepared_df.filter(pl.col('iata').is_not_null()).height}")
        print(f"  - All have ICAO codes: {prepared_df.filter(pl.col('icao').is_not_null()).height}")
        print(f"Geographic data coverage:")
        print(f"  - With coordinates: {prepared_df.filter((pl.col('latitude').is_not_null()) & (pl.col('longitude').is_not_null())).height}")
        print(f"  - With altitude data: {prepared_df.filter(pl.col('altitude').is_not_null()).height}")
        print(f"  - With timezone data: {prepared_df.filter(pl.col('timezone_name').is_not_null()).height}")
        print(f"  - With city/country: {prepared_df.filter((pl.col('city').is_not_null()) & (pl.col('country').is_not_null())).height}")
    
    return prepared_df

def find_country_by_name(country_name, session):
    """Find country in database by name with fuzzy matching and ISO code fallback"""
    from models.country import Country
    from utils.iso_country_codes import get_iso_a3_from_iso_a2, get_iso_a2_from_iso_a3, validate_iso_a3, validate_iso_a2
    
    if not country_name:
        return None, None, None
    
    country_name = country_name.strip()
    
    # First try exact name match
    country = session.exec(select(Country).where(Country.name == country_name)).first()
    if country:
        iso_a2 = get_iso_a2_from_iso_a3(country.iso_a3) if country.iso_a3 else None
        return country.country_id, country.iso_a3, iso_a2
    
    # Try case-insensitive match
    country = session.exec(select(Country).where(Country.name.ilike(country_name))).first()
    if country:
        iso_a2 = get_iso_a2_from_iso_a3(country.iso_a3) if country.iso_a3 else None
        return country.country_id, country.iso_a3, iso_a2
    
    # Check if the country name is actually an ISO code
    if len(country_name) == 2 and validate_iso_a2(country_name):
        # It's an ISO A2 code, convert to A3 and look up
        iso_a3 = get_iso_a3_from_iso_a2(country_name)
        if iso_a3:
            country = session.exec(select(Country).where(Country.iso_a3 == iso_a3)).first()
            if country:
                return country.country_id, country.iso_a3, country_name.upper()
    
    elif len(country_name) == 3 and validate_iso_a3(country_name):
        # It's an ISO A3 code, look up directly
        country = session.exec(select(Country).where(Country.iso_a3 == country_name.upper())).first()
        if country:
            iso_a2 = get_iso_a2_from_iso_a3(country_name.upper())
            return country.country_id, country.iso_a3, iso_a2
    
    # Try some common name variations
    name_variations = {
        "United States": ["USA", "United States of America"],
        "United Kingdom": ["UK", "Great Britain", "Britain"],
        "Russia": ["Russian Federation"],
        "South Korea": ["Korea, South", "Republic of Korea"],
        "North Korea": ["Korea, North", "Democratic People's Republic of Korea"],
        "Iran": ["Islamic Republic of Iran"],
        "Syria": ["Syrian Arab Republic"],
        "Venezuela": ["Bolivarian Republic of Venezuela"],
        "Bolivia": ["Plurinational State of Bolivia"],
        "Tanzania": ["United Republic of Tanzania"],
        "Macedonia": ["North Macedonia", "Former Yugoslav Republic of Macedonia"],
        "Congo": ["Republic of the Congo", "Congo-Brazzaville"],
        "Democratic Republic of the Congo": ["Congo, Democratic Republic of the", "Congo-Kinshasa"],
        "Ivory Coast": ["Côte d'Ivoire", "Cote d'Ivoire"],
        "Cape Verde": ["Cabo Verde"],
        "Swaziland": ["Eswatini"],
        "Burma": ["Myanmar"],
        "East Timor": ["Timor-Leste"],
        "Czech Republic": ["Czechia"],
    }
    
    # Check variations
    for standard_name, variations in name_variations.items():
        if country_name in variations or country_name == standard_name:
            # Try to find the standard name or any variation
            for name_to_try in [standard_name] + variations:
                country = session.exec(select(Country).where(Country.name.ilike(name_to_try))).first()
                if country:
                    iso_a2 = get_iso_a2_from_iso_a3(country.iso_a3) if country.iso_a3 else None
                    return country.country_id, country.iso_a3, iso_a2
    
    # Check if any country name contains the search term (partial match)
    country = session.exec(select(Country).where(Country.name.ilike(f"%{country_name}%"))).first()
    if country:
        iso_a2 = get_iso_a2_from_iso_a3(country.iso_a3) if country.iso_a3 else None
        return country.country_id, country.iso_a3, iso_a2
    
    return None, None, None

def create_airport_and_geo_records(airport_data, session):
    """Create Airport and AirportGeo records from airport data with comprehensive validation"""
    # Validate core airport data first
    core_errors = validate_core_airport_data(airport_data)
    if core_errors:
        return None, None, core_errors
    
    # Validate geographic data
    geo_errors, geo_warnings = validate_geographic_data(airport_data)
    if geo_errors:
        return None, None, geo_errors
    
    try:
        # Create Airport record (core operational data only)
        airport = Airport(
            iata=airport_data.get('iata') if airport_data.get('iata') else None,
            icao=airport_data['icao'].upper(),
            name=airport_data['name'].strip(),
            airport_type=AirportType(airport_data.get('airport_type', 'airport')),
            data_source=airport_data.get('data_source'),
            openflights_id=int(airport_data['openflights_id']) if airport_data.get('openflights_id') is not None else None
        )
        
        # Look up country ID and ISO codes using improved matching
        country_id = None
        country_iso_a3 = None
        country_iso_a2 = None
        country_name = airport_data.get('country')
        
        if country_name:
            country_id, country_iso_a3, country_iso_a2 = find_country_by_name(country_name, session)
            if not country_id:
                geo_warnings.append(f"Country '{country_name}' not found in database - skipping geographic data")
        else:
            geo_warnings.append("No country specified - skipping geographic data")
        
        # Create AirportGeo record only if we have a valid country_id (now required)
        airport_geo = None
        if country_id is not None:
            airport_geo = AirportGeo(
                airport_id=None,  # Will be set after airport is saved
                city=airport_data.get('city') if airport_data.get('city') else None,
                country=country_name,  # Store raw country name from airports.dat
                country_id=country_id,
                iso_a2=country_iso_a2,  # 2-letter ISO country code
                iso_a3=country_iso_a3,  # 3-letter ISO country code
                latitude=Decimal(str(airport_data['latitude'])) if airport_data.get('latitude') is not None else None,
                longitude=Decimal(str(airport_data['longitude'])) if airport_data.get('longitude') is not None else None,
                altitude=int(airport_data['altitude']) if airport_data.get('altitude') is not None else None,
                timezone_offset=Decimal(str(airport_data['timezone_offset'])) if airport_data.get('timezone_offset') is not None else None,
                dst=DSTType(airport_data['dst']) if airport_data.get('dst') and airport_data['dst'] in [e.value for e in DSTType] else None,
                timezone_name=airport_data.get('timezone_name') if airport_data.get('timezone_name') else None
            )
        
        return airport, airport_geo, geo_warnings
        
    except Exception as e:
        return None, None, [f"Error creating records: {str(e)}"]

def insert_airports_to_database(df, verbose=False):
    """Insert airport data into the normalized database schema with proper transaction handling"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available for database operations")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("Connected to database successfully!")
        
        with Session(db_manager.engine) as session:
            # Check existing airports to avoid duplicates
            existing_icao_codes = set()
            existing_airports = session.exec(select(Airport.icao)).all()
            existing_icao_codes.update(existing_airports)
            
            if verbose:
                print(f"Found {len(existing_icao_codes)} existing airports in database")
            
            # Convert Polars DataFrame to list of dictionaries
            airports_data = df.to_dicts()
            
            inserted_count = 0
            skipped_count = 0
            error_count = 0
            warning_count = 0
            batch_size = 100  # Process in batches for better transaction management
            
            if verbose:
                print(f"Processing {len(airports_data)} airports in batches of {batch_size}...")
            
            # Process airports in batches for better transaction handling
            with tqdm(
                total=len(airports_data),
                desc="🏗️  Inserting airports",
                unit="airports",
                colour='blue',
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} ({percentage:3.0f}%) [{elapsed}<{remaining}]'
            ) as pbar:
                for batch_start in range(0, len(airports_data), batch_size):
                    batch_end = min(batch_start + batch_size, len(airports_data))
                    batch_data = airports_data[batch_start:batch_end]
                    
                    # Process this batch with transaction handling
                    try:
                        batch_inserted = 0
                        batch_skipped = 0
                        batch_errors = 0
                        
                        for airport_data in batch_data:
                            icao = airport_data['icao']
                            
                            # Skip if airport already exists
                            if icao in existing_icao_codes:
                                batch_skipped += 1
                                continue
                            
                            try:
                                # Create Airport and AirportGeo records with validation
                                airport, airport_geo, issues = create_airport_and_geo_records(airport_data, session)
                                
                                if airport is None:
                                    if verbose and error_count < 10:  # Only show first 10 errors in verbose mode
                                        print(f"✗ Validation failed for {icao}: {', '.join(issues)}")
                                    batch_errors += 1
                                    continue
                                
                                if issues:  # These are warnings
                                    warning_count += len(issues)
                                    if verbose and warning_count <= 10:  # Only show first 10 warnings in verbose mode
                                        print(f"⚠ Warning for {icao}: {', '.join(issues)}")
                                
                                # Insert Airport record first
                                session.add(airport)
                                session.flush()  # Get the airport_id without committing the transaction
                                
                                # Set the foreign key and insert AirportGeo record (if available)
                                if airport_geo is not None:
                                    airport_geo.airport_id = airport.airport_id
                                    session.add(airport_geo)
                                
                                existing_icao_codes.add(icao)  # Track to avoid duplicates in this batch
                                batch_inserted += 1
                                
                            except Exception as e:
                                if verbose and batch_errors < 5:  # Only show first 5 errors per batch in verbose mode
                                    print(f"✗ Error processing {icao}: {e}")
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
                        if verbose:
                            print(f"✗ Batch transaction failed (airports {batch_start}-{batch_end}): {e}")
                        error_count += len(batch_data)
                        pbar.update(len(batch_data))
                        continue
            
            print(f"✓ Database insertion completed!")
            print(f"- Inserted: {inserted_count} new airports (with geographic data)")
            print(f"- Skipped: {skipped_count} existing airports")
            print(f"- Errors: {error_count} airports failed validation/insertion")
            if verbose:
                print(f"- Warnings: {warning_count} data quality warnings")
            
            # Verify data integrity after insertion
            verify_data_integrity(session, verbose)
            
            return True
            
    except Exception as e:
        print(f"✗ Database insertion failed: {e}")
        return False

def verify_data_integrity(session, verbose=False):
    """Verify data integrity after insertion"""
    try:
        # Check that all airports have corresponding geographic records
        airports_without_geo = session.exec(
            select(Airport)
            .outerjoin(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
            .where(AirportGeo.airport_id.is_(None))
        ).all()
        
        if airports_without_geo:
            if verbose:
                print(f"⚠ Warning: {len(airports_without_geo)} airports without geographic data")
        
        # Check for orphaned geographic records (shouldn't happen with proper FK constraints)
        orphaned_geo = session.exec(
            select(AirportGeo)
            .outerjoin(Airport, AirportGeo.airport_id == Airport.airport_id)
            .where(Airport.airport_id.is_(None))
        ).all()
        
        if orphaned_geo:
            if verbose:
                print(f"⚠ Warning: {len(orphaned_geo)} orphaned geographic records found")
        else:
            if verbose:
                print("✓ Data integrity verification passed")
            
    except Exception as e:
        if verbose:
            print(f"⚠ Data integrity check failed: {e}")

def show_database_stats():
    """Show statistics about airports in the normalized database schema"""
    if not DEPENDENCIES_AVAILABLE:
        return
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        with Session(db_manager.engine) as session:
            # Count total airports
            total_airports = session.exec(select(Airport)).all()
            total = len(total_airports)
            
            if total == 0:
                print("📊 Database Statistics: No airports found")
                return
            
            # Count airports with IATA codes
            with_iata = len([a for a in total_airports if a.iata])
            
            # Count geographic data from AirportGeo table
            total_geo = session.exec(select(AirportGeo)).all()
            geo_count = len(total_geo)
            
            with_coordinates = len([g for g in total_geo if g.latitude and g.longitude])
            with_altitude = len([g for g in total_geo if g.altitude])
            with_timezone = len([g for g in total_geo if g.timezone_name])
            with_city_country = len([g for g in total_geo if g.city and g.country_id])
            
            print(f"📊 Normalized Database Statistics:")
            print(f"  Total airports: {total:,}")
            print(f"  With IATA codes: {with_iata:,}")
            print(f"  Geographic records: {geo_count:,}")
            print(f"  With coordinates: {with_coordinates:,}")
            print(f"  With altitude data: {with_altitude:,}")
            print(f"  With timezone data: {with_timezone:,}")
            print(f"  With city/country: {with_city_country:,}")
            
            # Show sample airports with geographic data and country information
            sample_query = (
                select(Airport, AirportGeo, Country)
                .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
                .outerjoin(Country, AirportGeo.country_id == Country.country_id)
                .limit(3)
            )
            sample_results = session.exec(sample_query).all()
            
            # Count records with raw country data
            with_raw_country = len([g for g in total_geo if g.country])
            
            print(f"  With raw country data: {with_raw_country:,}")
            
            print(f"\nSample airports with geographic data:")
            for airport, geo, country in sample_results:
                iata_display = f"({airport.iata})" if airport.iata else "(no IATA)"
                country_name = country.name if country else "Unknown"
                raw_country = f" (raw: {geo.country})" if geo.country and geo.country != country_name else ""
                location = f"{geo.city}, {country_name}{raw_country}" if geo.city else f"{country_name}{raw_country}"
                coords = f"({geo.latitude}, {geo.longitude})" if geo.latitude and geo.longitude else "(no coords)"
                iso_display = f" [{geo.iso_a3}]" if geo.iso_a3 else ""
                print(f"  {airport.icao} {iata_display} - {airport.name}")
                print(f"    Location: {location}{iso_display} {coords}")
                
    except Exception as e:
        print(f"✗ Failed to get database statistics: {e}")

def main():
    """Main function to download and import airports data into normalized schema"""
    parser = argparse.ArgumentParser(description="Download and import airports data from OpenFlights.org")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()
    
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    if args.verbose:
        print("✈️  OpenFlights Airports Data Import (Normalized Schema)")
        print("=" * 52)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        if args.verbose:
            print("You can still download and analyze data without database connection")
        
        # Offer to continue without database import
        if not args.yes:
            try:
                response = input("\nContinue with download and analysis only? (y/N): ").strip().lower()
                if response != 'y':
                    return False
            except KeyboardInterrupt:
                print("\nOperation cancelled")
                return False
    
    # Step 1: Download data
    if not AIRPORTS_FILE.exists():
        if not download_airports_data():
            return False
    else:
        print(f"✓ Airports data already exists: {AIRPORTS_FILE}")
    
    # Step 2: Analyze data
    df = analyze_airports_data(verbose=args.verbose)
    if df is None:
        return False
    
    # Step 3: Prepare data
    prepared_df = prepare_airport_data(df, verbose=args.verbose)
    if len(prepared_df) == 0:
        print("✗ No suitable airport data found")
        return False
    
    # Step 4: Insert into database (if .env exists)
    if os.path.exists('.env'):
        if args.verbose:
            print(f"\nFound {len(prepared_df):,} airports ready for import")
        
        # Ask user what to do (unless --yes is specified)
        if args.yes:
            choice = 'y'
        else:
            print("What would you like to do?")
            print("  y = Import airports into database")
            print("  s = Show current database statistics only")
            choice = input("\nChoice (y/s): ").strip().lower()
        
        if choice == 's':
            show_database_stats()
            return True
        elif choice == 'y':
            if args.verbose:
                print("Importing airports into normalized database schema...")
            if not insert_airports_to_database(prepared_df, verbose=args.verbose):
                return False
            if args.verbose:
                print("\n" + "=" * 50)
            show_database_stats()
            if args.verbose:
                print("\n🎉 Normalized airport data import completed successfully!")
        else:
            print("Invalid choice. Showing statistics only.")
            show_database_stats()
    else:
        print(f"\n✓ Data analysis completed! {len(prepared_df)} airports ready for normalized import")
        if args.verbose:
            print("Configure .env file and run again to import into normalized database schema")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)