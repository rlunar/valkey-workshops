"""
Integration tests for database models and configuration.

Tests the complete database setup including model creation,
relationships, and configuration working together.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from airport.database.config import DatabaseConfig
from airport.database.models import Airport, Airline, Flight, Passenger, Booking


@pytest.fixture
def db_config():
    """Create a test database configuration."""
    config = DatabaseConfig(database_url="sqlite:///:memory:")
    config.create_tables()
    yield config
    config.close()


@pytest.fixture
def session(db_config):
    """Create a database session for testing."""
    with db_config.get_session_context() as session:
        yield session


class TestDatabaseIntegration:
    """Integration tests for the complete database system."""
    
    def test_complete_flight_booking_workflow(self, session):
        """Test a complete flight booking workflow."""
        # Create airports
        lax = Airport(iata="LAX", icao="KLAX", name="Los Angeles International")
        sfo = Airport(iata="SFO", icao="KSFO", name="San Francisco International")
        session.add_all([lax, sfo])
        session.flush()  # Get IDs without committing
        
        # Create airline
        airline = Airline(
            iata="AA",
            airlinename="American Airlines",
            base_airport=lax.airport_id
        )
        session.add(airline)
        session.flush()
        
        # Create flight
        flight = Flight(
            flightno="AA1234",
            from_airport=lax.airport_id,
            to_airport=sfo.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 12, 45),
            airline_id=airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.flush()
        
        # Create passengers
        passenger1 = Passenger(
            passportno="123456789",
            firstname="John",
            lastname="Doe"
        )
        passenger2 = Passenger(
            passportno="987654321",
            firstname="Jane",
            lastname="Smith"
        )
        session.add_all([passenger1, passenger2])
        session.flush()
        
        # Create bookings
        booking1 = Booking(
            flight_id=flight.flight_id,
            seat="12A",
            passenger_id=passenger1.passenger_id,
            price=Decimal("299.99")
        )
        booking2 = Booking(
            flight_id=flight.flight_id,
            seat="12B",
            passenger_id=passenger2.passenger_id,
            price=Decimal("299.99")
        )
        session.add_all([booking1, booking2])
        
        # Commit all changes
        session.commit()
        
        # Verify relationships work correctly
        assert len(flight.bookings) == 2
        assert len(passenger1.bookings) == 1
        assert len(passenger2.bookings) == 1
        assert flight.departure_airport.iata == "LAX"
        assert flight.arrival_airport.iata == "SFO"
        assert flight.airline.iata == "AA"
        assert airline.base_airport_obj.iata == "LAX"
    
    def test_query_optimization_indexes(self, session):
        """Test that indexes support common query patterns."""
        # Create test data
        airports = [
            Airport(iata="LAX", icao="KLAX", name="Los Angeles International"),
            Airport(iata="SFO", icao="KSFO", name="San Francisco International"),
            Airport(iata="JFK", icao="KJFK", name="John F. Kennedy International"),
        ]
        session.add_all(airports)
        session.flush()
        
        airline = Airline(
            iata="AA",
            airlinename="American Airlines",
            base_airport=airports[0].airport_id
        )
        session.add(airline)
        session.flush()
        
        # Create multiple flights for testing
        flights = []
        for i in range(10):
            flight = Flight(
                flightno=f"AA{1000 + i}",
                from_airport=airports[i % 2].airport_id,
                to_airport=airports[(i + 1) % 2].airport_id,
                departure=datetime(2024, 1, 15 + i, 10, 30),
                arrival=datetime(2024, 1, 15 + i, 12, 45),
                airline_id=airline.airline_id,
                airplane_id=12345 + i
            )
            flights.append(flight)
        session.add_all(flights)
        session.commit()
        
        # Test common query patterns that should benefit from indexes
        
        # 1. Search flights by route and date
        route_flights = session.query(Flight).filter(
            Flight.from_airport == airports[0].airport_id,
            Flight.to_airport == airports[1].airport_id,
            Flight.departure >= datetime(2024, 1, 15),
            Flight.departure < datetime(2024, 1, 20)
        ).all()
        assert len(route_flights) > 0
        
        # 2. Search flights by airline and date
        airline_flights = session.query(Flight).filter(
            Flight.airline_id == airline.airline_id,
            Flight.departure >= datetime(2024, 1, 15)
        ).all()
        assert len(airline_flights) == 10
        
        # 3. Search airports by IATA code
        airport = session.query(Airport).filter(Airport.iata == "LAX").first()
        assert airport is not None
        assert airport.name == "Los Angeles International"
        
        # 4. Search airports by name
        airport = session.query(Airport).filter(
            Airport.name.like("%Los Angeles%")
        ).first()
        assert airport is not None
    
    def test_foreign_key_constraints(self, session):
        """Test that foreign key constraints work with valid data."""
        # Create valid airport and airline first
        airport = Airport(iata="TST", icao="KTST", name="Test Airport")
        session.add(airport)
        session.flush()
        
        airline = Airline(iata="TS", airlinename="Test Airlines", base_airport=airport.airport_id)
        session.add(airline)
        session.flush()
        
        # Create flight with valid references
        flight = Flight(
            flightno="TS001",
            from_airport=airport.airport_id,
            to_airport=airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 12, 45),
            airline_id=airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.commit()
        
        # Verify the flight was created successfully
        assert flight.flight_id is not None
        assert flight.departure_airport.airport_id == airport.airport_id
        assert flight.airline.airline_id == airline.airline_id
    
    def test_cascade_operations(self, session):
        """Test cascade operations and relationship integrity."""
        # Create a complete booking scenario
        airport = Airport(iata="TST", icao="KTST", name="Test Airport")
        session.add(airport)
        session.flush()
        
        airline = Airline(
            iata="TS",
            airlinename="Test Airlines",
            base_airport=airport.airport_id
        )
        session.add(airline)
        session.flush()
        
        flight = Flight(
            flightno="TS001",
            from_airport=airport.airport_id,
            to_airport=airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 12, 45),
            airline_id=airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.flush()
        
        passenger = Passenger(
            passportno="TEST12345",
            firstname="Test",
            lastname="User"
        )
        session.add(passenger)
        session.flush()
        
        booking = Booking(
            flight_id=flight.flight_id,
            seat="1A",
            passenger_id=passenger.passenger_id,
            price=Decimal("100.00")
        )
        session.add(booking)
        session.commit()
        
        # Verify all relationships are established
        assert booking in flight.bookings
        assert booking in passenger.bookings
        assert flight in airline.flights
        assert airline in airport.based_airlines
    
    def test_data_types_and_constraints(self, session):
        """Test that data types and constraints work correctly."""
        # Test decimal precision for booking prices
        airport = Airport(iata="TST", icao="KTST", name="Test Airport")
        session.add(airport)
        session.flush()
        
        airline = Airline(iata="TS", airlinename="Test Airlines", base_airport=airport.airport_id)
        session.add(airline)
        session.flush()
        
        flight = Flight(
            flightno="TS001",
            from_airport=airport.airport_id,
            to_airport=airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 12, 45),
            airline_id=airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.flush()
        
        passenger = Passenger(passportno="TEST12345", firstname="Test", lastname="User")
        session.add(passenger)
        session.flush()
        
        # Test precise decimal values
        booking = Booking(
            flight_id=flight.flight_id,
            seat="1A",
            passenger_id=passenger.passenger_id,
            price=Decimal("1234.56")  # Test precision
        )
        session.add(booking)
        session.commit()
        
        # Retrieve and verify precision is maintained
        retrieved_booking = session.query(Booking).filter_by(booking_id=booking.booking_id).first()
        assert retrieved_booking.price == Decimal("1234.56")
    
    def test_session_context_manager_integration(self, db_config):
        """Test session context manager with model operations."""
        # Test successful transaction
        with db_config.get_session_context() as session:
            airport = Airport(iata="CTX", icao="KCTX", name="Context Test Airport")
            session.add(airport)
            # Automatic commit on context exit
        
        # Verify data persisted
        with db_config.get_session_context() as session:
            result = session.query(Airport).filter_by(iata="CTX").first()
            assert result is not None
            assert result.name == "Context Test Airport"
        
        # Test rollback on exception
        with pytest.raises(ValueError):
            with db_config.get_session_context() as session:
                airport = Airport(iata="ERR", icao="KERR", name="Error Test Airport")
                session.add(airport)
                raise ValueError("Test error")
        
        # Verify data was not persisted
        with db_config.get_session_context() as session:
            result = session.query(Airport).filter_by(iata="ERR").first()
            assert result is None
    
    def test_multiple_database_operations(self, session):
        """Test complex multi-table operations."""
        # Create a realistic scenario with multiple related records
        
        # Airports
        airports = [
            Airport(iata="NYC", icao="KJFK", name="John F. Kennedy International"),
            Airport(iata="LAX", icao="KLAX", name="Los Angeles International"),
            Airport(iata="CHI", icao="KORD", name="O'Hare International"),
        ]
        session.add_all(airports)
        session.flush()
        
        # Airlines
        airlines = [
            Airline(iata="AA", airlinename="American Airlines", base_airport=airports[0].airport_id),
            Airline(iata="DL", airlinename="Delta Air Lines", base_airport=airports[1].airport_id),
        ]
        session.add_all(airlines)
        session.flush()
        
        # Flights
        flights = [
            Flight(
                flightno="AA100",
                from_airport=airports[0].airport_id,
                to_airport=airports[1].airport_id,
                departure=datetime(2024, 1, 15, 8, 0),
                arrival=datetime(2024, 1, 15, 11, 30),
                airline_id=airlines[0].airline_id,
                airplane_id=1001
            ),
            Flight(
                flightno="DL200",
                from_airport=airports[1].airport_id,
                to_airport=airports[2].airport_id,
                departure=datetime(2024, 1, 15, 14, 0),
                arrival=datetime(2024, 1, 15, 17, 0),
                airline_id=airlines[1].airline_id,
                airplane_id=2001
            ),
        ]
        session.add_all(flights)
        session.flush()
        
        # Passengers
        passengers = [
            Passenger(passportno="P001", firstname="Alice", lastname="Johnson"),
            Passenger(passportno="P002", firstname="Bob", lastname="Wilson"),
            Passenger(passportno="P003", firstname="Carol", lastname="Davis"),
        ]
        session.add_all(passengers)
        session.flush()
        
        # Bookings
        bookings = [
            Booking(flight_id=flights[0].flight_id, seat="1A", passenger_id=passengers[0].passenger_id, price=Decimal("450.00")),
            Booking(flight_id=flights[0].flight_id, seat="1B", passenger_id=passengers[1].passenger_id, price=Decimal("450.00")),
            Booking(flight_id=flights[1].flight_id, seat="2A", passenger_id=passengers[0].passenger_id, price=Decimal("320.00")),
            Booking(flight_id=flights[1].flight_id, seat="2B", passenger_id=passengers[2].passenger_id, price=Decimal("320.00")),
        ]
        session.add_all(bookings)
        session.commit()
        
        # Complex queries to verify everything works
        
        # Find all flights from JFK
        jfk_flights = session.query(Flight).join(Airport, Flight.from_airport == Airport.airport_id).filter(Airport.iata == "NYC").all()
        assert len(jfk_flights) == 1
        assert jfk_flights[0].flightno == "AA100"
        
        # Find all bookings for Alice
        alice_bookings = session.query(Booking).join(Passenger).filter(Passenger.firstname == "Alice").all()
        assert len(alice_bookings) == 2
        
        # Find total revenue for American Airlines
        aa_revenue = session.query(Booking).join(Flight).join(Airline).filter(Airline.iata == "AA").all()
        total_revenue = sum(booking.price for booking in aa_revenue)
        assert total_revenue == Decimal("900.00")
        
        # Verify relationship navigation
        assert len(flights[0].bookings) == 2
        assert len(passengers[0].bookings) == 2
        assert airlines[0].base_airport_obj.iata == "NYC"