#!/usr/bin/env python3
"""
Comprehensive Flight Population Script

Generate realistic flight schedules based on flight rules, route data, and airport tiers.
Implements the recommendations from docs/flight_rules.md
"""

import os
import sys
import random
import math
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


class ComprehensiveFlightPopulator:
    """Generate flights using comprehensive flight rules and realistic patterns"""
    
    def __init__(self, db_manager: DatabaseManager, verbose: bool = False):
        self.db_manager = db_manager
        self.config = FlightConfig()
        self.verbose = verbose
        
        # Cache for database lookups
        self._airport_cache = {}
        self._airline_cache = {}
        self._aircraft_cache = []
        self._route_counts_cache = {}
    
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
    
    def get_routes_sample(self, session: Session, sample_size: int = 2000) -> List[Dict[str, Any]]:
        """Get a representative sample of routes"""
        
        # Get routes with complete data
        routes_query = (
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
                Route.airline_code.is_not(None)
            )
            .limit(sample_size)
        )
        
        routes = []
        for route in session.exec(routes_query).all():
            # Skip if airports or airline not in cache
            if (route.source_airport_code not in self._airport_cache or
                route.destination_airport_code not in self._airport_cache or
                route.airline_code not in self._airline_cache):
                continue
            
            routes.append({
                'route_id': route.route_id,
                'origin': route.source_airport_code,
                'destination': route.destination_airport_code,
                'airline': route.airline_code,
                'codeshare': route.codeshare or False,
                'stops': route.stops or 0,
                'equipment': route.equipment
            })
        
        if self.verbose:
            print(f"Selected {len(routes)} valid routes for flight generation")
        return routes
    
    def calculate_daily_flights(self, route: Dict[str, Any], date: datetime, distance_km: float) -> int:
        """Calculate number of flights for a route on a specific date based on updated flight rules"""
        
        origin_code = route['origin']
        dest_code = route['destination']
        airline_code = route['airline']
        
        # Get airport tiers for both origin and destination
        origin_routes = self._route_counts_cache.get(origin_code, 0)
        dest_routes = self._route_counts_cache.get(dest_code, 0)
        
        origin_tier = self.config.get_airport_tier(origin_routes)
        dest_tier = self.config.get_airport_tier(dest_routes)
        
        # Use the higher tier (lower tier number) for frequency calculation
        route_tier = origin_tier if origin_tier['min_routes'] >= dest_tier['min_routes'] else dest_tier
        
        # Distance-based frequency adjustments per flight rules
        if distance_km <= 1500:  # Short-haul
            if route_tier['min_routes'] >= 500:  # Tier 1
                base_flights = random.uniform(8, 15)
            elif route_tier['min_routes'] >= 200:  # Tier 2
                base_flights = random.uniform(4, 8)
            elif route_tier['min_routes'] >= 50:  # Tier 3
                base_flights = random.uniform(2, 4)
            elif route_tier['min_routes'] >= 10:  # Tier 4
                base_flights = random.uniform(0.4, 1.0)  # 3-7 per week
            else:  # Tier 5
                base_flights = random.uniform(0.1, 0.4)  # 1-3 per week
        elif distance_km <= 4000:  # Medium-haul
            if route_tier['min_routes'] >= 500:  # Tier 1
                base_flights = random.uniform(4, 8)
            elif route_tier['min_routes'] >= 200:  # Tier 2
                base_flights = random.uniform(2, 4)
            elif route_tier['min_routes'] >= 50:  # Tier 3
                base_flights = random.uniform(1, 2)
            elif route_tier['min_routes'] >= 10:  # Tier 4
                base_flights = random.uniform(0.3, 0.6)  # 2-4 per week
            else:  # Tier 5
                base_flights = 0  # No medium-haul for Tier 5
        else:  # Long-haul (4000+ km)
            if route_tier['min_routes'] >= 500:  # Tier 1
                base_flights = random.uniform(1, 3)
            elif route_tier['min_routes'] >= 200:  # Tier 2
                base_flights = random.uniform(0.4, 1.0)  # 3-7 per week
            elif route_tier['min_routes'] >= 50:  # Tier 3
                base_flights = random.uniform(0.4, 0.7)  # 3-5 per week (seasonal)
            else:  # Tier 4-5
                base_flights = 0  # Charter/seasonal only
        
        # Apply seasonal multiplier
        seasonal_mult = self.config.get_seasonal_multiplier(date.month)
        
        # Enhanced seasonal boost for tourism routes (long-haul)
        if distance_km > 4000:
            seasonal_mult *= 1.2  # Tourism boost
        
        # Apply day of week multiplier with distance consideration
        dow_mult = self.config.DAY_OF_WEEK_MULTIPLIERS[date.weekday()]
        
        # Business routes (short/medium haul) have stronger weekday patterns
        if distance_km <= 4000:
            if date.weekday() < 5:  # Weekdays
                dow_mult *= 1.1
            else:  # Weekends
                dow_mult *= 0.9
        
        # Apply airline-specific patterns
        airline_pattern = self.config.get_airline_pattern(airline_code)
        airline_mult = airline_pattern['frequency_boost']
        
        # Codeshare routes have reduced frequency
        codeshare_mult = 0.7 if route['codeshare'] else 1.0
        
        # Route efficiency scoring (simplified)
        # Higher tier destinations get priority
        tier_priority = 1.0
        if route_tier['min_routes'] >= 500:
            tier_priority = 1.2
        elif route_tier['min_routes'] >= 200:
            tier_priority = 1.1
        elif route_tier['min_routes'] < 50:
            tier_priority = 0.8
        
        # Calculate final flight count
        total_flights = base_flights * seasonal_mult * dow_mult * airline_mult * codeshare_mult * tier_priority
        
        # Convert to integer with probabilistic rounding
        flights_today = int(total_flights)
        if random.random() < (total_flights - flights_today):
            flights_today += 1
        
        return max(0, flights_today)
    
    def generate_departure_times(self, num_flights: int, airline_code: str) -> List[time]:
        """Generate realistic departure times based on airline patterns"""
        
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
    
    def estimate_distance_and_duration(self, origin: str, destination: str) -> Tuple[float, timedelta]:
        """Estimate distance and flight duration between airports"""
        
        if origin == destination:
            return 0.0, timedelta(hours=1)
        
        # Enhanced distance estimation based on airport code patterns and geography
        # This is still simplified - in production would use actual coordinates
        
        # Continental patterns (very rough approximation)
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
        
        # Distance estimation based on continental patterns
        if origin_continent == dest_continent:
            if origin[:2] == destination[:2]:
                # Same country/region
                distance_km = random.uniform(200, 1200)  # Short domestic
            else:
                # Same continent, different countries
                distance_km = random.uniform(800, 3000)  # Medium continental
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
            
            # Get distance range for continent pair
            pair = (origin_continent, dest_continent)
            reverse_pair = (dest_continent, origin_continent)
            
            if pair in intercontinental_distances:
                min_dist, max_dist = intercontinental_distances[pair]
            elif reverse_pair in intercontinental_distances:
                min_dist, max_dist = intercontinental_distances[reverse_pair]
            else:
                # Default long-haul
                min_dist, max_dist = 6000, 12000
            
            distance_km = random.uniform(min_dist, max_dist)
        
        # Calculate duration using flight rules speed estimates
        if distance_km <= 1500:  # Short-haul
            avg_speed = 600  # km/h
            overhead = 30    # minutes
        elif distance_km <= 4000:  # Medium-haul
            avg_speed = 700  # km/h
            overhead = 45    # minutes
        else:  # Long-haul
            avg_speed = 800  # km/h
            overhead = 60    # minutes
        
        flight_time_hours = distance_km / avg_speed
        total_minutes = int(flight_time_hours * 60) + overhead
        
        # Ensure reasonable bounds
        total_minutes = max(45, min(total_minutes, 960))  # 45 min to 16 hours
        
        return distance_km, timedelta(minutes=total_minutes)
    
    def select_aircraft(self, route: Dict[str, Any], distance_km: float, daily_flights: int) -> Optional[Dict[str, Any]]:
        """Select appropriate aircraft based on distance and demand following flight rules"""
        
        if not self._aircraft_cache:
            return None
        
        # Estimate passenger demand based on route tier and daily flights
        origin_routes = self._route_counts_cache.get(route['origin'], 0)
        dest_routes = self._route_counts_cache.get(route['destination'], 0)
        max_routes = max(origin_routes, dest_routes)
        
        # Base passenger estimate
        if max_routes >= 500:  # Tier 1
            base_passengers = 180
        elif max_routes >= 200:  # Tier 2
            base_passengers = 140
        elif max_routes >= 50:  # Tier 3
            base_passengers = 100
        else:  # Tier 4-5
            base_passengers = 70
        
        # Adjust for flight frequency (more flights = smaller aircraft)
        if daily_flights > 6:
            base_passengers = int(base_passengers * 0.7)
        elif daily_flights > 3:
            base_passengers = int(base_passengers * 0.85)
        
        # Aircraft selection based on distance rules from flight_rules.md
        aircraft_category = self.config.get_aircraft_category_by_distance(distance_km)
        target_capacity_range = aircraft_category['capacity_range']
        
        # Adjust capacity based on passenger demand and frequency
        min_capacity, max_capacity = target_capacity_range
        
        # For high-frequency routes, prefer smaller aircraft
        if daily_flights > 6:
            max_capacity = int(max_capacity * 0.8)
        elif daily_flights > 3:
            max_capacity = int(max_capacity * 0.9)
        
        # For low-demand routes, prefer smaller aircraft within category
        if base_passengers < min_capacity * 0.6:
            max_capacity = int(min_capacity * 1.2)
        
        # Ensure we stay within reasonable bounds
        target_capacity_range = (max(30, min_capacity), min(500, max_capacity))
        
        # Filter aircraft by capacity range
        suitable_aircraft = [
            aircraft for aircraft in self._aircraft_cache
            if (target_capacity_range[0] <= aircraft['capacity'] <= target_capacity_range[1])
        ]
        
        # If no suitable aircraft in range, expand search
        if not suitable_aircraft:
            # Try broader capacity range
            broader_min = max(50, target_capacity_range[0] - 50)
            broader_max = min(500, target_capacity_range[1] + 100)
            
            suitable_aircraft = [
                aircraft for aircraft in self._aircraft_cache
                if (broader_min <= aircraft['capacity'] <= broader_max)
            ]
        
        if suitable_aircraft:
            # Prefer aircraft closer to estimated passenger demand
            def capacity_score(aircraft):
                capacity = aircraft['capacity']
                # Score based on how close capacity is to passenger demand
                if capacity >= base_passengers:
                    return 1.0 / (1.0 + (capacity - base_passengers) / base_passengers)
                else:
                    return capacity / base_passengers
            
            # Sort by capacity score and add some randomness
            suitable_aircraft.sort(key=capacity_score, reverse=True)
            
            # Select from top 30% with some randomness
            top_count = max(1, len(suitable_aircraft) // 3)
            return random.choice(suitable_aircraft[:top_count])
        
        # Final fallback to any aircraft
        return random.choice(self._aircraft_cache) if self._aircraft_cache else None
    
    def generate_flights_for_route_date(self, route: Dict[str, Any], date: datetime) -> List[Flight]:
        """Generate all flights for a specific route on a specific date"""
        
        # Estimate distance and duration
        distance_km, duration = self.estimate_distance_and_duration(route['origin'], route['destination'])
        
        # Calculate number of flights based on distance
        num_flights = self.calculate_daily_flights(route, date, distance_km)
        
        if num_flights == 0:
            return []
        
        # Generate departure times
        departure_times = self.generate_departure_times(num_flights, route['airline'])
        
        # Select appropriate aircraft based on distance and demand
        aircraft = self.select_aircraft(route, distance_km, num_flights)
        
        if not aircraft:
            return []
        
        # Generate flights
        flights = []
        
        for i, departure_time in enumerate(departure_times):
            # Create departure datetime
            departure_dt = datetime.combine(date.date(), departure_time)
            arrival_dt = departure_dt + duration
            
            # Generate flight number (max 8 characters) with better logic
            airline_code = route['airline']
            
            # Create base number from route and date for consistency
            base_number = ((route['route_id'] + date.timetuple().tm_yday) % 900) + 100
            
            # For multiple daily flights, use different suffixes
            if len(departure_times) > 1:
                flight_suffix = chr(65 + i) if i < 26 else str(i)  # A, B, C... or numbers
                flight_number = f"{airline_code}{base_number}{flight_suffix}"
            else:
                flight_number = f"{airline_code}{base_number}"
            
            # Ensure flight number is within 8 character limit
            if len(flight_number) > 8:
                # Truncate airline code if needed
                available_chars = 8 - len(str(base_number)) - (1 if len(departure_times) > 1 else 0)
                airline_code_short = airline_code[:available_chars]
                
                if len(departure_times) > 1:
                    flight_suffix = chr(65 + i) if i < 26 else str(i % 10)
                    flight_number = f"{airline_code_short}{base_number}{flight_suffix}"
                else:
                    flight_number = f"{airline_code_short}{base_number}"
            
            # Validate flight number length
            if len(flight_number) > 8:
                # Emergency fallback - use just airline + 3 digits
                emergency_num = (base_number + i) % 1000
                flight_number = f"{airline_code[:5]}{emergency_num:03d}"
            
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
                        batch_size: int = 1000, max_routes: int = 1000) -> int:
        """Populate flights for the specified date range"""
        
        if self.verbose:
            print(f"Populating flights from {start_date.date()} to {end_date.date()}")
        
        with Session(self.db_manager.engine) as session:
            # Initialize caches
            self.initialize_caches(session)
            
            if not self._airport_cache or not self._airline_cache or not self._aircraft_cache:
                print("❌ Insufficient data in database for flight generation")
                if self.verbose:
                    print(f"   Airports: {len(self._airport_cache)}")
                    print(f"   Airlines: {len(self._airline_cache)}")
                    print(f"   Aircraft: {len(self._aircraft_cache)}")
                return 0
            
            # Get route sample
            routes = self.get_routes_sample(session, max_routes)
            
            if not routes:
                print("❌ No valid routes found for flight generation")
                return 0
            
            total_flights = 0
            current_date = start_date
            days_processed = 0
            total_days = (end_date - start_date).days + 1
            
            if self.verbose:
                print(f"Processing {total_days} days with {len(routes)} routes")
                print("Flight generation progress:")
            
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
                    desc="🛫 Generating flights",
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
                            # Log route-specific errors but continue
                            if days_processed == 0 and self.verbose:  # Only log on first day to avoid spam
                                print(f"   Warning: Error generating flights for route {route['origin']}-{route['destination']}: {e}")
                    
                    # Batch insert
                    if daily_flights:
                        try:
                            # Insert in batches
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
                if self.verbose:
                    print(f"   Processed {days_processed}/{total_days} days")
                    print(f"   Created {total_flights:,} flights so far")
                return total_flights
            except Exception as e:
                if use_progress_bar:
                    pbar.close()
                print(f"\n❌ Fatal error during flight generation: {e}")
                if self.verbose:
                    print(f"   Processed {days_processed}/{total_days} days")
                    print(f"   Created {total_flights:,} flights before error")
                raise
    
    def clear_flights_in_range(self, start_date: datetime, end_date: datetime) -> int:
        """Clear existing flights in the specified date range"""
        
        with Session(self.db_manager.engine) as session:
            # Count existing flights
            count_query = select(func.count(Flight.flight_id)).where(
                Flight.departure >= start_date,
                Flight.departure <= end_date
            )
            existing_count = session.exec(count_query).first()
            
            if existing_count > 0:
                if self.verbose:
                    print(f"Clearing {existing_count:,} existing flights in date range...")
                
                # Delete in batches to avoid memory issues
                batch_size = 10000
                deleted_total = 0
                
                # Import tqdm for progress bar
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
                
                if self.verbose:
                    print(f"Cleared {deleted_total:,} flights")
                return deleted_total
            
            return 0


