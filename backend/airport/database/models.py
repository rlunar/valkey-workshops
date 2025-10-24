"""
SQLAlchemy database models for the airport workshop system.

Based on the Flughafen DB by Stefan Pröll, Eva Zangerle, Wolfgang Gassler
licensed under CC BY 4.0. To view a copy of this license, 
visit https://creativecommons.org/licenses/by/4.0

This module defines the core database models used in the Valkey caching workshop:
- Airport: Airport information with IATA/ICAO codes
- Airline: Airline information with base airport relationships
- Flight: Flight schedules with departure/arrival times and relationships
- Passenger: Passenger information with passport details
- Booking: Flight bookings linking passengers to flights with seat assignments
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index, Numeric
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List

# Create the declarative base for all models
Base = declarative_base()


class Airport(Base):
    """
    Airport model representing airport information.
    
    This model stores basic airport data including IATA/ICAO codes and names.
    Used extensively in flight search queries and caching demonstrations.
    """
    __tablename__ = 'airport'
    
    # Primary key
    airport_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Airport codes and identification
    iata = Column(String(3), nullable=True, index=True)  # 3-letter IATA code (e.g., 'LAX')
    icao = Column(String(4), unique=True, nullable=False, index=True)  # 4-letter ICAO code (e.g., 'KLAX')
    name = Column(String(50), nullable=False, index=True)  # Airport name
    
    # Relationships - flights departing from and arriving at this airport
    departing_flights = relationship(
        "Flight", 
        foreign_keys="Flight.from_airport",
        back_populates="departure_airport",
        lazy="select"
    )
    arriving_flights = relationship(
        "Flight", 
        foreign_keys="Flight.to_airport", 
        back_populates="arrival_airport",
        lazy="select"
    )
    
    # Airlines with this as their base airport
    based_airlines = relationship("Airline", back_populates="base_airport_obj", lazy="select")
    
    def __repr__(self):
        return f"<Airport(id={self.airport_id}, iata='{self.iata}', icao='{self.icao}', name='{self.name}')>"


class Airline(Base):
    """
    Airline model representing airline information.
    
    Stores airline data including IATA codes and base airport relationships.
    Used in flight search and airline-specific caching patterns.
    """
    __tablename__ = 'airline'
    
    # Primary key
    airline_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Airline identification
    iata = Column(String(2), unique=True, nullable=False, index=True)  # 2-letter IATA code (e.g., 'AA')
    airlinename = Column(String(30), nullable=True)  # Full airline name
    base_airport = Column(Integer, ForeignKey('airport.airport_id'), nullable=False, index=True)
    
    # Relationships
    flights = relationship("Flight", back_populates="airline", lazy="select")
    base_airport_obj = relationship("Airport", back_populates="based_airlines", lazy="select")
    
    def __repr__(self):
        return f"<Airline(id={self.airline_id}, iata='{self.iata}', name='{self.airlinename}')>"


class Flight(Base):
    """
    Flight model representing scheduled flights.
    
    Core model for the workshop demonstrations, containing flight schedules
    and relationships to airports, airlines, and bookings. Used extensively
    in query optimization and caching pattern demonstrations.
    """
    __tablename__ = 'flight'
    
    # Primary key
    flight_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Flight identification and schedule
    flightno = Column(String(8), nullable=False, index=True)  # Flight number (e.g., 'AA1234')
    from_airport = Column(Integer, ForeignKey('airport.airport_id'), nullable=False, index=True)
    to_airport = Column(Integer, ForeignKey('airport.airport_id'), nullable=False, index=True)
    departure = Column(DateTime, nullable=False, index=True)  # Scheduled departure time
    arrival = Column(DateTime, nullable=False, index=True)    # Scheduled arrival time
    
    # Aircraft and airline information
    airline_id = Column(Integer, ForeignKey('airline.airline_id'), nullable=False, index=True)
    airplane_id = Column(Integer, nullable=False, index=True)  # Reference to airplane (simplified for workshop)
    
    # Relationships
    airline = relationship("Airline", back_populates="flights", lazy="select")
    departure_airport = relationship(
        "Airport", 
        foreign_keys=[from_airport], 
        back_populates="departing_flights",
        lazy="select"
    )
    arrival_airport = relationship(
        "Airport", 
        foreign_keys=[to_airport], 
        back_populates="arriving_flights",
        lazy="select"
    )
    bookings = relationship("Booking", back_populates="flight", lazy="select")
    
    def __repr__(self):
        return f"<Flight(id={self.flight_id}, flightno='{self.flightno}', from={self.from_airport}, to={self.to_airport})>"


class Passenger(Base):
    """
    Passenger model representing passenger information.
    
    Stores basic passenger data including passport information.
    Used in booking relationships and passenger manifest caching demonstrations.
    """
    __tablename__ = 'passenger'
    
    # Primary key
    passenger_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Passenger identification
    passportno = Column(String(9), unique=True, nullable=False, index=True)  # Passport number
    firstname = Column(String(100), nullable=False)  # First name
    lastname = Column(String(100), nullable=False)   # Last name
    
    # Relationships
    bookings = relationship("Booking", back_populates="passenger", lazy="select")
    
    def __repr__(self):
        return f"<Passenger(id={self.passenger_id}, passport='{self.passportno}', name='{self.firstname} {self.lastname}')>"


class Booking(Base):
    """
    Booking model representing flight bookings.
    
    Links passengers to flights with seat assignments and pricing information.
    Central to seat reservation demonstrations and booking-related caching patterns.
    """
    __tablename__ = 'booking'
    
    # Primary key
    booking_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Booking details
    flight_id = Column(Integer, ForeignKey('flight.flight_id'), nullable=False, index=True)
    seat = Column(String(4), nullable=True)  # Seat assignment (e.g., '12A', '15F')
    passenger_id = Column(Integer, ForeignKey('passenger.passenger_id'), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)  # Booking price
    
    # Relationships
    flight = relationship("Flight", back_populates="bookings", lazy="select")
    passenger = relationship("Passenger", back_populates="bookings", lazy="select")
    
    def __repr__(self):
        return f"<Booking(id={self.booking_id}, flight_id={self.flight_id}, passenger_id={self.passenger_id}, seat='{self.seat}')>"


# Create composite indexes for common query patterns used in workshop demonstrations
Index('idx_flight_route_date', Flight.from_airport, Flight.to_airport, Flight.departure)
Index('idx_flight_airline_date', Flight.airline_id, Flight.departure)
Index('idx_booking_flight_seat', Booking.flight_id, Booking.seat, unique=True)  # Unique seat per flight
Index('idx_passenger_name', Passenger.firstname, Passenger.lastname)


# Metadata for table creation and schema management
def create_all_tables(engine):
    """
    Create all database tables using the provided SQLAlchemy engine.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine):
    """
    Drop all database tables using the provided SQLAlchemy engine.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.drop_all(bind=engine)


# Export all models and utilities
__all__ = [
    'Base',
    'Airport', 
    'Airline', 
    'Flight', 
    'Passenger', 
    'Booking',
    'create_all_tables',
    'drop_all_tables'
]