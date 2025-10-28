#!/usr/bin/env python3
"""
Check current flight distribution to identify the JFK and hub distribution issues
"""

import os
import sys
from sqlmodel import Session, select, func

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from models.database import DatabaseManager
    from models.flight import Flight
    from models.airport import Airport
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def check_flight_distribution():
    """Check the current flight distribution"""
    
    if not DEPENDENCIES_AVAILABLE:
        return
    
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        return
    
    load_dotenv()
    
    # Initialize database
    db_manager = DatabaseManager()
    
    with Session(db_manager.engine) as session:
        # Check total flights
        total_flights_query = select(func.count(Flight.flight_id))
        total_flights = session.exec(total_flights_query).first()
        print(f"Total flights: {total_flights:,}")
        
        if total_flights == 0:
            print("No flights found in database. Run the population script first.")
            return
        
        # Check JFK flights (both departing and arriving)
        jfk_flights_query = select(func.count(Flight.flight_id)).select_from(
            Flight.__table__.join(Airport.__table__, Flight.from_airport == Airport.airport_id)
        ).where(Airport.iata == 'JFK')
        
        jfk_departing = session.exec(jfk_flights_query).first() or 0
        
        jfk_arriving_query = select(func.count(Flight.flight_id)).select_from(
            Flight.__table__.join(Airport.__table__, Flight.to_airport == Airport.airport_id)
        ).where(Airport.iata == 'JFK')
        
        jfk_arriving = session.exec(jfk_arriving_query).first() or 0
        
        print(f"JFK departing flights: {jfk_departing:,}")
        print(f"JFK arriving flights: {jfk_arriving:,}")
        print(f"Total JFK flights: {jfk_departing + jfk_arriving:,}")
        
        # Check top routes by flight count
        print("\nTop 10 routes by flight count:")
        top_routes_query = select(
            Airport.iata.label('from_airport'),
            Airport.iata.label('to_airport'), 
            func.count(Flight.flight_id).label('flight_count')
        ).select_from(
            Flight.__table__
            .join(Airport.__table__.alias('from_airport'), Flight.from_airport == Airport.airport_id)
            .join(Airport.__table__.alias('to_airport'), Flight.to_airport == Airport.airport_id)
        ).group_by(
            Flight.from_airport, Flight.to_airport
        ).order_by(
            func.count(Flight.flight_id).desc()
        ).limit(10)
        
        # This is complex with SQLModel, let's use a simpler approach
        # Get all flights with airport codes
        flights_with_airports = session.exec(
            select(
                Flight.flight_id,
                Airport.iata.label('from_iata')
            ).select_from(
                Flight.__table__.join(Airport.__table__, Flight.from_airport == Airport.airport_id)
            )
        ).all()
        
        # Let's try a different approach - check major hub distribution
        major_hubs = ['ATL', 'ORD', 'LHR', 'CDG', 'FRA', 'LAX', 'DFW', 'JFK', 'AMS']
        
        print("\nMajor hub flight distribution:")
        for hub in major_hubs:
            # Departing flights
            departing_query = select(func.count(Flight.flight_id)).select_from(
                Flight.__table__.join(Airport.__table__, Flight.from_airport == Airport.airport_id)
            ).where(Airport.iata == hub)
            
            departing_count = session.exec(departing_query).first() or 0
            
            # Arriving flights  
            arriving_query = select(func.count(Flight.flight_id)).select_from(
                Flight.__table__.join(Airport.__table__, Flight.to_airport == Airport.airport_id)
            ).where(Airport.iata == hub)
            
            arriving_count = session.exec(arriving_query).first() or 0
            
            total_hub_flights = departing_count + arriving_count
            print(f"  {hub}: {total_hub_flights:,} flights ({departing_count:,} departing, {arriving_count:,} arriving)")
        
        # Check if we can find the problematic DFW-ATL route concentration
        print("\nChecking specific route concentrations:")
        problem_routes = [('DFW', 'ATL'), ('ATL', 'DFW'), ('DFW', 'ORD'), ('ORD', 'DFW')]
        
        for from_code, to_code in problem_routes:
            route_query = select(func.count(Flight.flight_id)).select_from(
                Flight.__table__
                .join(Airport.__table__.alias('from_airport'), Flight.from_airport == Airport.airport_id)
                .join(Airport.__table__.alias('to_airport'), Flight.to_airport == Airport.airport_id)
            ).where(
                Airport.iata == from_code,
                Airport.iata == to_code
            )
            
            # This is getting complex with the joins, let's use a simpler raw query approach
            try:
                result = session.exec(select(func.count(Flight.flight_id)).where(
                    Flight.from_airport.in_(
                        select(Airport.airport_id).where(Airport.iata == from_code)
                    ),
                    Flight.to_airport.in_(
                        select(Airport.airport_id).where(Airport.iata == to_code)
                    )
                )).first()
                
                print(f"  {from_code} -> {to_code}: {result:,} flights")
            except Exception as e:
                print(f"  {from_code} -> {to_code}: Error querying - {e}")

if __name__ == "__main__":
    check_flight_distribution()