"""
Test suite for SQLAlchemy database models.

Tests model creation, relationships, constraints, and basic functionality
for the airport workshop database models.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from airport.database.models import (
    Base,
    Airport,
    Airline,
    Flight,
    Passenger,
    Booking,
    create_all_tables,
    drop_all_tables,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    create_all_tables(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_airport(session):
    """Create a sample airport for testing."""
    airport = Airport(
        iata="LAX",
        icao="KLAX",
        name="Los Angeles International Airport"
    )
    session.add(airport)
    session.commit()
    return airport


@pytest.fixture
def sample_airline(session, sample_airport):
    """Create a sample airline for testing."""
    airline = Airline(
        iata="AA",
        airlinename="American Airlines",
        base_airport=sample_airport.airport_id
    )
    session.add(airline)
    session.commit()
    return airline


@pytest.fixture
def sample_passenger(session):
    """Create a sample passenger for testing."""
    passenger = Passenger(
        passportno="123456789",
        firstname="John",
        lastname="Doe"
    )
    session.add(passenger)
    session.commit()
    return passenger


class TestAirportModel:
    """Test cases for the Airport model."""
    
    def test_airport_creation(self, session):
        """Test basic airport creation."""
        airport = Airport(
            iata="JFK",
            icao="KJFK",
            name="John F. Kennedy International Airport"
        )
        session.add(airport)
        session.commit()
        
        assert airport.airport_id is not None
        assert airport.iata == "JFK"
        assert airport.icao == "KJFK"
        assert airport.name == "John F. Kennedy International Airport"
    
    def test_airport_unique_icao(self, session):
        """Test that ICAO codes must be unique."""
        airport1 = Airport(iata="JFK", icao="KJFK", name="Airport 1")
        airport2 = Airport(iata="LGA", icao="KJFK", name="Airport 2")
        
        session.add(airport1)
        session.commit()
        
        session.add(airport2)
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_airport_nullable_iata(self, session):
        """Test that IATA code can be null."""
        airport = Airport(
            iata=None,
            icao="KXXX",
            name="Test Airport"
        )
        session.add(airport)
        session.commit()
        
        assert airport.iata is None
        assert airport.icao == "KXXX"
    
    def test_airport_repr(self, sample_airport):
        """Test airport string representation."""
        repr_str = repr(sample_airport)
        assert "Airport" in repr_str
        assert "LAX" in repr_str
        assert "KLAX" in repr_str


class TestAirlineModel:
    """Test cases for the Airline model."""
    
    def test_airline_creation(self, session, sample_airport):
        """Test basic airline creation."""
        airline = Airline(
            iata="DL",
            airlinename="Delta Air Lines",
            base_airport=sample_airport.airport_id
        )
        session.add(airline)
        session.commit()
        
        assert airline.airline_id is not None
        assert airline.iata == "DL"
        assert airline.airlinename == "Delta Air Lines"
        assert airline.base_airport == sample_airport.airport_id
    
    def test_airline_unique_iata(self, session, sample_airport):
        """Test that airline IATA codes must be unique."""
        airline1 = Airline(iata="AA", airlinename="Airline 1", base_airport=sample_airport.airport_id)
        airline2 = Airline(iata="AA", airlinename="Airline 2", base_airport=sample_airport.airport_id)
        
        session.add(airline1)
        session.commit()
        
        session.add(airline2)
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_airline_base_airport_relationship(self, session, sample_airline, sample_airport):
        """Test airline-airport relationship."""
        assert sample_airline.base_airport_obj.airport_id == sample_airport.airport_id
        assert sample_airline in sample_airport.based_airlines
    
    def test_airline_repr(self, sample_airline):
        """Test airline string representation."""
        repr_str = repr(sample_airline)
        assert "Airline" in repr_str
        assert "AA" in repr_str


class TestFlightModel:
    """Test cases for the Flight model."""
    
    def test_flight_creation(self, session, sample_airport, sample_airline):
        """Test basic flight creation."""
        # Create destination airport
        dest_airport = Airport(iata="SFO", icao="KSFO", name="San Francisco International")
        session.add(dest_airport)
        session.commit()
        
        departure_time = datetime(2024, 1, 15, 10, 30)
        arrival_time = datetime(2024, 1, 15, 13, 45)
        
        flight = Flight(
            flightno="AA1234",
            from_airport=sample_airport.airport_id,
            to_airport=dest_airport.airport_id,
            departure=departure_time,
            arrival=arrival_time,
            airline_id=sample_airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.commit()
        
        assert flight.flight_id is not None
        assert flight.flightno == "AA1234"
        assert flight.from_airport == sample_airport.airport_id
        assert flight.to_airport == dest_airport.airport_id
        assert flight.departure == departure_time
        assert flight.arrival == arrival_time
    
    def test_flight_relationships(self, session, sample_airport, sample_airline):
        """Test flight relationships with airports and airlines."""
        dest_airport = Airport(iata="SFO", icao="KSFO", name="San Francisco International")
        session.add(dest_airport)
        session.commit()
        
        flight = Flight(
            flightno="AA1234",
            from_airport=sample_airport.airport_id,
            to_airport=dest_airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 13, 45),
            airline_id=sample_airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.commit()
        
        # Test relationships
        assert flight.departure_airport.airport_id == sample_airport.airport_id
        assert flight.arrival_airport.airport_id == dest_airport.airport_id
        assert flight.airline.airline_id == sample_airline.airline_id
        assert flight in sample_airport.departing_flights
        assert flight in dest_airport.arriving_flights
        assert flight in sample_airline.flights
    
    def test_flight_repr(self, session, sample_airport, sample_airline):
        """Test flight string representation."""
        dest_airport = Airport(iata="SFO", icao="KSFO", name="San Francisco International")
        session.add(dest_airport)
        session.commit()
        
        flight = Flight(
            flightno="AA1234",
            from_airport=sample_airport.airport_id,
            to_airport=dest_airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 13, 45),
            airline_id=sample_airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.commit()
        
        repr_str = repr(flight)
        assert "Flight" in repr_str
        assert "AA1234" in repr_str


class TestPassengerModel:
    """Test cases for the Passenger model."""
    
    def test_passenger_creation(self, session):
        """Test basic passenger creation."""
        passenger = Passenger(
            passportno="987654321",
            firstname="Jane",
            lastname="Smith"
        )
        session.add(passenger)
        session.commit()
        
        assert passenger.passenger_id is not None
        assert passenger.passportno == "987654321"
        assert passenger.firstname == "Jane"
        assert passenger.lastname == "Smith"
    
    def test_passenger_unique_passport(self, session):
        """Test that passport numbers must be unique."""
        passenger1 = Passenger(passportno="123456789", firstname="John", lastname="Doe")
        passenger2 = Passenger(passportno="123456789", firstname="Jane", lastname="Smith")
        
        session.add(passenger1)
        session.commit()
        
        session.add(passenger2)
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_passenger_repr(self, sample_passenger):
        """Test passenger string representation."""
        repr_str = repr(sample_passenger)
        assert "Passenger" in repr_str
        assert "123456789" in repr_str
        assert "John Doe" in repr_str


class TestBookingModel:
    """Test cases for the Booking model."""
    
    def test_booking_creation(self, session, sample_airport, sample_airline, sample_passenger):
        """Test basic booking creation."""
        # Create flight
        dest_airport = Airport(iata="SFO", icao="KSFO", name="San Francisco International")
        session.add(dest_airport)
        session.commit()
        
        flight = Flight(
            flightno="AA1234",
            from_airport=sample_airport.airport_id,
            to_airport=dest_airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 13, 45),
            airline_id=sample_airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.commit()
        
        # Create booking
        booking = Booking(
            flight_id=flight.flight_id,
            seat="12A",
            passenger_id=sample_passenger.passenger_id,
            price=Decimal("299.99")
        )
        session.add(booking)
        session.commit()
        
        assert booking.booking_id is not None
        assert booking.flight_id == flight.flight_id
        assert booking.seat == "12A"
        assert booking.passenger_id == sample_passenger.passenger_id
        assert booking.price == Decimal("299.99")
    
    def test_booking_relationships(self, session, sample_airport, sample_airline, sample_passenger):
        """Test booking relationships with flights and passengers."""
        # Create flight
        dest_airport = Airport(iata="SFO", icao="KSFO", name="San Francisco International")
        session.add(dest_airport)
        session.commit()
        
        flight = Flight(
            flightno="AA1234",
            from_airport=sample_airport.airport_id,
            to_airport=dest_airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 13, 45),
            airline_id=sample_airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.commit()
        
        booking = Booking(
            flight_id=flight.flight_id,
            seat="12A",
            passenger_id=sample_passenger.passenger_id,
            price=Decimal("299.99")
        )
        session.add(booking)
        session.commit()
        
        # Test relationships
        assert booking.flight.flight_id == flight.flight_id
        assert booking.passenger.passenger_id == sample_passenger.passenger_id
        assert booking in flight.bookings
        assert booking in sample_passenger.bookings
    
    def test_booking_unique_seat_per_flight(self, session, sample_airport, sample_airline, sample_passenger):
        """Test that seat assignments are unique per flight."""
        # Create flight
        dest_airport = Airport(iata="SFO", icao="KSFO", name="San Francisco International")
        session.add(dest_airport)
        session.commit()
        
        flight = Flight(
            flightno="AA1234",
            from_airport=sample_airport.airport_id,
            to_airport=dest_airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 13, 45),
            airline_id=sample_airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.commit()
        
        # Create another passenger
        passenger2 = Passenger(passportno="987654321", firstname="Jane", lastname="Smith")
        session.add(passenger2)
        session.commit()
        
        # Create first booking
        booking1 = Booking(
            flight_id=flight.flight_id,
            seat="12A",
            passenger_id=sample_passenger.passenger_id,
            price=Decimal("299.99")
        )
        session.add(booking1)
        session.commit()
        
        # Try to create second booking with same seat
        booking2 = Booking(
            flight_id=flight.flight_id,
            seat="12A",
            passenger_id=passenger2.passenger_id,
            price=Decimal("299.99")
        )
        session.add(booking2)
        with pytest.raises(IntegrityError):
            session.commit()
    
    def test_booking_repr(self, session, sample_airport, sample_airline, sample_passenger):
        """Test booking string representation."""
        # Create flight
        dest_airport = Airport(iata="SFO", icao="KSFO", name="San Francisco International")
        session.add(dest_airport)
        session.commit()
        
        flight = Flight(
            flightno="AA1234",
            from_airport=sample_airport.airport_id,
            to_airport=dest_airport.airport_id,
            departure=datetime(2024, 1, 15, 10, 30),
            arrival=datetime(2024, 1, 15, 13, 45),
            airline_id=sample_airline.airline_id,
            airplane_id=12345
        )
        session.add(flight)
        session.commit()
        
        booking = Booking(
            flight_id=flight.flight_id,
            seat="12A",
            passenger_id=sample_passenger.passenger_id,
            price=Decimal("299.99")
        )
        session.add(booking)
        session.commit()
        
        repr_str = repr(booking)
        assert "Booking" in repr_str
        assert "12A" in repr_str


class TestModelUtilities:
    """Test cases for model utility functions."""
    
    def test_create_all_tables(self):
        """Test table creation utility."""
        engine = create_engine("sqlite:///:memory:")
        create_all_tables(engine)
        
        # Check that tables exist
        inspector = engine.dialect.get_table_names(engine.connect())
        expected_tables = {'airport', 'airline', 'flight', 'passenger', 'booking'}
        actual_tables = set(inspector)
        
        assert expected_tables.issubset(actual_tables)
        engine.dispose()
    
    def test_drop_all_tables(self):
        """Test table dropping utility."""
        engine = create_engine("sqlite:///:memory:")
        create_all_tables(engine)
        drop_all_tables(engine)
        
        # Check that tables are dropped
        inspector = engine.dialect.get_table_names(engine.connect())
        expected_tables = {'airport', 'airline', 'flight', 'passenger', 'booking'}
        actual_tables = set(inspector)
        
        assert not expected_tables.issubset(actual_tables)
        engine.dispose()


class TestModelIndexes:
    """Test cases for model indexes and query optimization."""
    
    def test_airport_indexes(self, engine):
        """Test that airport indexes are created properly."""
        # This is a basic test - in a real scenario you'd inspect the database
        # to verify indexes exist
        inspector = engine.dialect.get_indexes(engine.connect(), 'airport')
        index_columns = [idx['column_names'] for idx in inspector]
        
        # Check for expected indexed columns
        assert any('iata' in cols for cols in index_columns)
        assert any('name' in cols for cols in index_columns)
    
    def test_flight_composite_indexes(self, engine):
        """Test that flight composite indexes are created."""
        # Basic test for composite indexes
        inspector = engine.dialect.get_indexes(engine.connect(), 'flight')
        
        # Should have indexes on departure, airline_id, etc.
        assert len(inspector) > 0  # At least some indexes should exist