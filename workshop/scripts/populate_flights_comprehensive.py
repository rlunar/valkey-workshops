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
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.config = FlightConfig()
        
        # Cache for database lookups
        self._airport_cache = {}
        self._airline_cache = {}
        self._aircraft_cache = []
        self._route_counts_cache = {}
    
    def initialize_caches(self, session: Session):
        """Initialize lookup caches for better performance"""
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
        
        print(f"Cached {len(self._airport_cache)} airports, "
              f"{len(self._airline_cache)} airlines, "
              f"{len(self._aircraft_cache)} aircraft")
    
    def calculate_airport_route_counts(self, session: Session) -> Dict[str, int]:
        """Calculate total route counts per airport (inbound + outbound)"""
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
        
        print(f"Selected {len(routes)} valid routes for flight generation")
        return routes
    
    def calculate_daily_flights(self, route: Dict[str, Any], date: datetime) -> int:
        """Calculate number of flights for a route on a specific date"""
        
        origin_code = route['origin']
        airline_code = route['airline']
        
        # Get airport tier based on route count
        origin_routes = self._route_counts_cache.get(origin_code, 0)
        airport_tier = self.config.get_airport_tier(origin_routes)
        
        # Get base daily flight range
        min_daily, max_daily = airport_tier['daily_flights_range']
        base_flights = random.uniform(min_daily, max_daily)
        
        # Apply seasonal multiplier
        seasonal_mult = self.config.get_seasonal_multiplier(date.month)
        seasonal_mult *= airport_tier['seasonal_boost']
        
        # Apply day of week multiplier
        dow_mult = self.config.DAY_OF_WEEK_MULTIPLIERS[date.weekday()]
        
        # Apply airline-specific patterns
        airline_pattern = self.config.get_airline_pattern(airline_code)
        airline_mult = airline_pattern['frequency_boost']
        
        # Codeshare routes have reduced frequency
        codeshare_mult = 0.7 if route['codeshare'] else 1.0
        
        # Calculate final flight count
        total_flights = base_flights * seasonal_mult * dow_mult * airline_mult * codeshare_mult
        
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
    
    def estimate_flight_duration(self, origin: str, destination: str) -> timedelta:
        """Estimate flight duration between airports"""
        
        # Simple estimation based on airport codes (very basic)
        # In reality, would use great circle distance calculation
        
        if origin == destination:
            return timedelta(hours=1)
        
        # Rough estimation based on geographic patterns in airport codes
        origin_region = origin[0] if origin else 'X'
        dest_region = destination[0] if destination else 'X'
        
        if origin_region == dest_region:
            # Same region - shorter flight
            duration_minutes = random.randint(60, 180)  # 1-3 hours
        else:
            # Different regions - longer flight
            duration_minutes = random.randint(120, 480)  # 2-8 hours
        
        return timedelta(minutes=duration_minutes)
    
    def select_aircraft(self, route: Dict[str, Any], estimated_passengers: int) -> Optional[Dict[str, Any]]:
        """Select appropriate aircraft for the route"""
        
        if not self._aircraft_cache:
            return None
        
        # Estimate distance (simplified)
        distance_km = 1000  # Default assumption
        
        # Get aircraft category
        category = self.config.get_aircraft_category(distance_km, estimated_passengers)
        category_config = self.config.AIRCRAFT_CATEGORIES[category]
        
        # Filter aircraft by capacity range
        suitable_aircraft = [
            aircraft for aircraft in self._aircraft_cache
            if (category_config['capacity_range'][0] <= aircraft['capacity'] <= 
                category_config['capacity_range'][1])
        ]
        
        if suitable_aircraft:
            return random.choice(suitable_aircraft)
        
        # Fallback to any aircraft
        return random.choice(self._aircraft_cache)
    
    def generate_flights_for_route_date(self, route: Dict[str, Any], date: datetime) -> List[Flight]:
        """Generate all flights for a specific route on a specific date"""
        
        # Calculate number of flights
        num_flights = self.calculate_daily_flights(route, date)
        
        if num_flights == 0:
            return []
        
        # Generate departure times
        departure_times = self.generate_departure_times(num_flights, route['airline'])
        
        # Estimate flight duration
        duration = self.estimate_flight_duration(route['origin'], route['destination'])
        
        # Select aircraft
        estimated_passengers = num_flights * 150  # Rough estimate
        aircraft = self.select_aircraft(route, estimated_passengers)
        
        if not aircraft:
            return []
        
        # Generate flights
        flights = []
        
        for i, departure_time in enumerate(departure_times):
            # Create departure datetime
            departure_dt = datetime.combine(date.date(), departure_time)
            arrival_dt = departure_dt + duration
            
            # Generate flight number (max 8 characters)
            base_number = (route['route_id'] % 900) + 100  # 3-digit number
            
            # For multiple daily flights, use different base numbers
            if len(departure_times) > 1:
                base_number = base_number + i
            
            flight_number = f"{route['airline']}{base_number}"
            
            # Ensure flight number is within 8 character limit
            if len(flight_number) > 8:
                # Truncate airline code if needed
                max_airline_len = 8 - len(str(base_number))
                airline_code = route['airline'][:max_airline_len]
                flight_number = f"{airline_code}{base_number}"
            
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
        
        print(f"Populating flights from {start_date.date()} to {end_date.date()}")
        
        with Session(self.db_manager.engine) as session:
            # Initialize caches
            self.initialize_caches(session)
            
            if not self._airport_cache or not self._airline_cache or not self._aircraft_cache:
                print("❌ Insufficient data in database for flight generation")
                return 0
            
            # Get route sample
            routes = self.get_routes_sample(session, max_routes)
            
            if not routes:
                print("❌ No valid routes found for flight generation")
                return 0
            
            total_flights = 0
            current_date = start_date
            
            print(f"Processing {(end_date - start_date).days + 1} days with {len(routes)} routes")
            
            while current_date <= end_date:
                daily_flights = []
                
                # Generate flights for each route on this date
                for route in routes:
                    route_flights = self.generate_flights_for_route_date(route, current_date)
                    daily_flights.extend(route_flights)
                
                # Batch insert
                if daily_flights:
                    # Insert in batches
                    for i in range(0, len(daily_flights), batch_size):
                        batch = daily_flights[i:i + batch_size]
                        session.add_all(batch)
                        session.commit()
                    
                    total_flights += len(daily_flights)
                
                # Progress update
                if current_date.day == 1 or current_date == start_date:
                    print(f"Processed {current_date.strftime('%Y-%m-%d')}: "
                          f"{len(daily_flights)} flights today, {total_flights:,} total")
                
                current_date += timedelta(days=1)
            
            print(f"✅ Flight generation completed: {total_flights:,} flights created")
            return total_flights
    
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
                print(f"Clearing {existing_count:,} existing flights in date range...")
                
                # Delete in batches to avoid memory issues
                batch_size = 10000
                deleted_total = 0
                
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
                    
                    if len(flight_ids) < batch_size:
                        break
                
                print(f"Cleared {deleted_total:,} flights")
                return deleted_total
            
            return 0


