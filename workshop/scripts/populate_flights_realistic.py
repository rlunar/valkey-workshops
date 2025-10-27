#!/usr/bin/env python3
"""
Realistic Flight Population Script

Generate flights with priority for major hub airports based on actual route data.
This script prioritizes routes involving major hubs like ATL, ORD, LHR, CDG, FRA, LAX, DFW, JFK.
"""

import os
import sys
import random
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import Session, select, func

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.database import DatabaseManager
    from models.flight import Flight
    from models.route import Route
    from models.airport import Airport
    from models.airline import Airline
    from models.airplane import Airplane
    from scripts.flight_config import FlightConfig
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False


class RealisticFlightPopulator:
    """Generate flights with priority for major hub airports"""
    
    def __init__(self, db_manager: DatabaseManager, verbose: bool = False):
        self.db_manager = db_manager
        self.config = FlightConfig()
        self.verbose = verbose
        
        # Major hub airports (prioritized for flight generation)
        self.major_hubs = {
            'ATL', 'ORD', 'LHR', 'CDG', 'FRA', 'LAX', 'DFW', 'JFK',
            'AMS', 'PEK', 'NRT', 'ICN', 'SIN', 'DXB', 'LGW', 'FCO',
            'MAD', 'BCN', 'MUC', 'ZUR', 'VIE', 'CPH', 'ARN', 'HEL',
            'SVO', 'IST', 'DOH', 'BKK', 'HKG', 'PVG', 'CAN', 'DEL',
            'BOM', 'SYD', 'MEL', 'YYZ', 'YVR', 'GRU', 'EZE', 'SCL',
            'LIM', 'BOG', 'PTY', 'CUN', 'MEX', 'MCO', 'LAS', 'PHX',
            'SEA', 'SFO', 'DEN', 'IAH', 'MIA', 'BOS', 'EWR', 'CLT'
        }
        
        # Cache for database lookups
        self._airport_cache = {}
        self._airline_cache = {}
        self._aircraft_cache = []
        self._route_counts_cache = {}
        self._hub_routes_cache = []
    
    def initialize_caches(self, session: Session):
        """Initialize lookup caches for better performance"""
        if self.verbose:
            print("Initializing data caches...")
        
        # Airport cache (IATA -> airport_id)
        airport_query = select(Airport.iata, Airport.airport_id, Airport.name).where(
            Airport.iata.is_not(None)
        )
        for iata, airport_id, name in session.exec(airport_query).all():
            self._airport_cache[iata] = {'id': airport_id, 'name': name}
        
        # Airline cache (IATA -> airline_id)
        airline_query = select(Airline.iata, Airline.airline_id, Airline.name).where(
            Airline.iata.is_not(None)
        )
        for iata, airline_id, name in session.exec(airline_query).all():
            self._airline_cache[iata] = {'id': airline_id, 'name': name}
        
        # Aircraft cache (random selection pool)
        aircraft_query = select(Airplane.airplane_id, Airplane.capacity).limit(1000)
        self._aircraft_cache = [
            {'id': airplane_id, 'capacity': capacity}
            for airplane_id, capacity in session.exec(aircraft_query).all()
        ]
        
        # Route counts cache
        self._route_counts_cache = self.calculate_airport_route_counts(session)
        
        if self.verbose:
            print(f"Cached {len(self._airport_cache)} airports, "
                  f"{len(self._airline_cache)} airlines, "
                  f"{len(self._aircraft_cache)} aircraft")
            
            # Show major hubs found
            found_hubs = [hub for hub in self.major_hubs if hub in self._airport_cache]
            print(f"Found {len(found_hubs)} major hubs in database: {', '.join(sorted(found_hubs))}")
    
    def calculate_airport_route_counts(self, session: Session) -> Dict[str, int]:
        """Calculate total route counts per airport (inbound + outbound)"""
        if self.verbose:
            print("Calculating airport route counts...")
        
        route_counts = {}
        
        # Count outbound routes
        outbound_query = (
            select(Route.source_airport_code, func.count(Route.route_id))
            .where(Route.source_airport_code.is_not(None))
            .group_by(Route.source_airport_code)
        )
        
        for airport_code, count in session.exec(outbound_query).all():
            route_counts[airport_code] = route_counts.get(airport_code, 0) + count
        
        # Count inbound routes
        inbound_query = (
            select(Route.destination_airport_code, func.count(Route.route_id))
            .where(Route.destination_airport_code.is_not(None))
            .group_by(Route.destination_airport_code)
        )
        
        for airport_code, count in session.exec(inbound_query).all():
            route_counts[airport_code] = route_counts.get(airport_code, 0) + count
        
        return route_counts
    
    def get_prioritized_routes(self, session: Session, max_routes: int = 2000) -> List[Dict[str, Any]]:
        """Get routes prioritized by major hub involvement"""
        
        # Get existing airline codes and airports from cache
        existing_airlines = list(self._airline_cache.keys())
        existing_airports = list(self._airport_cache.keys())
        
        if not existing_airlines or not existing_airports:
            if self.verbose:
                print("No airlines or airports in cache")
            return []
        
        # Find major hubs that exist in our database
        available_hubs = [hub for hub in self.major_hubs if hub in existing_airports]
        
        if self.verbose:
            print(f"Prioritizing routes for {len(available_hubs)} major hubs")
        
        # Get routes involving major hubs (highest priority)
        hub_routes_query = (
            select(
                Route.route_id,
                Route.source_airport_code,
                Route.destination_airport_code,
                Route.airline_code,
                Route.codeshare,
                Route.stops,
                Route.equipment
            )
            .where(
                Route.source_airport_code.is_not(None),
                Route.destination_airport_code.is_not(None),
                Route.airline_code.is_not(None),
                Route.source_airport_code.in_(existing_airports),
                Route.destination_airport_code.in_(existing_airports),
                Route.airline_code.in_(existing_airlines),
                # At least one end must be a major hub
                (Route.source_airport_code.in_(available_hubs)) | 
                (Route.destination_airport_code.in_(available_hubs))
            )
            .limit(int(max_routes * 0.7))  # 70% of routes should involve hubs
        )
        
        hub_routes = []
        for route in session.exec(hub_routes_query).all():
            # Calculate priority score based on hub involvement
            priority_score = 0
            if route.source_airport_code in self.major_hubs:
                priority_score += 2
            if route.destination_airport_code in self.major_hubs:
                priority_score += 2
            
            # Boost score for routes between two hubs
            if (route.source_airport_code in self.major_hubs and 
                route.destination_airport_code in self.major_hubs):
                priority_score += 3
            
            hub_routes.append({
                'route_id': route.route_id,
                'origin': route.source_airport_code,
                'destination': route.destination_airport_code,
                'airline': route.airline_code,
                'codeshare': route.codeshare or False,
                'stops': route.stops or 0,
                'equipment': route.equipment,
                'priority_score': priority_score,
                'is_hub_route': True
            })
        
        # Get additional non-hub routes to fill remaining capacity
        remaining_capacity = max_routes - len(hub_routes)
        if remaining_capacity > 0:
            non_hub_routes_query = (
                select(
                    Route.route_id,
                    Route.source_airport_code,
                    Route.destination_airport_code,
                    Route.airline_code,
                    Route.codeshare,
                    Route.stops,
                    Route.equipment
                )
                .where(
                    Route.source_airport_code.is_not(None),
                    Route.destination_airport_code.is_not(None),
                    Route.airline_code.is_not(None),
                    Route.source_airport_code.in_(existing_airports),
                    Route.destination_airport_code.in_(existing_airports),
                    Route.airline_code.in_(existing_airlines),
                    # Neither end is a major hub
                    ~(Route.source_airport_code.in_(available_hubs)),
                    ~(Route.destination_airport_code.in_(available_hubs))
                )
                .limit(remaining_capacity)
            )
            
            for route in session.exec(non_hub_routes_query).all():
                hub_routes.append({
                    'route_id': route.route_id,
                    'origin': route.source_airport_code,
                    'destination': route.destination_airport_code,
                    'airline': route.airline_code,
                    'codeshare': route.codeshare or False,
                    'stops': route.stops or 0,
                    'equipment': route.equipment,
                    'priority_score': 1,  # Lower priority
                    'is_hub_route': False
                })
        
        # Sort by priority score (highest first)
        hub_routes.sort(key=lambda x: x['priority_score'], reverse=True)
        
        if self.verbose:
            hub_count = sum(1 for r in hub_routes if r['is_hub_route'])
            print(f"Selected {len(hub_routes)} routes: {hub_count} hub routes, {len(hub_routes) - hub_count} non-hub routes")
        
        return hub_routes
    
    def calculate_daily_flights(self, route: Dict[str, Any], date: datetime, distance_km: float) -> int:
        """Calculate number of flights for a route on a specific date"""
        
        origin_code = route['origin']
        dest_code = route['destination']
        
        # Get airport tiers for both origin and destination
        origin_routes = self._route_counts_cache.get(origin_code, 0)
        dest_routes = self._route_counts_cache.get(dest_code, 0)
        
        origin_tier = self.config.get_airport_tier(origin_routes)
        dest_tier = self.config.get_airport_tier(dest_routes)
        
        # Use the higher tier (lower tier number) for frequency calculation
        route_tier = origin_tier if origin_tier['min_routes'] >= dest_tier['min_routes'] else dest_tier
        
        # Base flight frequency based on distance and tier
        if distance_km <= 1500:  # Short-haul
            if route_tier['min_routes'] >= 500:  # Tier 1
                base_flights = random.uniform(4, 8)
            elif route_tier['min_routes'] >= 200:  # Tier 2
                base_flights = random.uniform(2, 4)
            elif route_tier['min_routes'] >= 50:  # Tier 3
                base_flights = random.uniform(1, 2)
            elif route_tier['min_routes'] >= 10:  # Tier 4
                base_flights = random.uniform(0.4, 1)
            else:  # Tier 5
                base_flights = random.uniform(0.2, 0.6)
        elif distance_km <= 4000:  # Medium-haul
            if route_tier['min_routes'] >= 500:  # Tier 1
                base_flights = random.uniform(2, 4)
            elif route_tier['min_routes'] >= 200:  # Tier 2
                base_flights = random.uniform(1, 2)
            elif route_tier['min_routes'] >= 50:  # Tier 3
                base_flights = random.uniform(0.4, 1)
            elif route_tier['min_routes'] >= 10:  # Tier 4
                base_flights = random.uniform(0.2, 0.5)
            else:  # Tier 5
                base_flights = 0
        else:  # Long-haul (4000+ km)
            if route_tier['min_routes'] >= 500:  # Tier 1
                base_flights = random.uniform(0.5, 1.5)
            elif route_tier['min_routes'] >= 200:  # Tier 2
                base_flights = random.uniform(0.3, 0.8)
            elif route_tier['min_routes'] >= 50:  # Tier 3
                base_flights = random.uniform(0.2, 0.5)
            else:  # Tier 4-5
                base_flights = 0
        
        # Major hub boost - significantly increase flights for hub routes
        if route['is_hub_route']:
            hub_multiplier = 1.5  # 50% more flights for hub routes
            if (origin_code in self.major_hubs and dest_code in self.major_hubs):
                hub_multiplier = 2.0  # 100% more for hub-to-hub routes
            base_flights *= hub_multiplier
        
        # Apply seasonal multiplier
        seasonal_mult = self.config.get_seasonal_multiplier(date.month)
        
        # Apply day of week multiplier
        dow_mult = self.config.DAY_OF_WEEK_MULTIPLIERS[date.weekday()]
        
        # Apply airline-specific patterns
        airline_pattern = self.config.get_airline_pattern(route['airline'])
        airline_mult = airline_pattern['frequency_boost']
        
        # Codeshare routes have reduced frequency
        codeshare_mult = 0.7 if route['codeshare'] else 1.0
        
        # Calculate final flight count
        total_flights = base_flights * seasonal_mult * dow_mult * airline_mult * codeshare_mult
        
        # Convert to integer with probabilistic rounding
        flights_today = int(total_flights)
        if random.random() < (total_flights - flights_today):
            flights_today += 1
        
        # Ensure reasonable daily limits per route
        flights_today = min(flights_today, 15)  # Max 15 flights per route per day
        
        return max(0, flights_today)
    
    def estimate_distance_and_duration(self, origin: str, destination: str) -> Tuple[float, timedelta]:
        """Estimate distance and flight duration between airports"""
        
        if origin == destination:
            return 0.0, timedelta(hours=1)
        
        # Enhanced distance estimation for major hubs
        hub_distances = {
            # North American hubs
            ('ATL', 'ORD'): 945, ('ATL', 'LAX'): 3135, ('ATL', 'DFW'): 1159,
            ('ATL', 'JFK'): 1200, ('ORD', 'LAX'): 2802, ('ORD', 'DFW'): 1290,
            ('ORD', 'JFK'): 1185, ('LAX', 'DFW'): 1991, ('LAX', 'JFK'): 3944,
            ('DFW', 'JFK'): 2176, ('ATL', 'MCO'): 663, ('ATL', 'LAS'): 2831,
            
            # European hubs
            ('LHR', 'CDG'): 344, ('LHR', 'FRA'): 659, ('LHR', 'AMS'): 370,
            ('CDG', 'FRA'): 479, ('CDG', 'AMS'): 431, ('FRA', 'AMS'): 364,
            ('LHR', 'FCO'): 1435, ('CDG', 'MAD'): 1054, ('FRA', 'MUC'): 304,
            
            # Transatlantic
            ('LHR', 'JFK'): 5585, ('CDG', 'JFK'): 5837, ('FRA', 'JFK'): 6194,
            ('LHR', 'ATL'): 6900, ('CDG', 'ATL'): 7000, ('FRA', 'ATL'): 7300,
            
            # Transpacific
            ('LAX', 'NRT'): 8815, ('SFO', 'NRT'): 8614, ('LAX', 'ICN'): 9600,
            ('LAX', 'PVG'): 11129, ('SFO', 'HKG'): 13593,
            
            # Asia-Europe
            ('LHR', 'HKG'): 9648, ('FRA', 'PEK'): 7365, ('CDG', 'NRT'): 9714,
        }
        
        # Check if we have a known distance for this route
        route_key = (origin, destination)
        reverse_key = (destination, origin)
        
        if route_key in hub_distances:
            distance_km = hub_distances[route_key]
        elif reverse_key in hub_distances:
            distance_km = hub_distances[reverse_key]
        else:
            # Fall back to continent-based estimation
            continent_codes = {
                'A': 'North America', 'B': 'North America', 'C': 'North America', 'D': 'North America',
                'E': 'Europe', 'F': 'Europe', 'G': 'Europe', 'H': 'Europe',
                'I': 'Asia', 'J': 'Asia', 'K': 'Asia', 'L': 'Asia',
                'M': 'Oceania', 'N': 'Oceania', 'O': 'Oceania', 'P': 'South America',
                'Q': 'South America', 'R': 'South America', 'S': 'Africa', 'T': 'Africa',
                'U': 'Europe', 'V': 'Asia', 'W': 'Asia', 'X': 'Other',
                'Y': 'Other', 'Z': 'Asia'
            }
            
            origin_continent = continent_codes.get(origin[0] if origin else 'X', 'Other')
            dest_continent = continent_codes.get(destination[0] if destination else 'X', 'Other')
            
            if origin_continent == dest_continent:
                if origin[:2] == destination[:2]:
                    distance_km = random.uniform(200, 1200)  # Same country/region
                else:
                    distance_km = random.uniform(800, 3000)  # Same continent
            else:
                # Different continents
                intercontinental_distances = {
                    ('North America', 'Europe'): (5500, 8000),
                    ('North America', 'Asia'): (8000, 12000),
                    ('Europe', 'Asia'): (3000, 9000),
                    ('North America', 'South America'): (3000, 8000),
                    ('Europe', 'Africa'): (1500, 6000),
                    ('Asia', 'Oceania'): (3000, 8000),
                }
                
                pair = (origin_continent, dest_continent)
                reverse_pair = (dest_continent, origin_continent)
                
                if pair in intercontinental_distances:
                    min_dist, max_dist = intercontinental_distances[pair]
                elif reverse_pair in intercontinental_distances:
                    min_dist, max_dist = intercontinental_distances[reverse_pair]
                else:
                    min_dist, max_dist = 6000, 12000
                
                distance_km = random.uniform(min_dist, max_dist)
        
        # Calculate duration
        if distance_km <= 1500:  # Short-haul
            avg_speed = 600
            overhead = 30
        elif distance_km <= 4000:  # Medium-haul
            avg_speed = 700
            overhead = 45
        else:  # Long-haul
            avg_speed = 800
            overhead = 60
        
        flight_time_hours = distance_km / avg_speed
        total_minutes = int(flight_time_hours * 60) + overhead
        total_minutes = max(45, min(total_minutes, 960))  # 45 min to 16 hours
        
        return distance_km, timedelta(minutes=total_minutes)
    
    def select_aircraft(self, route: Dict[str, Any], distance_km: float, daily_flights: int) -> Optional[Dict[str, Any]]:
        """Select appropriate aircraft based on distance and demand"""
        
        if not self._aircraft_cache:
            return None
        
        # Get aircraft category based on distance
        aircraft_category = self.config.get_aircraft_category_by_distance(distance_km)
        target_capacity_range = aircraft_category['capacity_range']
        
        # Adjust capacity based on hub status and frequency
        min_capacity, max_capacity = target_capacity_range
        
        # Hub routes typically use larger aircraft
        if route['is_hub_route']:
            min_capacity = int(min_capacity * 1.2)
            max_capacity = int(max_capacity * 1.3)
        
        # High-frequency routes use smaller aircraft
        if daily_flights > 6:
            max_capacity = int(max_capacity * 0.8)
        elif daily_flights > 3:
            max_capacity = int(max_capacity * 0.9)
        
        # Filter aircraft by capacity range
        suitable_aircraft = [
            aircraft for aircraft in self._aircraft_cache
            if (min_capacity <= aircraft['capacity'] <= max_capacity)
        ]
        
        if not suitable_aircraft:
            # Expand search if no suitable aircraft found
            broader_min = max(50, min_capacity - 50)
            broader_max = min(500, max_capacity + 100)
            
            suitable_aircraft = [
                aircraft for aircraft in self._aircraft_cache
                if (broader_min <= aircraft['capacity'] <= broader_max)
            ]
        
        if suitable_aircraft:
            return random.choice(suitable_aircraft)
        
        # Final fallback
        return random.choice(self._aircraft_cache) if self._aircraft_cache else None
    
    def generate_departure_times(self, num_flights: int, airline_code: str) -> List[time]:
        """Generate realistic departure times"""
        
        if num_flights == 0:
            return []
        
        airline_pattern = self.config.get_airline_pattern(airline_code)
        peak_preference = airline_pattern['peak_preference']
        
        # Select time slots based on airline preference
        available_times = []
        
        # Add peak times with higher weight
        peak_times = [t for t in self.config.DEPARTURE_TIMES 
                     if t.hour in self.config.PEAK_HOURS]
        available_times.extend(peak_times * int(peak_preference * 10))
        
        # Add off-peak times
        offpeak_times = [t for t in self.config.DEPARTURE_TIMES 
                        if t.hour in self.config.OFF_PEAK_HOURS]
        available_times.extend(offpeak_times * int((1 - peak_preference) * 10))
        
        # Select unique times
        if num_flights >= len(available_times):
            return sorted(available_times[:num_flights])
        
        selected_times = random.sample(available_times, num_flights)
        return sorted(selected_times)
    
    def generate_flights_for_route_date(self, route: Dict[str, Any], date: datetime) -> List[Flight]:
        """Generate all flights for a specific route on a specific date"""
        
        # Estimate distance and duration
        distance_km, duration = self.estimate_distance_and_duration(route['origin'], route['destination'])
        
        # Calculate number of flights
        num_flights = self.calculate_daily_flights(route, date, distance_km)
        
        if num_flights == 0:
            return []
        
        # Generate departure times
        departure_times = self.generate_departure_times(num_flights, route['airline'])
        
        # Select appropriate aircraft
        aircraft = self.select_aircraft(route, distance_km, num_flights)
        
        if not aircraft:
            return []
        
        # Generate flights
        flights = []
        
        for i, departure_time in enumerate(departure_times):
            departure_dt = datetime.combine(date.date(), departure_time)
            arrival_dt = departure_dt + duration
            
            # Generate flight number
            airline_code = route['airline']
            base_number = ((route['route_id'] + date.timetuple().tm_yday) % 900) + 100
            
            if len(departure_times) > 1:
                flight_suffix = chr(65 + i) if i < 26 else str(i)
                flight_number = f"{airline_code}{base_number}{flight_suffix}"
            else:
                flight_number = f"{airline_code}{base_number}"
            
            # Ensure flight number is within 8 character limit
            if len(flight_number) > 8:
                available_chars = 8 - len(str(base_number)) - (1 if len(departure_times) > 1 else 0)
                airline_code_short = airline_code[:available_chars]
                
                if len(departure_times) > 1:
                    flight_suffix = chr(65 + i) if i < 26 else str(i % 10)
                    flight_number = f"{airline_code_short}{base_number}{flight_suffix}"
                else:
                    flight_number = f"{airline_code_short}{base_number}"
            
            flight = Flight(
                flightno=flight_number,
                from_airport=self._airport_cache[route['origin']]['id'],
                to_airport=self._airport_cache[route['destination']]['id'],
                departure=departure_dt,
                arrival=arrival_dt,
                airline_id=self._airline_cache[route['airline']]['id'],
                airplane_id=aircraft['id']
            )
            
            flights.append(flight)
        
        return flights
    
    def populate_flights(self, start_date: datetime, end_date: datetime, 
                        batch_size: int = 1000, max_routes: int = 2000) -> int:
        """Populate flights for the specified date range"""
        
        if self.verbose:
            print(f"Populating flights from {start_date.date()} to {end_date.date()}")
        
        with Session(self.db_manager.engine) as session:
            # Initialize caches
            self.initialize_caches(session)
            
            if not self._airport_cache or not self._airline_cache or not self._aircraft_cache:
                print("❌ Insufficient data in database for flight generation")
                return 0
            
            # Get prioritized routes (hub routes first)
            routes = self.get_prioritized_routes(session, max_routes)
            
            if not routes:
                print("❌ No valid routes found for flight generation")
                return 0
            
            total_flights = 0
            current_date = start_date
            days_processed = 0
            total_days = (end_date - start_date).days + 1
            
            if self.verbose:
                print(f"Processing {total_days} days with {len(routes)} routes")
                hub_routes = sum(1 for r in routes if r['is_hub_route'])
                print(f"Route breakdown: {hub_routes} hub routes, {len(routes) - hub_routes} non-hub routes")
            
            # Import tqdm for progress bar
            try:
                from tqdm import tqdm
                use_progress_bar = not self.verbose
            except ImportError:
                use_progress_bar = False
            
            # Create progress bar if not verbose
            if use_progress_bar:
                pbar = tqdm(
                    total=total_days,
                    desc="🛫 Generating hub flights",
                    unit="day",
                    colour='blue',
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} days ({percentage:3.0f}%) [{elapsed}<{remaining}] {postfix}'
                )
            
            try:
                while current_date <= end_date:
                    daily_flights = []
                    
                    # Generate flights for each route on this date
                    for route in routes:
                        try:
                            route_flights = self.generate_flights_for_route_date(route, current_date)
                            daily_flights.extend(route_flights)
                        except Exception as e:
                            if days_processed == 0 and self.verbose:
                                print(f"   Warning: Error generating flights for route {route['origin']}-{route['destination']}: {e}")
                    
                    # Batch insert
                    if daily_flights:
                        try:
                            for i in range(0, len(daily_flights), batch_size):
                                batch = daily_flights[i:i + batch_size]
                                session.add_all(batch)
                                session.commit()
                            
                            total_flights += len(daily_flights)
                        except Exception as e:
                            if self.verbose:
                                print(f"   Error inserting flights for {current_date.date()}: {e}")
                            session.rollback()
                    
                    days_processed += 1
                    
                    # Update progress
                    if use_progress_bar:
                        pbar.update(1)
                        pbar.set_postfix({
                            'Flights': f"{total_flights:,}",
                            'Today': len(daily_flights)
                        })
                    elif self.verbose and (days_processed % 30 == 0 or current_date == start_date or current_date == end_date):
                        progress_pct = (days_processed / total_days) * 100
                        print(f"   {progress_pct:.1f}% - {current_date.strftime('%Y-%m-%d')}: "
                              f"{len(daily_flights)} flights today, {total_flights:,} total")
                    
                    current_date += timedelta(days=1)
                
                if use_progress_bar:
                    pbar.close()
                
                if self.verbose:
                    print(f"✅ Flight generation completed: {total_flights:,} flights created")
                return total_flights
                
            except KeyboardInterrupt:
                if use_progress_bar:
                    pbar.close()
                print(f"\n⚠ Flight generation interrupted by user")
                return total_flights
            except Exception as e:
                if use_progress_bar:
                    pbar.close()
                print(f"\n❌ Fatal error during flight generation: {e}")
                raise
    
    def clear_flights_in_range(self, start_date: datetime, end_date: datetime) -> int:
        """Clear existing flights in the specified date range"""
        
        with Session(self.db_manager.engine) as session:
            count_query = select(func.count(Flight.flight_id)).where(
                Flight.departure >= start_date,
                Flight.departure <= end_date
            )
            existing_count = session.exec(count_query).first()
            
            if existing_count > 0:
                if self.verbose:
                    print(f"Clearing {existing_count:,} existing flights in date range...")
                
                # Delete in batches
                batch_size = 10000
                deleted_total = 0
                
                try:
                    from tqdm import tqdm
                    use_progress_bar = not self.verbose and existing_count > 1000
                except ImportError:
                    use_progress_bar = False
                
                if use_progress_bar:
                    pbar = tqdm(
                        total=existing_count,
                        desc="🗑️  Clearing flights",
                        unit="flight",
                        colour='red',
                        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} ({percentage:3.0f}%) [{elapsed}<{remaining}]'
                    )
                
                while True:
                    delete_query = select(Flight.flight_id).where(
                        Flight.departure >= start_date,
                        Flight.departure <= end_date
                    ).limit(batch_size)
                    
                    flight_ids = session.exec(delete_query).all()
                    
                    if not flight_ids:
                        break
                    
                    for flight_id in flight_ids:
                        flight = session.get(Flight, flight_id)
                        if flight:
                            session.delete(flight)
                    
                    session.commit()
                    deleted_total += len(flight_ids)
                    
                    if use_progress_bar:
                        pbar.update(len(flight_ids))
                    
                    if len(flight_ids) < batch_size:
                        break
                
                if use_progress_bar:
                    pbar.close()
                
                return deleted_total
            
            return 0


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Realistic Flight Population Script (Hub-Prioritized)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output (default: progress bar only)')
    parser.add_argument('--reset-db', action='store_true',
                       help='Reset database without prompting')
    parser.add_argument('--no-reset', action='store_true',
                       help='Keep existing data without prompting')
    args = parser.parse_args()
    
    if not DEPENDENCIES_AVAILABLE:
        return 1
    
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return 1
    
    load_dotenv()
    
    if args.verbose:
        print("Realistic Flight Population Script (Hub-Prioritized)")
        print("=" * 50)
        print("This script prioritizes routes involving major hub airports:")
        print("ATL, ORD, LHR, CDG, FRA, LAX, DFW, JFK, AMS, and others")
    
    # Initialize
    db_manager = DatabaseManager()
    populator = RealisticFlightPopulator(db_manager, verbose=args.verbose)
    
    # Define date range
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 6, 30)
    
    if args.verbose:
        print(f"\nDate range: {start_date.date()} to {end_date.date()}")
        print(f"Total days: {(end_date - start_date).days + 1}")
    
    # Handle database reset
    reset_db = False
    if args.reset_db:
        reset_db = True
    elif args.no_reset:
        reset_db = False
    else:
        response = input("Reset existing flight data? (y/N): ")
        reset_db = response.lower() == 'y'
    
    try:
        cleared_count = 0
        if reset_db:
            cleared_count = populator.clear_flights_in_range(start_date, end_date)
        
        # Generate new flights
        created_count = populator.populate_flights(start_date, end_date)
        
        print(f"✅ Hub-prioritized flight population completed!")
        if args.verbose:
            print(f"   Flights cleared: {cleared_count:,}")
            print(f"   Flights created: {created_count:,}")
            print(f"   Net change: {created_count - cleared_count:,}")
        else:
            print(f"   Created {created_count:,} flights with hub priority")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during flight population: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())