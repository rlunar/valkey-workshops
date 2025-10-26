#!/usr/bin/env python3
"""
Simplified Flight Population Script

Generate flights based on existing routes with realistic scheduling patterns.
"""

import os
import sys
import random
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional
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
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False


class SimpleFlightPopulator:
    """Generate flights based on route data and flight rules"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # Common departure times (24-hour format)
        self.departure_times = [
            time(6, 0), time(7, 30), time(9, 0), time(10, 30),
            time(12, 0), time(13, 30), time(15, 0), time(16, 30),
            time(18, 0), time(19, 30), time(21, 0), time(22, 30)
        ]
        
        # Flight frequency by airport route count
        self.frequency_rules = {
            500: {'daily': (8, 12), 'name': 'Major Hub'},      # 500+ routes
            200: {'daily': (4, 8), 'name': 'Regional Hub'},    # 200-499 routes  
            50: {'daily': (2, 4), 'name': 'Secondary'},        # 50-199 routes
            10: {'daily': (1, 2), 'name': 'Regional'},         # 10-49 routes
            0: {'daily': (0.3, 1), 'name': 'Local'}            # 1-9 routes
        }
    
    def get_airport_frequency(self, route_count: int) -> Dict[str, Any]:
        """Get flight frequency rules for airport based on route count"""
        for threshold in sorted(self.frequency_rules.keys(), reverse=True):
            if route_count >= threshold:
                return self.frequency_rules[threshold]
        return self.frequency_rules[0]
    
    def get_route_counts_by_airport(self, session: Session) -> Dict[str, int]:
        """Get route counts for each airport"""
        print("Calculating airport route counts...")
        
        # Count outbound routes
        outbound_query = (
            select(Route.source_airport_code, func.count(Route.route_id).label('count'))
            .where(Route.source_airport_code.is_not(None))
            .group_by(Route.source_airport_code)
        )
        
        # Count inbound routes  
        inbound_query = (
            select(Route.destination_airport_code, func.count(Route.route_id).label('count'))
            .where(Route.destination_airport_code.is_not(None))
            .group_by(Route.destination_airport_code)
        )
        
        route_counts = {}
        
        # Add outbound counts
        for airport_code, count in session.exec(outbound_query).all():
            route_counts[airport_code] = route_counts.get(airport_code, 0) + count
            
        # Add inbound counts
        for airport_code, count in session.exec(inbound_query).all():
            route_counts[airport_code] = route_counts.get(airport_code, 0) + count
        
        print(f"Found route counts for {len(route_counts)} airports")
        return route_counts
    
    def get_sample_routes(self, session: Session, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get a sample of routes with complete data"""
        
        routes_query = (
            select(
                Route.route_id,
                Route.source_airport_code,
                Route.destination_airport_code,
                Route.airline_code,
                Route.equipment
            )
            .where(
                Route.source_airport_code.is_not(None),
                Route.destination_airport_code.is_not(None),
                Route.airline_code.is_not(None)
            )
            .limit(limit)
        )
        
        routes = []
        for route in session.exec(routes_query).all():
            routes.append({
                'route_id': route.route_id,
                'origin': route.source_airport_code,
                'destination': route.destination_airport_code,
                'airline': route.airline_code,
                'equipment': route.equipment
            })
        
        return routes
    
    def get_airport_ids(self, session: Session) -> Dict[str, int]:
        """Get mapping of airport codes to IDs"""
        airport_query = select(Airport.iata, Airport.airport_id).where(Airport.iata.is_not(None))
        
        airport_ids = {}
        for iata, airport_id in session.exec(airport_query).all():
            airport_ids[iata] = airport_id
            
        return airport_ids
    
    def get_airline_ids(self, session: Session) -> Dict[str, int]:
        """Get mapping of airline codes to IDs"""
        airline_query = select(Airline.iata, Airline.airline_id).where(Airline.iata.is_not(None))
        
        airline_ids = {}
        for iata, airline_id in session.exec(airline_query).all():
            airline_ids[iata] = airline_id
            
        return airline_ids
    
    def get_random_aircraft(self, session: Session) -> Optional[int]:
        """Get a random aircraft ID"""
        aircraft_query = select(Airplane.airplane_id).limit(100)
        aircraft_list = session.exec(aircraft_query).all()
        
        return random.choice(aircraft_list) if aircraft_list else None
    
    def calculate_flight_duration(self, origin: str, destination: str) -> timedelta:
        """Estimate flight duration based on route"""
        # Simple duration estimation
        if origin == destination:
            return timedelta(hours=1)
        
        # Rough estimation based on airport codes (very simplified)
        base_duration = random.randint(60, 300)  # 1-5 hours
        return timedelta(minutes=base_duration)
    
    def generate_flights_for_route(self, route: Dict[str, Any], date: datetime,
                                 route_counts: Dict[str, int], airport_ids: Dict[str, int],
                                 airline_ids: Dict[str, int], aircraft_id: int) -> List[Flight]:
        """Generate flights for a specific route on a specific date"""
        
        origin_code = route['origin']
        dest_code = route['destination']
        airline_code = route['airline']
        
        # Check if we have required IDs
        if (origin_code not in airport_ids or dest_code not in airport_ids or 
            airline_code not in airline_ids):
            return []
        
        # Get route count for origin airport (use for frequency)
        origin_routes = route_counts.get(origin_code, 0)
        freq_rules = self.get_airport_frequency(origin_routes)
        
        # Calculate number of flights for this route on this date
        min_daily, max_daily = freq_rules['daily']
        
        # Add some randomness and day-of-week variation
        dow_multiplier = 1.0
        if date.weekday() in [4, 6]:  # Friday, Sunday - higher traffic
            dow_multiplier = 1.3
        elif date.weekday() == 5:  # Saturday - lower traffic
            dow_multiplier = 0.7
        
        daily_flights = random.uniform(min_daily, max_daily) * dow_multiplier
        
        # Convert to integer number of flights
        num_flights = int(daily_flights)
        if random.random() < (daily_flights - num_flights):
            num_flights += 1
        
        if num_flights == 0:
            return []
        
        # Generate flights
        flights = []
        selected_times = random.sample(self.departure_times, min(num_flights, len(self.departure_times)))
        
        for i, departure_time in enumerate(selected_times):
            departure_dt = datetime.combine(date.date(), departure_time)
            duration = self.calculate_flight_duration(origin_code, dest_code)
            arrival_dt = departure_dt + duration
            
            # Generate flight number (max 8 characters)
            flight_num = random.randint(100, 999)  # 3-digit number
            flight_number = f"{airline_code}{flight_num}"
            
            # Ensure flight number is within 8 character limit
            if len(flight_number) > 8:
                # Truncate airline code if needed
                max_airline_len = 8 - len(str(flight_num))
                airline_code_short = airline_code[:max_airline_len]
                flight_number = f"{airline_code_short}{flight_num}"
            
            flight = Flight(
                flightno=flight_number,
                from_airport=airport_ids[origin_code],
                to_airport=airport_ids[dest_code],
                departure=departure_dt,
                arrival=arrival_dt,
                airline_id=airline_ids[airline_code],
                airplane_id=aircraft_id
            )
            
            flights.append(flight)
        
        return flights
    
    def populate_flights(self, start_date: datetime, end_date: datetime, 
                        max_routes_per_day: int = 100) -> int:
        """Populate flights for date range"""
        
        if not DEPENDENCIES_AVAILABLE:
            print("Dependencies not available")
            return 0
        
        print(f"Populating flights from {start_date.date()} to {end_date.date()}")
        
        with Session(self.db_manager.engine) as session:
            # Get required data
            print("Loading reference data...")
            route_counts = self.get_route_counts_by_airport(session)
            routes = self.get_sample_routes(session, max_routes_per_day)
            airport_ids = self.get_airport_ids(session)
            airline_ids = self.get_airline_ids(session)
            aircraft_id = self.get_random_aircraft(session)
            
            if not aircraft_id:
                print("❌ No aircraft found in database")
                return 0
            
            print(f"Processing {len(routes)} routes")
            print(f"Found {len(airport_ids)} airports with IATA codes")
            print(f"Found {len(airline_ids)} airlines with IATA codes")
            
            total_flights = 0
            current_date = start_date
            
            while current_date <= end_date:
                daily_flights = []
                
                # Process subset of routes each day
                daily_routes = random.sample(routes, min(max_routes_per_day, len(routes)))
                
                for route in daily_routes:
                    route_flights = self.generate_flights_for_route(
                        route, current_date, route_counts, airport_ids, 
                        airline_ids, aircraft_id
                    )
                    daily_flights.extend(route_flights)
                
                # Insert daily flights
                if daily_flights:
                    session.add_all(daily_flights)
                    session.commit()
                    total_flights += len(daily_flights)
                
                if current_date.day == 1:  # Progress update monthly
                    print(f"Processed {current_date.strftime('%Y-%m')}: {total_flights:,} flights so far")
                
                current_date += timedelta(days=1)
            
            print(f"✅ Created {total_flights:,} flights")
            return total_flights


def main():
    """Main function"""
    if not DEPENDENCIES_AVAILABLE:
        return 1
    
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return 1
    
    load_dotenv()
    
    print("Simple Flight Population Script")
    print("=" * 35)
    
    # Initialize
    db_manager = DatabaseManager()
    populator = SimpleFlightPopulator(db_manager)
    
    # Define date range
    today = datetime.now()
    start_date = datetime(today.year - 1, 1, 1)  # Last year
    end_date = datetime(today.year + 1, 12, 31)  # Next year
    
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    
    # Confirmation
    response = input("\nGenerate flights for 2-year period? This may take several minutes. (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return 0
    
    try:
        flights_created = populator.populate_flights(start_date, end_date)
        
        if flights_created > 0:
            print(f"\n🎉 Successfully created {flights_created:,} flights!")
        else:
            print("\n⚠ No flights were created. Check your data.")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())