def main():
    """Main function"""
    if not DEPENDENCIES_AVAILABLE:
        return 1
    
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return 1
    
    load_dotenv()
    
    print("Comprehensive Flight Population Script")
    print("=" * 40)
    
    # Show configuration
    FlightConfig.print_configuration_summary()
    
    # Initialize
    db_manager = DatabaseManager()
    populator = ComprehensiveFlightPopulator(db_manager)
    
    # Define date range
    today = datetime.now()
    start_date = datetime(today.year - 1, 1, 1)  # Last year
    end_date = datetime(today.year + 1, 12, 31)  # Next year
    
    print(f"\nProposed date range: {start_date.date()} to {end_date.date()}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    
    # Get user preferences
    print("\nOptions:")
    print("1. Full 2-year population (recommended)")
    print("2. Current year only")
    print("3. Custom date range")
    print("4. Test run (1 month)")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '2':
        start_date = datetime(today.year, 1, 1)
        end_date = datetime(today.year, 12, 31)
    elif choice == '3':
        start_str = input("Start date (YYYY-MM-DD): ").strip()
        end_str = input("End date (YYYY-MM-DD): ").strip()
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d')
        except ValueError:
            print("Invalid date format")
            return 1
    elif choice == '4':
        start_date = datetime(today.year, today.month, 1)
        end_date = start_date + timedelta(days=30)
    
    print(f"\nFinal date range: {start_date.date()} to {end_date.date()}")
    
    # Confirmation
    response = input("\nProceed with flight generation? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return 0
    
    try:
        # Clear existing flights
        cleared_count = populator.clear_flights_in_range(start_date, end_date)
        
        # Generate new flights
        created_count = populator.populate_flights(start_date, end_date)
        
        print(f"\n🎉 Flight population completed!")
        print(f"   Flights cleared: {cleared_count:,}")
        print(f"   Flights created: {created_count:,}")
        print(f"   Net change: {created_count - cleared_count:,}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during flight population: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())