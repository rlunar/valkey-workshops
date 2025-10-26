#!/usr/bin/env python3
"""
Create relationships between cities and airports for flight planning.

This script maps airports to nearby cities based on country code, city name matching,
and geographic distance. It starts from the airports table (fewer records) for efficiency.
"""

import os
import sys
import math
import argparse
from decimal import Decimal
from typing import List, Tuple, Dict, Set
from sqlmodel import Session, select, text
from tqdm import tqdm
from collections import defaultdict
import concurrent.futures
from functools import lru_cache

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.city import City, CityAirportRelation
from models.airport import Airport
from models.airport_geo import AirportGeo


class CityAirportRelationCreator:
    """Create relationships between airports and nearby cities"""
    
    def __init__(self, db_manager: DatabaseManager, verbose: bool = False):
        self.db_manager = db_manager
        self.verbose = verbose
        self._distance_cache = {}  # Cache for distance calculations
    
    def _build_spatial_grid(self, cities: List, grid_size: float = 1.0) -> Dict:
        """Build a spatial grid for faster geographic lookups"""
        grid = defaultdict(list)
        for city in cities:
            if city.latitude and city.longitude:
                # Create grid coordinates (1 degree = ~111km)
                # Convert Decimal to float for division
                grid_lat = int(float(city.latitude) / grid_size)
                grid_lon = int(float(city.longitude) / grid_size)
                grid[(grid_lat, grid_lon)].append(city)
        return grid
    
    def _get_nearby_grid_cells(self, lat: float, lon: float, max_distance_km: float, grid_size: float = 1.0) -> List:
        """Get grid cells within max_distance of a point"""
        # Approximate grid cells to check (1 degree ≈ 111km)
        grid_radius = int(math.ceil(max_distance_km / (111 * grid_size))) + 1
        
        # Ensure lat and lon are floats for division
        center_lat = int(float(lat) / grid_size)
        center_lon = int(float(lon) / grid_size)
        
        cells = []
        for lat_offset in range(-grid_radius, grid_radius + 1):
            for lon_offset in range(-grid_radius, grid_radius + 1):
                cells.append((center_lat + lat_offset, center_lon + lon_offset))
        return cells
    
    @lru_cache(maxsize=10000)
    def _cached_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Cached distance calculation to avoid redundant computations"""
        return self.calculate_distance(lat1, lon1, lat2, lon2)
    
    def _process_airport_batch(self, airports_batch: List, cities_data: Dict, max_distance_km: float) -> List:
        """Process a batch of airports in parallel"""
        relations = []
        
        for airport_data in airports_batch:
            airport_id, airport_name, airport_iata, airport_icao, lat, lon, country, iso_a2, airport_city = airport_data
            
            best_matches = self._find_matches_for_airport(
                airport_id, lat, lon, iso_a2, airport_city, cities_data, max_distance_km
            )
            
            if best_matches:
                relations.extend(self._create_relations_for_matches(
                    airport_id, best_matches
                ))
        
        return relations
    
    def _find_matches_for_airport(self, airport_id: int, lat: float, lon: float, 
                                 iso_a2: str, airport_city: str, cities_data: Dict, 
                                 max_distance_km: float) -> List:
        """Optimized matching logic for a single airport"""
        best_matches = []
        
        # Strategy 1: Exact match by country code and city name
        if iso_a2 and airport_city:
            airport_city_normalized = airport_city.lower().strip()
            exact_key = f"{iso_a2}:{airport_city_normalized}"
            
            exact_matches = cities_data['by_country_and_name'].get(exact_key, [])
            if exact_matches:
                for city in exact_matches:
                    distance = self._cached_distance(lat, lon, float(city.latitude), float(city.longitude))
                    best_matches.append((city, distance, 'exact'))
                return best_matches  # Early return for exact matches
        
        # Strategy 2: Spatial grid lookup for nearby cities
        nearby_cells = self._get_nearby_grid_cells(lat, lon, max_distance_km)
        candidate_cities = []
        
        for cell in nearby_cells:
            candidate_cities.extend(cities_data['spatial_grid'].get(cell, []))
        
        # Remove duplicates while preserving order
        seen_city_ids = set()
        unique_candidates = []
        for city in candidate_cities:
            if city.city_id not in seen_city_ids:
                seen_city_ids.add(city.city_id)
                unique_candidates.append(city)
        candidate_cities = unique_candidates
        
        # Filter by country first, then distance
        country_candidates = [city for city in candidate_cities if city.country_code == iso_a2]
        
        # Strategy 2a: Partial name match within same country
        if iso_a2 and airport_city and country_candidates:
            airport_city_normalized = airport_city.lower().strip()
            
            for city in country_candidates:
                if city.name:
                    city_name_normalized = city.name.lower().strip()
                    
                    if (airport_city_normalized in city_name_normalized or 
                        city_name_normalized in airport_city_normalized or
                        self._fuzzy_name_match(airport_city_normalized, city_name_normalized)):
                        
                        distance = self._cached_distance(lat, lon, float(city.latitude), float(city.longitude))
                        if distance <= max_distance_km:
                            best_matches.append((city, distance, 'partial'))
        
        # Strategy 2b: Distance-based matching within same country
        if not best_matches and country_candidates:
            for city in country_candidates:
                distance = self._cached_distance(lat, lon, float(city.latitude), float(city.longitude))
                if distance <= min(50.0, max_distance_km):
                    best_matches.append((city, distance, 'distance'))
        
        # Strategy 3: Global distance-based matching (limited scope)
        if not best_matches:
            # Only check very close cities globally
            for city in candidate_cities:
                distance = self._cached_distance(lat, lon, float(city.latitude), float(city.longitude))
                if distance <= 25.0:
                    best_matches.append((city, distance, 'global'))
        
        return best_matches
    
    def _create_relations_for_matches(self, airport_id: int, best_matches: List) -> List:
        """Create CityAirportRelation objects for matches"""
        relations = []
        
        # Sort by distance and match type priority
        match_type_priority = {'exact': 0, 'partial': 1, 'distance': 2, 'global': 3}
        best_matches.sort(key=lambda x: (match_type_priority[x[2]], x[1]))
        
        # Limit to top 3 matches to avoid too many relations
        best_matches = best_matches[:3]
        
        for i, (city, distance, match_type) in enumerate(best_matches):
            # Calculate scores based on match type and distance
            if match_type == 'exact':
                accessibility_score = 9.99
                is_primary = (i == 0)
            elif match_type == 'partial':
                accessibility_score = max(7.0, min(9.99, 10.0 - (distance / 10)))
                is_primary = (i == 0 and distance <= 25.0)
            else:
                accessibility_score = max(5.0, min(9.99, 10.0 - (distance / 5)))
                is_primary = (i == 0 and distance <= 15.0)
            
            # Calculate passenger share
            population = float(city.population) if city.population else 1000.0
            base_share = min(1.0, population / 1000000.0)
            passenger_share = base_share * (accessibility_score / 10.0) * (1.0 / (i + 1))
            
            relation = CityAirportRelation(
                city_id=city.city_id,
                airport_id=airport_id,
                distance_km=Decimal(str(round(distance, 2))),
                is_primary_airport=is_primary,
                accessibility_score=Decimal(str(round(accessibility_score, 2))),
                estimated_passenger_share=Decimal(str(round(passenger_share, 4))),
                seasonal_variation=Decimal('1.2')
            )
            relations.append(relation)
        
        return relations

    def create_city_airport_relations(self, max_distance_km: float = 100.0, batch_size: int = 1000, use_parallel: bool = True):
        """
        Create relationships between airports and nearby cities with optimized performance.
        
        Optimizations:
        1. Spatial grid indexing for O(1) geographic lookups
        2. Parallel processing of airport batches
        3. Distance calculation caching
        4. Bulk database operations
        5. Early termination for exact matches
        """
        if self.verbose:
            print("Creating city-airport relationships (optimized version)...")
        
        with Session(self.db_manager.engine) as session:
            # Clear existing relations
            if self.verbose:
                print("Clearing existing relations...")
            session.exec(text("DELETE FROM city_airport_relation"))
            session.commit()
            
            # Get all airports with geographic data
            airports_with_geo = session.exec(
                select(Airport.airport_id, Airport.name, Airport.iata, Airport.icao,
                       AirportGeo.latitude, AirportGeo.longitude, AirportGeo.country, AirportGeo.iso_a2,
                       AirportGeo.city).where(
                    Airport.airport_id == AirportGeo.airport_id,
                    AirportGeo.latitude.is_not(None),
                    AirportGeo.longitude.is_not(None)
                )
            ).all()
            
            if self.verbose:
                print(f"Found {len(airports_with_geo)} airports with geographic data")
            
            # Load cities and build optimized lookup structures
            cities = session.exec(
                select(City).where(
                    City.latitude.is_not(None),
                    City.longitude.is_not(None)
                )
            ).all()
            
            if self.verbose:
                print(f"Found {len(cities)} cities with coordinates")
                print("Building optimized lookup structures...")
            
            # Build lookup structures
            cities_by_country_and_name = {}
            spatial_grid = self._build_spatial_grid(cities, grid_size=1.0)
            
            for city in tqdm(cities, desc="Building lookups", disable=not self.verbose):
                # Create country+name lookup for exact matching
                if city.country_code and city.name:
                    city_name_normalized = city.name.lower().strip()
                    key = f"{city.country_code}:{city_name_normalized}"
                    if key not in cities_by_country_and_name:
                        cities_by_country_and_name[key] = []
                    cities_by_country_and_name[key].append(city)
            
            # Prepare cities data for processing
            cities_data = {
                'by_country_and_name': cities_by_country_and_name,
                'spatial_grid': spatial_grid
            }
            
            # Process airports in batches
            all_relations = []
            matched_airports = 0
            
            if use_parallel and len(airports_with_geo) > 100:
                # Parallel processing for large datasets
                if self.verbose:
                    print("Using parallel processing...")
                
                # Split airports into batches
                airport_batches = [
                    airports_with_geo[i:i + batch_size] 
                    for i in range(0, len(airports_with_geo), batch_size)
                ]
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    future_to_batch = {
                        executor.submit(self._process_airport_batch, batch, cities_data, max_distance_km): batch
                        for batch in airport_batches
                    }
                    
                    for future in tqdm(concurrent.futures.as_completed(future_to_batch), 
                                     total=len(airport_batches), desc="Processing batches", 
                                     disable=not self.verbose):
                        batch_relations = future.result()
                        all_relations.extend(batch_relations)
                        matched_airports += len([r for r in batch_relations if r])
            else:
                # Sequential processing for smaller datasets
                for airport_data in tqdm(airports_with_geo, desc="Processing airports", disable=not self.verbose):
                    airport_id, airport_name, airport_iata, airport_icao, lat, lon, country, iso_a2, airport_city = airport_data
                    
                    best_matches = self._find_matches_for_airport(
                        airport_id, float(lat), float(lon), iso_a2, airport_city, cities_data, max_distance_km
                    )
                    
                    if best_matches:
                        matched_airports += 1
                        relations = self._create_relations_for_matches(airport_id, best_matches)
                        all_relations.extend(relations)
            
            # Bulk insert all relations
            if self.verbose:
                print(f"Inserting {len(all_relations)} relationships...")
            
            # Insert in larger batches for better performance
            insert_batch_size = 2000
            for i in tqdm(range(0, len(all_relations), insert_batch_size), 
                         desc="Inserting relations", disable=not self.verbose):
                batch = all_relations[i:i + insert_batch_size]
                session.add_all(batch)
                session.commit()
            
            total_airports = len(airports_with_geo)
            print(f"Successfully created city-airport relationships")
            if self.verbose:
                print(f"Total airports processed: {total_airports}")
                print(f"Airports matched to cities: {matched_airports}")
                print(f"Total relationships created: {len(all_relations)}")
                if total_airports > 0:
                    print(f"Match rate: {matched_airports/total_airports*100:.1f}%")
    
    def _fuzzy_name_match(self, name1: str, name2: str) -> bool:
        """Check if two city names are similar enough to be considered a match"""
        # Split names into words and check for significant word overlap
        words1 = set(word for word in name1.split() if len(word) > 2)
        words2 = set(word for word in name2.split() if len(word) > 2)
        
        if not words1 or not words2:
            return False
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union >= 0.5 if union > 0 else False
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r


def main():
    """Main function to create city-airport relationships"""
    parser = argparse.ArgumentParser(description="Create relationships between cities and airports")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--max-distance", type=float, default=100.0, 
                       help="Maximum distance for city-airport matching in km (default: 100)")
    parser.add_argument("--batch-size", type=int, default=1000,
                       help="Batch size for parallel processing (default: 1000)")
    parser.add_argument("--no-parallel", action="store_true",
                       help="Disable parallel processing")
    args = parser.parse_args()
    
    if args.verbose:
        print("City-Airport Relationship Creator (Optimized)")
        print("=" * 45)
        print(f"Max distance: {args.max_distance}km")
        print(f"Batch size: {args.batch_size}")
        print(f"Parallel processing: {'Disabled' if args.no_parallel else 'Enabled'}")
        print()
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Initialize creator
    creator = CityAirportRelationCreator(db_manager, verbose=args.verbose)
    
    try:
        # Create relationships with optimizations
        creator.create_city_airport_relations(
            max_distance_km=args.max_distance,
            batch_size=args.batch_size,
            use_parallel=not args.no_parallel
        )
        
        print("City-airport relationship creation completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())