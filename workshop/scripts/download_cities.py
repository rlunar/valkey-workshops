#!/usr/bin/env python3
"""
Download and populate city data from GeoNames dataset for flight planning.

This script downloads city data from GeoNames and populates the city table
with population information to help plan flight frequencies and routes.
"""

import os
import sys
import requests
import zipfile
import csv
import argparse
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlmodel import Session, select, text
import tempfile
from tqdm import tqdm

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.city import City, CityAirportRelation
from models.country import Country
from models.airport import Airport
from models.airport_geo import AirportGeo


class GeoNamesCityDownloader:
    """Download and process GeoNames city data for flight planning"""
    
    # GeoNames URLs for different city datasets
    GEONAMES_URLS = {
        'cities1000': 'http://download.geonames.org/export/dump/cities1000.zip',  # Cities with population > 1000
        'cities5000': 'http://download.geonames.org/export/dump/cities5000.zip',  # Cities with population > 5000
        'cities15000': 'http://download.geonames.org/export/dump/cities15000.zip',  # Cities with population > 15000
    }
    
    def __init__(self, db_manager: DatabaseManager, verbose: bool = False):
        self.db_manager = db_manager
        self.country_mapping: Dict[str, int] = {}
        self.verbose = verbose
    
    def load_country_mapping(self, session: Session):
        """Load country code to country_id mapping"""
        countries = session.exec(select(Country)).all()
        for country in countries:
            if country.iso_code:
                self.country_mapping[country.iso_code] = country.country_id
        if self.verbose:
            print(f"Loaded {len(self.country_mapping)} country mappings")
    
    def download_and_extract(self, dataset: str = 'cities15000') -> str:
        """Download and extract GeoNames city data"""
        if dataset not in self.GEONAMES_URLS:
            raise ValueError(f"Unknown dataset: {dataset}. Available: {list(self.GEONAMES_URLS.keys())}")
        
        url = self.GEONAMES_URLS[dataset]
        if self.verbose:
            print(f"Downloading {dataset} from GeoNames...")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, f"{dataset}.zip")
        
        # First, get file size using HEAD request
        if self.verbose:
            print("Checking file size...")
        head_response = requests.head(url)
        head_response.raise_for_status()
        total_size = int(head_response.headers.get('content-length', 0))
        
        if self.verbose and total_size > 0:
            # Convert bytes to MB for display
            size_mb = total_size / (1024 * 1024)
            print(f"File size: {size_mb:.1f} MB")
        
        # Download the file with progress bar
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            # Always show download progress bar (even if not verbose)
            with tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024, 
                     desc=f"Downloading {dataset}", miniters=1) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        # Extract the file
        if self.verbose:
            print("Extracting archive...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Return path to the extracted txt file
        txt_file = os.path.join(temp_dir, f"{dataset}.txt")
        if not os.path.exists(txt_file):
            raise FileNotFoundError(f"Expected file {txt_file} not found after extraction")
        
        if self.verbose:
            print(f"Downloaded and extracted to: {txt_file}")
        return txt_file
    
    def calculate_flight_metrics(self, population: int, feature_code: str) -> tuple:
        """Calculate flight demand score and recommended daily flights based on population"""
        if not population:
            return None, None
        
        # Base flight demand score calculation
        # Logarithmic scale to handle wide population ranges
        import math
        base_score = math.log10(population) if population > 0 else 0
        
        # Adjust based on city type (feature_code)
        multiplier = {
            'PPLC': 2.0,    # Capital city
            'PPLA': 1.5,    # Administrative center
            'PPLA2': 1.3,   # Secondary administrative center
            'PPLA3': 1.2,   # Third-level administrative center
            'PPLA4': 1.1,   # Fourth-level administrative center
            'PPL': 1.0,     # Regular populated place
        }.get(feature_code, 1.0)
        
        flight_demand_score = round(base_score * multiplier, 2)
        
        # Recommended daily flights based on population tiers
        if population >= 5000000:  # Mega cities
            daily_flights = max(50, int(population / 200000))
        elif population >= 1000000:  # Major cities
            daily_flights = max(20, int(population / 100000))
        elif population >= 500000:  # Large cities
            daily_flights = max(10, int(population / 75000))
        elif population >= 100000:  # Medium cities
            daily_flights = max(5, int(population / 50000))
        elif population >= 50000:   # Small cities
            daily_flights = max(2, int(population / 25000))
        else:  # Towns
            daily_flights = max(1, int(population / 15000))
        
        return flight_demand_score, daily_flights
    
    def parse_geonames_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single line from GeoNames data file"""
        fields = line.strip().split('\t')
        
        # GeoNames format has 19 fields
        if len(fields) < 19:
            return None
        
        try:
            geonames_id = int(fields[0])
            name = fields[1]
            ascii_name = fields[2]
            alternate_names = fields[3] if fields[3] else None
            latitude = Decimal(fields[4]) if fields[4] else None
            longitude = Decimal(fields[5]) if fields[5] else None
            feature_class = fields[6] if fields[6] else None
            feature_code = fields[7] if fields[7] else None
            country_code = fields[8] if fields[8] else None
            admin1_code = fields[10] if fields[10] else None
            admin2_code = fields[11] if fields[11] else None
            admin3_code = fields[12] if fields[12] else None
            admin4_code = fields[13] if fields[13] else None
            population = int(fields[14]) if fields[14] and fields[14].isdigit() else None
            elevation = int(fields[15]) if fields[15] and fields[15].isdigit() else None
            timezone = fields[17] if fields[17] else None
            
            # Calculate flight planning metrics
            flight_demand_score, recommended_daily_flights = self.calculate_flight_metrics(
                population or 0, feature_code or ''
            )
            
            return {
                'geonames_id': geonames_id,
                'name': name,
                'ascii_name': ascii_name,
                'alternate_names': alternate_names,
                'latitude': latitude,
                'longitude': longitude,
                'feature_class': feature_class,
                'feature_code': feature_code,
                'country_code': country_code,
                'country_id': self.country_mapping.get(country_code),
                'admin1_code': admin1_code,
                'admin2_code': admin2_code,
                'admin3_code': admin3_code,
                'admin4_code': admin4_code,
                'population': population,
                'elevation': elevation,
                'timezone': timezone,
                'flight_demand_score': flight_demand_score,
                'recommended_daily_flights': recommended_daily_flights,
                'peak_season_multiplier': Decimal('1.5'),  # Default 50% increase in peak season
                'data_source': 'GeoNames',
            }
        except (ValueError, IndexError) as e:
            if self.verbose:
                print(f"Error parsing line: {e}")
            return None
    
    def populate_cities(self, txt_file: str, batch_size: int = 1000):
        """Populate the city table with GeoNames data"""
        if self.verbose:
            print("Populating cities table...")
        
        with Session(self.db_manager.engine) as session:
            # Load country mapping
            self.load_country_mapping(session)
            
            # Clear existing data
            if self.verbose:
                print("Clearing existing city data...")
            session.exec(text("DELETE FROM city_airport_relation"))
            session.exec(text("DELETE FROM city"))
            session.commit()
            
            # Count total lines for progress bar
            total_lines = 0
            with open(txt_file, 'r', encoding='utf-8') as f:
                for _ in f:
                    total_lines += 1
            
            cities_batch = []
            processed_count = 0
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                # Always show processing progress bar since this is a long operation
                with tqdm(total=total_lines, desc="Processing cities", unit="lines") as pbar:
                    for line in f:
                        pbar.update(1)
                        city_data = self.parse_geonames_line(line)
                        if city_data:
                            # Only include populated places (feature_class = 'P')
                            if city_data.get('feature_class') == 'P':
                                city = City(**city_data)
                                cities_batch.append(city)
                                
                                if len(cities_batch) >= batch_size:
                                    session.add_all(cities_batch)
                                    session.commit()
                                    processed_count += len(cities_batch)
                                    # Always show cities saved count
                                    pbar.set_postfix({"Cities saved": processed_count})
                                    cities_batch = []
                    
                    # Process remaining cities
                    if cities_batch:
                        session.add_all(cities_batch)
                        session.commit()
                        processed_count += len(cities_batch)
            
            print(f"Successfully populated {processed_count} cities")
    



def main():
    """Main function to download and populate city data"""
    parser = argparse.ArgumentParser(description="Download and populate city data from GeoNames")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--dataset", choices=['cities1000', 'cities5000', 'cities15000'], 
                       default='cities1000', help="Choose dataset size (default: cities1000)")
    args = parser.parse_args()
    
    if args.verbose:
        print("GeoNames City Data Downloader for Flight Planning")
        print("=" * 50)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Create tables if they don't exist
    if args.verbose:
        print("Creating database tables...")
    db_manager.create_tables()
    
    # Initialize downloader
    downloader = GeoNamesCityDownloader(db_manager, verbose=args.verbose)
    
    try:
        # Download and extract data
        txt_file = downloader.download_and_extract(args.dataset)
        
        # Populate cities
        downloader.populate_cities(txt_file)
        
        # Note: City-airport relationships are now created separately
        # Run scripts/create_city_airport_relations.py after populating airports
        
        print("City data download and population completed successfully!")
        
        # Clean up temporary file
        os.unlink(txt_file)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())