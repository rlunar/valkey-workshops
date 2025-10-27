#!/usr/bin/env python3
"""
Flight Population Script

Populate flights for all airports based on flight rules and route data
for the last year and upcoming year (2-year span total).
"""

import os
import sys
import random
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Tuple, Optional
from sqlmodel import Session, select, func
from decimal import Decimal

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.flight import Flight
from models.route import Route
from models.airport import Airport
from models.airline import Airline
from models.airplane import Airplane
from models.airplane_type import AirplaneType
from models.city import City, CityAirportRelation


class FlightPopulator:
    """Generate realistic flight schedules based on route data and flight rules"""
    
    def __init__(self, db_manager: DatabaseManager, verbose: bool = False):
        self.db_manager = db_manager
        self.verbose = verbose
        
        # Flight timing patterns (24-hour format)
        self.peak_hours = [7, 8, 9, 12, 13, 17, 18, 19, 20]
        self.off_peak_hours = [6, 10, 11, 14, 15, 16, 21, 22]
        self.night_hours = [23, 0, 1, 2, 3, 4, 5]
        
        # Seasonal multipliers
        self.seasonal_multipliers = {
            'winter': 0.85,  # Dec, Jan, Feb
            'spring': 1.0,   # Mar, Apr, May
            'summer': 1.3,   # Jun, Jul, Aug
            'fall': 1.1      # Sep, Oct, Nov
        }
        
        # Day of week multipliers
        self.dow_multipliers = {
            0: 1.2,  # Monday
            1: 1.1,  # Tuesday
            2: 1.0,  # Wednesday
            3: 1.1,  # Thursday
            4: 1.3,  # Friday
            5: 0.9,  # Saturday
            6: 1.0   # Sunday
        }
    
    def get_airport_tier(self, route_count: int) -> Dict[str, Any]:
        """Determine airport tier based on route count"""
        if route_count >= 500:
            return {
                'tier': 1,
                'name': 'Major Hub',
                'daily_flights': (6, 12),
                'weekly_pattern': [1.0] * 7,  # All days
                'seasonal_boost': 1.3
            }
        elif route_count >= 200:
            return {
                'tier': 2,
                'name': 'Regional Hub',
                'daily_flights': (2, 6),
                'weekly_pattern': [1.0] * 7,
                'seasonal_boost': 1.2
            }
        elif route_count >= 50:
            return {
                'tier': 3,
                'name': 'Secondary Airport',
                'daily_flights': (1, 3),
                'weekly_pattern': [1.0, 1.0, 1.0, 1.0, 1.0, 0.8, 0.9],
                'seasonal_boost': 1.15
            }
        elif route_count >= 10:
            return {
                'tier': 4,
                'name': 'Regional Airport',
                'daily_flights': (0.4, 1.0),  # 3-7 flights per week
                'weekly_pattern': [1.0, 0.5, 1.0, 0.5, 1.0, 0.3, 0.8],
                'seasonal_boost': 1.1
            }
        else:
            return {
                'tier': 5,
                'name': 'Local Airport',
                'daily_flights': (0.1, 0.4),  # 1-3 flights per week
                'weekly_pattern': [0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.3],
                'seasonal_boost': 1.05
            }
    
    def get_seasonal_multiplier(self, date: datetime) -> float:
        """Get seasonal multiplier for a given date"""
        month = date.month
        if month in [12, 1, 2]:
            return self.seasonal_multipliers['winter']
        elif month in [3, 4, 5]:
            return self.seasonal_multipliers['spring']
        elif month in [6, 7, 8]:
            return self.seasonal_multipliers['summer']
        else:
            return self.seasonal_multipliers['fall']
    
    def generate_flight_times(self, count: int, is_peak_route: bool = False) -> List[time]:
        """Generate realistic flight departure times"""
        times = []
        
        for _ in range(count):
            if is_peak_route:
                # Peak routes favor peak hours
                if random.random() < 0.7:
                    hour = random.choice(self.peak_hours)
                else:
                    hour = random.choice(self.off_peak_hours)
            else:
                # Regular distribution
                if random.random() < 0.5:
                    hour = random.choice(self.peak_hours)
                elif random.random() < 0.8:
                    hour = random.choice(self.off_peak_hours)
                else:
                    hour = random.choice(self.night_hours)
            
            minute = random.choice([0, 15, 30, 45])  # Common departure times
            times.append(time(hour, minute))
        
        return sorted(times)
    
    def calculate_flight_duration(self, origin_airport: Airport, dest_airport: Airport) -> timedelta:
        """Calculate estimated flight duration based on distance"""
        # Simple distance-based calculation (in reality, would use great circle distance)
        if origin_airport.latitude and origin_airport.longitude and \
           dest_airport.latitude and dest_airport.longitude:
            
            # Rough distance calculation
            lat_diff = abs(float(origin_airport.latitude) - float(dest_airport.latitude))
            lon_diff = abs(float(origin_airport.longitude) - float(dest_airport.longitude))
            distance_factor = (lat_diff + lon_diff) * 60  # Rough km estimate
            
            # Base flight time: 500 km/h average speed + 30 min overhead
            flight_minutes = int(distance_factor * 1.2) + 30
            
            # Cap at reasonable limits
            flight_minutes = max(30, min(flight_minutes, 960))  # 30 min to 16 hours
            
            return timedelta(minutes=flight_minutes)
        
        # Default duration if no coordinates
        return timedelta(hours=2)
    
    def get_aircraft_for_route(self, session: Session, route_distance: float, 
                              passenger_demand: int) -> Optional[Airplane]:
        """Select appropriate aircraft for route based on distance and demand"""
        
        # Define aircraft categories by capacity
        if passenger_demand > 300 or route_distance > 5000:
            # Wide-body for high demand or long-haul
            capacity_range = (250, 500)
        elif passenger_demand > 150 or route_distance > 2000:
            # Narrow-body for medium demand or medium-haul
            capacity_range = (120, 250)
        else:
            # Regional aircraft for short routes or low demand
            capacity_range = (50, 120)
        
        # Find suitable aircraft
        aircraft_query = (
            select(Airplane)
            .where(
                Airplane.capacity >= capacity_range[0],
                Airplane.capacity <= capacity_range[1]
            )
            .limit(100)
        )
        
        aircraft_list = session.exec(aircraft_query).all()
        
        if aircraft_list:
            return random.choice(aircraft_list)
        
        # Fallback: any aircraft
        fallback_query = select(Airplane).limit(100)
        fallback_list = session.exec(fallback_query).all()
        
        return random.choice(fallback_list) if fallback_list else None
    
    def generate_flight_number(self, airline_code: str, route_id: int) -> str:
        """Generate realistic flight number"""
        # Use airline code + route-based number
        flight_num = (route_id % 9000) + 1000  # 4-digit number
        return f"{airline_code}{flight_num}"
    
    def populate_flights_for_date_range(self, start_date: datetime, end_date: datetime, 
                                      batch_size: int = 1000) -> int:
        """Populate flights for a specific date range"""
        
        if self.verbose:
            print(f"Populating flights from {start_date.date()} to {end_date.date()}")
        
        with Session(self.db_manager.engine) as session:
            # Get all routes with airport and airline information
            routes_query = (
                select(
                    Route,
                    Airport.alias('origin_airport'),
                    Airport.alias('dest_airport'),
                    Airline
                )
                .join(Airport.alias('origin_airport'), 
                      Route.source_airport_id_openflights == Airport.alias('origin_airport').openflights_id)
                .join(Airport.alias('dest_airport'), 
                      Route.destination_airport_id_openflights == Airport.alias('dest_airport').openflights_id)
                .join(Airline, Route.airline_id_openflights == Airline.openflights_id)
                .where(
                    Route.source_airport_code.is_not(None),
                    Route.destination_airport_code.is_not(None),
                    Route.airline_code.is_not(None)
                )
            )
            
            routes_data = session.exec(routes_query).all()
            
            if not routes_data:
                print("No routes found with complete airport and airline data")
                return 0
            
            if self.verbose:
                print(f"Found {len(routes_data)} routes to process")
            
            # Get airport route counts for tier determination
            airport_route_counts = {}
            for route, origin_airport, dest_airport, airline in routes_data:
                origin_code = route.source_airport_code
                dest_code = route.destination_airport_code
                
                airport_route_counts[origin_code] = airport_route_counts.get(origin_code, 0) + 1
                airport_route_counts[dest_code] = airport_route_counts.get(dest_code, 0) + 1
            
            flights_created = 0
            current_date = start_date
            total_days = (end_date - start_date).days + 1
            
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
            
            while current_date <= end_date:
                daily_flights = []
                
                # Process each route for this date
                for route, origin_airport, dest_airport, airline in routes_data:
                    
                    # Determine airport tiers
                    origin_tier = self.get_airport_tier(
                        airport_route_counts.get(route.source_airport_code, 0)
                    )
                    dest_tier = self.get_airport_tier(
                        airport_route_counts.get(route.destination_airport_code, 0)
                    )
                    
                    # Use the higher tier for frequency calculation
                    route_tier = origin_tier if origin_tier['tier'] <= dest_tier['tier'] else dest_tier
                    
                    # Calculate base daily flights
                    min_flights, max_flights = route_tier['daily_flights']
                    base_daily_flights = random.uniform(min_flights, max_flights)
                    
                    # Apply seasonal multiplier
                    seasonal_mult = self.get_seasonal_multiplier(current_date)
                    seasonal_mult *= route_tier['seasonal_boost']
                    
                    # Apply day of week multiplier
                    dow_mult = self.dow_multipliers[current_date.weekday()]
                    dow_mult *= route_tier['weekly_pattern'][current_date.weekday()]
                    
                    # Calculate final flight count for this day
                    daily_flight_count = base_daily_flights * seasonal_mult * dow_mult
                    
                    # Convert to integer (with probability for fractional parts)
                    flights_today = int(daily_flight_count)
                    if random.random() < (daily_flight_count - flights_today):
                        flights_today += 1
                    
                    # Generate flights for this route on this day
                    if flights_today > 0:
                        flight_times = self.generate_flight_times(
                            flights_today, 
                            route_tier['tier'] <= 2
                        )
                        
                        flight_duration = self.calculate_flight_duration(origin_airport, dest_airport)
                        
                        # Get appropriate aircraft
                        estimated_demand = int(100 * (route_tier['tier'] ** -0.5))
                        aircraft = self.get_aircraft_for_route(
                            session, 1000, estimated_demand  # Default distance
                        )
                        
                        if not aircraft:
                            continue  # Skip if no aircraft available
                        
                        for i, departure_time in enumerate(flight_times):
                            # Create departure datetime
                            departure_dt = datetime.combine(current_date.date(), departure_time)
                            arrival_dt = departure_dt + flight_duration
                            
                            # Generate flight number (max 8 characters)
                            airline_code = airline.iata or airline.icao or "XX"
                            base_number = ((route.route_id or 0) % 900) + 100
                            
                            # For multiple daily flights, use different base numbers
                            if len(flight_times) > 1:
                                base_number = base_number + i
                            
                            flight_number = f"{airline_code}{base_number}"
                            
                            # Ensure flight number is within 8 character limit
                            if len(flight_number) > 8:
                                max_airline_len = 8 - len(str(base_number))
                                airline_code = airline_code[:max_airline_len]
                                flight_number = f"{airline_code}{base_number}"
                            
                            flight = Flight(
                                flightno=flight_number,
                                from_airport=origin_airport.airport_id,
                                to_airport=dest_airport.airport_id,
                                departure=departure_dt,
                                arrival=arrival_dt,
                                airline_id=airline.airline_id,
                                airplane_id=aircraft.airplane_id
                            )
                            
                            daily_flights.append(flight)
                
                # Batch insert daily flights
                if daily_flights:
                    session.add_all(daily_flights)
                    session.commit()
                    flights_created += len(daily_flights)
                    
                    if self.verbose and flights_created % batch_size == 0:
                        print(f"Created {flights_created:,} flights (Date: {current_date.date()})")
                
                # Update progress
                if use_progress_bar:
                    pbar.update(1)
                    pbar.set_postfix({
                        'Flights': f"{flights_created:,}",
                        'Today': len(daily_flights)
                    })
                
                current_date += timedelta(days=1)
            
            if use_progress_bar:
                pbar.close()
            
            if self.verbose:
                print(f"Total flights created: {flights_created:,}")
            return flights_created
    
    def clear_existing_flights(self, start_date: datetime, end_date: datetime) -> int:
        """Clear existing flights in the date range"""
        with Session(self.db_manager.engine) as session:
            delete_query = select(Flight).where(
                Flight.departure >= start_date,
                Flight.departure <= end_date
            )
            
            existing_flights = session.exec(delete_query).all()
            count = len(existing_flights)
            
            if count > 0:
                # Import tqdm for progress bar
                try:
                    from tqdm import tqdm
                    use_progress_bar = not self.verbose and count > 1000
                except ImportError:
                    use_progress_bar = False
                
                if use_progress_bar:
                    pbar = tqdm(
                        existing_flights,
                        desc="🗑️  Clearing flights",
                        unit="flight",
                        colour='red',
                        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} ({percentage:3.0f}%) [{elapsed}<{remaining}]'
                    )
                    for flight in pbar:
                        session.delete(flight)
                    pbar.close()
                else:
                    for flight in existing_flights:
                        session.delete(flight)
                
                session.commit()
                
                if self.verbose:
                    print(f"Cleared {count:,} existing flights in date range")
            
            return count
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get current database statistics"""
        with Session(self.db_manager.engine) as session:
            stats = {}
            
            stats['routes'] = session.exec(select(func.count(Route.route_id))).first()
            stats['airports'] = session.exec(select(func.count(Airport.airport_id))).first()
            stats['airlines'] = session.exec(select(func.count(Airline.airline_id))).first()
            stats['aircraft'] = session.exec(select(func.count(Airplane.airplane_id))).first()
            stats['flights'] = session.exec(select(func.count(Flight.flight_id))).first()
            
            return stats


def main():
    """Main function to populate flights"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Flight Population Script')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output (default: progress bar only)')
    parser.add_argument('--reset-db', action='store_true',
                       help='Reset database without prompting')
    parser.add_argument('--no-reset', action='store_true',
                       help='Keep existing data without prompting')
    args = parser.parse_args()
    
    if args.verbose:
        print("Flight Population Script")
        print("=" * 30)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    populator = FlightPopulator(db_manager, verbose=args.verbose)
    
    # Get current database stats
    if args.verbose:
        print("Current Database Statistics:")
        stats = populator.get_database_stats()
        for key, value in stats.items():
            print(f"  {key.capitalize()}: {value:,}")
        
        if stats['routes'] == 0:
            print("\n❌ No routes found in database. Please import route data first.")
            return 1
        
        if stats['aircraft'] == 0:
            print("\n❌ No aircraft found in database. Please import aircraft data first.")
            return 1
    
    # Define date range - optimized for 2025 and first half of 2026
    start_date = datetime(2025, 1, 1)  # Start of 2025
    end_date = datetime(2026, 6, 30)   # End of first half of 2026
    
    if args.verbose:
        print(f"\nGenerating flights for: {start_date.date()} to {end_date.date()}")
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
                print("\nClearing existing flights in date range...")
            cleared_count = populator.clear_existing_flights(start_date, end_date)
        
        # Populate flights
        if args.verbose:
            print("\nStarting flight population...")
        flights_created = populator.populate_flights_for_date_range(start_date, end_date)
        
        print(f"✅ Flight population completed successfully!")
        if args.verbose:
            print(f"   Flights created: {flights_created:,}")
            print(f"   Flights cleared: {cleared_count:,}")
            print(f"   Net change: {flights_created - cleared_count:,}")
            
            # Final stats
            print("\nFinal Database Statistics:")
            final_stats = populator.get_database_stats()
            for key, value in final_stats.items():
                print(f"  {key.capitalize()}: {value:,}")
        else:
            print(f"   Created {flights_created:,} flights")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during flight population: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())