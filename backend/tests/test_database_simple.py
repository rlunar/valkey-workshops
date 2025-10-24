"""
Simplified database tests focusing on core functionality.

This test suite validates the essential database functionality
without complex test isolation issues.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from airport.database.models import (
    Base, Airport, Airline, Flight, Passenger, Booking
)
from airport.database.config import DatabaseConfig


class TestDatabaseCore:
    """Core database functionality tests."""
    
    def test_model_creation_and_relationships(self):
        """Test creating models and their relationships."""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create airport
            airport = Airport(iata="TST", icao="KTST", name="Test Airport")
            session.add(airport)
            session.flush()
            
            # Create airline
            airline = Airline(
                iata="TS", 
                airlinename="Test Airlines", 
                base_airport=airport.airport_id
            )
            session.add(airline)
            session.flush()
            
            # Create flight
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
            
            # Create passenger
            passenger = Passenger(
                passportno="TEST123",
                firstname="Test",
                lastname="User"
            )
            session.add(passenger)
            session.flush()
            
            # Create booking
            booking = Booking(
                flight_id=flight.flight_id,
                seat="1A",
                passenger_id=passenger.passenger_id,
                price=Decimal("100.00")
            )
            session.add(booking)
            session.commit()
            
            # Test relationships
            assert flight.departure_airport.iata == "TST"
            assert flight.airline.iata == "TS"
            assert booking.flight.flightno == "TS001"
            assert booking.passenger.firstname == "Test"
            assert len(flight.bookings) == 1
            assert len(passenger.bookings) == 1
            
        finally:
            session.close()
    
    def test_database_config_basic(self):
        """Test basic database configuration functionality."""
        config = DatabaseConfig()
        
        # Test configuration properties
        assert config.db_type == 'sqlite'
        assert 'sqlite:///' in config.database_url
        assert not config._is_initialized
        
        # Test initialization
        config.initialize()
        assert config._is_initialized
        assert config.engine is not None
        assert config.SessionLocal is not None
        
        # Test connection
        assert config.test_connection() is True
        
        # Test session creation
        session = config.get_session()
        assert session is not None
        session.close()
        
        # Clean up
        config.close()
    
    def test_database_config_with_tables(self):
        """Test database configuration with table creation."""
        config = DatabaseConfig()
        config.create_tables()
        
        # Test that we can create and query data
        with config.get_session_context() as session:
            airport = Airport(iata="CFG", icao="KCFG", name="Config Test Airport")
            session.add(airport)
        
        # Verify data was saved
        with config.get_session_context() as session:
            result = session.query(Airport).filter_by(iata="CFG").first()
            assert result is not None
            assert result.name == "Config Test Airport"
        
        config.close()
    
    def test_model_constraints(self):
        """Test model constraints and validation."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Test unique constraints work
            airport1 = Airport(iata="DUP", icao="KDUP", name="Airport 1")
            airport2 = Airport(iata="DIF", icao="KDUP", name="Airport 2")  # Same ICAO
            
            session.add(airport1)
            session.commit()
            
            session.add(airport2)
            # This should fail due to unique ICAO constraint
            with pytest.raises(Exception):  # Could be IntegrityError or similar
                session.commit()
                
        except Exception:
            session.rollback()
        finally:
            session.close()
    
    def test_query_patterns(self):
        """Test common query patterns used in the workshop."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Create test data
            airports = [
                Airport(iata="LAX", icao="KLAX", name="Los Angeles"),
                Airport(iata="SFO", icao="KSFO", name="San Francisco"),
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
            
            flights = []
            for i in range(5):
                flight = Flight(
                    flightno=f"AA{100+i}",
                    from_airport=airports[0].airport_id,
                    to_airport=airports[1].airport_id,
                    departure=datetime(2024, 1, 15+i, 10, 0),
                    arrival=datetime(2024, 1, 15+i, 12, 0),
                    airline_id=airline.airline_id,
                    airplane_id=1000+i
                )
                flights.append(flight)
            session.add_all(flights)
            session.commit()
            
            # Test query patterns
            
            # 1. Find flights by route
            route_flights = session.query(Flight).filter(
                Flight.from_airport == airports[0].airport_id,
                Flight.to_airport == airports[1].airport_id
            ).all()
            assert len(route_flights) == 5
            
            # 2. Find flights by airline
            airline_flights = session.query(Flight).filter(
                Flight.airline_id == airline.airline_id
            ).all()
            assert len(airline_flights) == 5
            
            # 3. Find airport by IATA
            lax = session.query(Airport).filter(Airport.iata == "LAX").first()
            assert lax is not None
            assert lax.name == "Los Angeles"
            
            # 4. Join queries
            flight_with_airports = session.query(Flight, Airport).join(
                Airport, Flight.from_airport == Airport.airport_id
            ).filter(Airport.iata == "LAX").all()
            assert len(flight_with_airports) == 5
            
        finally:
            session.close()


class TestDatabaseUtilities:
    """Test database utility functions."""
    
    def test_table_creation_utilities(self):
        """Test table creation and dropping utilities."""
        from airport.database.models import create_all_tables, drop_all_tables
        
        engine = create_engine("sqlite:///:memory:")
        
        # Test table creation
        create_all_tables(engine)
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            
        expected_tables = {'airport', 'airline', 'flight', 'passenger', 'booking'}
        assert expected_tables.issubset(set(tables))
        
        # Test table dropping
        drop_all_tables(engine)
        
        # Verify tables are gone
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            
        assert not expected_tables.issubset(set(tables))
        
        engine.dispose()
    
    def test_model_string_representations(self):
        """Test model __repr__ methods."""
        airport = Airport(airport_id=1, iata="TST", icao="KTST", name="Test Airport")
        airline = Airline(airline_id=1, iata="TS", airlinename="Test Airlines")
        passenger = Passenger(passenger_id=1, passportno="123", firstname="John", lastname="Doe")
        
        # Test that repr methods work and contain expected information
        assert "Airport" in repr(airport)
        assert "TST" in repr(airport)
        
        assert "Airline" in repr(airline)
        assert "TS" in repr(airline)
        
        assert "Passenger" in repr(passenger)
        assert "John Doe" in repr(passenger)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])