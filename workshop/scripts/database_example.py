"""
Example usage of the Flughafen DB SQLModel classes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlmodel import Session, select
    from models import Airport, Airline, Flight, Passenger, Booking
    from models.database import DatabaseManager
    from dotenv import load_dotenv
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
    print(f"- Airline: {Airline}")
    print(f"- Flight: {Flight}")
    print(f"- Passenger: {Passenger}")
    print(f"- Booking: {Booking}")
    
    print("\nTo run database queries:")
    print("1. Copy .env.example to .env and configure your database")
    print("2. Uncomment the example_queries() call below")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✓ .env file found")
    else:
        print("⚠ .env file not found - copy .env.example to .env and configure")
    
    # example_queries()