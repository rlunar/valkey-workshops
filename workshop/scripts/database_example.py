"""
Example usage of the Flughafen DB SQLModel classes

This file demonstrates various query patterns for the normalized airport schema,
where airport data is split between Airport (core data) and AirportGeo (geographic data).

Available example functions:

1. example_queries() - Original examples with basic Airport, Flight, and Booking queries
2. normalized_schema_examples() - Comprehensive examples for Airport/AirportGeo joins:
   - Basic joins between Airport and AirportGeo
   - Geographic filtering (country, coordinates, altitude)
   - Timezone-based queries
   - Handling missing geographic data
   
3. advanced_flight_queries() - Complex multi-table joins with proper aliasing:
   - International flights between countries
   - Distance-based flight analysis concepts
   - Timezone-aware flight scheduling
   
4. query_best_practices() - Best practices guide for normalized schema:
   - Proper join usage (INNER vs LEFT JOIN)
   - Index optimization tips
   - Query patterns and performance considerations
   
5. demonstrate_common_use_cases() - Real-world use cases:
   - Airport search by code or name
   - Regional airport listings
   - Flight route planning considerations

To run examples:
1. Ensure your .env file is configured with database connection details
2. Uncomment the desired function call at the bottom of this file
3. Run: python scripts/database_example.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlmodel import Session, select, and_, or_
    from models import Airport, AirportGeo, Airline, Flight, Passenger, Booking
    from models.database import DatabaseManager
    from dotenv import load_dotenv
    from decimal import Decimal
    SQLMODEL_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    SQLMODEL_AVAILABLE = False

# Load environment variables
if SQLMODEL_AVAILABLE:
    load_dotenv()

def example_queries():
    """Example queries using the SQLModel classes"""
    
    try:
        # Use environment variables for database connection
        db_manager = DatabaseManager()
        print(f"Connected to database successfully!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Make sure your .env file is configured correctly")
        return
    
    with Session(db_manager.engine) as session:
        
        # Get all airports
        airports = session.exec(select(Airport)).all()
        print(f"Found {len(airports)} airports")
        
        # Get flights from a specific airport
        vienna_airport = session.exec(
            select(Airport).where(Airport.iata == "VIE")
        ).first()
        
        if vienna_airport:
            flights_from_vienna = session.exec(
                select(Flight).where(Flight.from_airport == vienna_airport.airport_id)
            ).all()
            print(f"Flights from Vienna: {len(flights_from_vienna)}")
        
        # Get airline information
        airlines = session.exec(select(Airline)).all()
        for airline in airlines[:5]:  # First 5 airlines
            print(f"Airline: {airline.airlinename} ({airline.iata})")
        
        # Complex query: Get bookings with passenger and flight info
        bookings_query = (
            select(Booking, Passenger, Flight)
            .join(Passenger, Booking.passenger_id == Passenger.passenger_id)
            .join(Flight, Booking.flight_id == Flight.flight_id)
            .limit(10)
        )
        
        results = session.exec(bookings_query).all()
        for booking, passenger, flight in results:
            print(f"Booking: {passenger.firstname} {passenger.lastname} "
                  f"on flight {flight.flightno} - Seat: {booking.seat}")


def normalized_schema_examples():
    """
    Examples demonstrating the normalized Airport/AirportGeo schema.
    Shows best practices for querying the separated airport data.
    """
    
    try:
        db_manager = DatabaseManager()
        print(f"Connected to database for normalized schema examples!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return
    
    with Session(db_manager.engine) as session:
        
        print("\n" + "="*60)
        print("NORMALIZED AIRPORT SCHEMA EXAMPLES")
        print("="*60)
        
        # Example 1: Basic Airport + AirportGeo Join
        print("\n1. Basic Airport with Geographic Data Join:")
        print("-" * 45)
        
        airport_with_geo_query = (
            select(Airport, AirportGeo)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
            .limit(5)
        )
        
        results = session.exec(airport_with_geo_query).all()
        for airport, geo in results:
            print(f"  {airport.name} ({airport.iata}/{airport.icao})")
            print(f"    Location: {geo.city}, {geo.country}")
            print(f"    Coordinates: {geo.latitude}, {geo.longitude}")
            print(f"    Altitude: {geo.altitude} ft")
            print()
        
        # Example 2: Geographic-based Filtering
        print("\n2. Geographic-based Filtering:")
        print("-" * 35)
        
        # Find airports in a specific country
        country_query = (
            select(Airport, AirportGeo)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
            .where(AirportGeo.country == "Austria")
            .limit(10)
        )
        
        austrian_airports = session.exec(country_query).all()
        print(f"  Found {len(austrian_airports)} airports in Austria:")
        for airport, geo in austrian_airports:
            print(f"    {airport.name} ({airport.iata}) - {geo.city}")
        
        # Example 3: Coordinate-based Proximity Search
        print("\n3. Coordinate-based Proximity Search:")
        print("-" * 40)
        
        # Find airports near Vienna (48.2082, 16.3738) within ~1 degree
        vienna_lat, vienna_lon = Decimal('48.2082'), Decimal('16.3738')
        proximity_query = (
            select(Airport, AirportGeo)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
            .where(
                and_(
                    AirportGeo.latitude.between(vienna_lat - 1, vienna_lat + 1),
                    AirportGeo.longitude.between(vienna_lon - 1, vienna_lon + 1)
                )
            )
        )
        
        nearby_airports = session.exec(proximity_query).all()
        print(f"  Found {len(nearby_airports)} airports near Vienna:")
        for airport, geo in nearby_airports:
            print(f"    {airport.name} ({airport.iata}) - {geo.city}")
        
        # Example 4: Altitude-based Filtering
        print("\n4. High-altitude Airports (>5000 ft):")
        print("-" * 35)
        
        high_altitude_query = (
            select(Airport, AirportGeo)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
            .where(AirportGeo.altitude > 5000)
            .order_by(AirportGeo.altitude.desc())
            .limit(5)
        )
        
        high_airports = session.exec(high_altitude_query).all()
        for airport, geo in high_airports:
            print(f"    {airport.name} ({airport.iata}) - {geo.altitude} ft")
        
        # Example 5: Timezone-based Queries
        print("\n5. Airports by Timezone:")
        print("-" * 25)
        
        timezone_query = (
            select(Airport, AirportGeo)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
            .where(AirportGeo.timezone_name.like('%Europe%'))
            .limit(5)
        )
        
        european_tz_airports = session.exec(timezone_query).all()
        for airport, geo in european_tz_airports:
            print(f"    {airport.name} - {geo.timezone_name} (UTC{geo.timezone_offset:+})")
        
        # Example 6: Left Join for Airports without Geographic Data
        print("\n6. Airports with Missing Geographic Data:")
        print("-" * 42)
        
        missing_geo_query = (
            select(Airport, AirportGeo)
            .outerjoin(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
            .where(AirportGeo.airport_id.is_(None))
            .limit(5)
        )
        
        airports_no_geo = session.exec(missing_geo_query).all()
        print(f"    Found {len(airports_no_geo)} airports without geographic data")
        for airport, geo in airports_no_geo:
            print(f"    {airport.name} ({airport.icao}) - No geographic data")
        
        # Example 7: Complex Multi-table Join with Flights
        print("\n7. Flights Between Countries:")
        print("-" * 30)
        
        international_flights_query = (
            select(Flight, Airport, AirportGeo, Airport, AirportGeo)
            .join(Airport, Flight.from_airport == Airport.airport_id, isouter=False)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id, isouter=False)
            .join(Airport, Flight.to_airport == Airport.airport_id, isouter=False)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id, isouter=False)
            .where(
                and_(
                    AirportGeo.country != AirportGeo.country,  # Different countries
                    Flight.flightno.is_not(None)
                )
            )
            .limit(3)
        )
        
        # Note: This is a complex query that would need proper aliasing in practice
        # For demonstration purposes, showing the concept
        print("    Complex international flight queries require table aliases")
        print("    (See advanced_flight_queries() for proper implementation)")


def advanced_flight_queries():
    """
    Advanced examples showing proper table aliasing for complex joins
    involving multiple instances of the same tables.
    """
    
    try:
        db_manager = DatabaseManager()
    except Exception as e:
        print(f"Database connection failed: {e}")
        return
    
    with Session(db_manager.engine) as session:
        
        print("\n" + "="*60)
        print("ADVANCED QUERIES WITH TABLE ALIASES")
        print("="*60)
        
        # Create aliases for multiple uses of the same tables
        from sqlalchemy import alias
        
        # Aliases for departure airport and geo data
        dep_airport = alias(Airport.__table__, name='dep_airport')
        dep_geo = alias(AirportGeo.__table__, name='dep_geo')
        
        # Aliases for arrival airport and geo data
        arr_airport = alias(Airport.__table__, name='arr_airport')
        arr_geo = alias(AirportGeo.__table__, name='arr_geo')
        
        print("\n1. International Flights with Geographic Context:")
        print("-" * 48)
        
        # This would be the proper way to do complex multi-table joins
        # Note: SQLModel makes this more complex, so showing the concept
        print("    Example concept: Find flights between different countries")
        print("    FROM flight f")
        print("    JOIN airport dep_a ON f.from_airport = dep_a.airport_id")
        print("    JOIN airport_geo dep_g ON dep_a.airport_id = dep_g.airport_id")
        print("    JOIN airport arr_a ON f.to_airport = arr_a.airport_id")
        print("    JOIN airport_geo arr_g ON arr_a.airport_id = arr_g.airport_id")
        print("    WHERE dep_g.country != arr_g.country")
        
        print("\n2. Distance-based Flight Analysis:")
        print("-" * 35)
        print("    Calculate flight distances using geographic coordinates")
        print("    Useful for route optimization and fuel calculations")
        
        print("\n3. Timezone-aware Flight Scheduling:")
        print("-" * 38)
        print("    Consider departure/arrival timezones for scheduling")
        print("    Account for daylight saving time differences")


def query_best_practices():
    """
    Demonstrates best practices for querying the normalized schema.
    """
    
    print("\n" + "="*60)
    print("BEST PRACTICES FOR NORMALIZED SCHEMA QUERIES")
    print("="*60)
    
    print("\n1. Always Use Proper Joins:")
    print("-" * 30)
    print("   ✓ INNER JOIN when you need both airport and geographic data")
    print("   ✓ LEFT JOIN when geographic data might be missing")
    print("   ✓ Consider performance implications of joins")
    
    print("\n2. Index Usage:")
    print("-" * 15)
    print("   ✓ Use indexed fields for WHERE clauses (iata, icao, name)")
    print("   ✓ Foreign key joins are automatically optimized")
    print("   ✓ Consider adding indexes on frequently queried geo fields")
    
    print("\n3. Query Patterns:")
    print("-" * 17)
    print("   ✓ Filter on Airport table first, then join AirportGeo")
    print("   ✓ Use specific field selection to reduce data transfer")
    print("   ✓ Batch queries when possible to reduce round trips")
    
    print("\n4. Error Handling:")
    print("-" * 17)
    print("   ✓ Handle cases where geographic data might be NULL")
    print("   ✓ Validate coordinate ranges before using in calculations")
    print("   ✓ Consider timezone conversion for time-based queries")
    
    print("\n5. Performance Tips:")
    print("-" * 18)
    print("   ✓ Use LIMIT for large result sets")
    print("   ✓ Consider creating views for common join patterns")
    print("   ✓ Monitor query execution plans for optimization")


def demonstrate_common_use_cases():
    """
    Shows common real-world use cases for the normalized schema.
    """
    
    try:
        db_manager = DatabaseManager()
    except Exception as e:
        print(f"Database connection failed: {e}")
        return
    
    with Session(db_manager.engine) as session:
        
        print("\n" + "="*60)
        print("COMMON USE CASES")
        print("="*60)
        
        print("\n1. Airport Search by Code or Name:")
        print("-" * 35)
        
        # Search for airport by IATA code with location info
        search_code = "VIE"  # Vienna
        airport_search = (
            select(Airport, AirportGeo)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id, isouter=True)
            .where(
                or_(
                    Airport.iata == search_code,
                    Airport.icao == search_code,
                    Airport.name.contains(search_code)
                )
            )
        )
        
        results = session.exec(airport_search).all()
        for airport, geo in results:
            location = f"{geo.city}, {geo.country}" if geo else "Location unknown"
            print(f"    {airport.name} ({airport.iata}/{airport.icao}) - {location}")
        
        print("\n2. Regional Airport Listing:")
        print("-" * 28)
        
        # Get all airports in a region with their details
        region_query = (
            select(Airport, AirportGeo)
            .join(AirportGeo, Airport.airport_id == AirportGeo.airport_id)
            .where(AirportGeo.country.in_(["Austria", "Germany", "Switzerland"]))
            .order_by(AirportGeo.country, Airport.name)
            .limit(10)
        )
        
        regional_airports = session.exec(region_query).all()
        current_country = None
        for airport, geo in regional_airports:
            if geo.country != current_country:
                current_country = geo.country
                print(f"\n    {current_country}:")
            print(f"      {airport.name} ({airport.iata}) - {geo.city}")
        
        print("\n3. Flight Route Planning:")
        print("-" * 25)
        print("    Use geographic data for:")
        print("    • Distance calculations between airports")
        print("    • Fuel planning based on altitude differences")
        print("    • Timezone considerations for scheduling")
        print("    • Weather routing using geographic coordinates")


if __name__ == "__main__":
    print("Flughafen DB SQLModel Example")
    
    if not SQLMODEL_AVAILABLE:
        print("\nTo use this example:")
        print("1. Install dependencies: uv sync")
        print("2. Copy .env.example to .env and configure your database")
        print("3. Uncomment the example_queries() call")
        sys.exit(1)
    
    print("SQLModel successfully imported!")
    print("Models available:")
    print(f"- Airport: {Airport}")
    print(f"- AirportGeo: {AirportGeo}")
    print(f"- Airline: {Airline}")
    print(f"- Flight: {Flight}")
    print(f"- Passenger: {Passenger}")
    print(f"- Booking: {Booking}")
    
    print("\nTo run database queries:")
    print("1. Copy .env.example to .env and configure your database")
    print("2. Uncomment one of the example function calls below")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✓ .env file found")
    else:
        print("⚠ .env file not found - copy .env.example to .env and configure")
    
    print("\nAvailable example functions:")
    print("- example_queries()              # Original examples")
    print("- normalized_schema_examples()   # Normalized Airport/AirportGeo examples")
    print("- advanced_flight_queries()      # Complex multi-table joins")
    print("- query_best_practices()         # Best practices guide")
    print("- demonstrate_common_use_cases() # Real-world use cases")
    
    # Uncomment the examples you want to run:
    # example_queries()
    # normalized_schema_examples()
    # advanced_flight_queries()
    # query_best_practices()
    # demonstrate_common_use_cases()