def main():
    """Main function"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Comprehensive Flight Population Script')
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
        print("Comprehensive Flight Population Script")
        print("=" * 40)
        FlightConfig.print_configuration_summary()
    
    # Initialize
    db_manager = DatabaseManager()
    populator = ComprehensiveFlightPopulator(db_manager, verbose=args.verbose)
    
    # Define date range - default to full 2-year population
    today = datetime.now()
    start_date = datetime(today.year - 1, 1, 1)  # Last year
    end_date = datetime(today.year + 1, 12, 31)  # Next year
    
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
        # Only ask about database reset
        response = input("Reset existing flight data? (y/N): ")
        reset_db = response.lower() == 'y'
    
    try:
        cleared_count = 0
        if reset_db:
            if args.verbose:
                print("\nClearing existing flights...")
            cleared_count = populator.clear_flights_in_range(start_date, end_date)
        
        # Generate new flights
        if args.verbose:
            print("\nGenerating flights...")
        created_count = populator.populate_flights(start_date, end_date)
        
        print(f"✅ Flight population completed!")
        if args.verbose:
            print(f"   Flights cleared: {cleared_count:,}")
            print(f"   Flights created: {created_count:,}")
            print(f"   Net change: {created_count - cleared_count:,}")
        else:
            print(f"   Created {created_count:,} flights")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during flight population: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())