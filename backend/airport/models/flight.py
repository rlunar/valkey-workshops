"""
Flight-related Pydantic models for the airport workshop application.

This module contains models for flight schedules, status, and complete flight information
with proper validation and field constraints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from .enums import FlightStatus


class AirportModel(BaseModel):
    """Airport information model."""
    model_config = ConfigDict(from_attributes=True)
    
    airport_id: int
    iata: Optional[str] = Field(None, max_length=3, description="IATA airport code")
    icao: str = Field(..., max_length=4, description="ICAO airport code")
    name: str = Field(..., max_length=50, description="Airport name")


class AirlineModel(BaseModel):
    """Airline information model."""
    model_config = ConfigDict(from_attributes=True)
    
    airline_id: int
    iata: str = Field(..., max_length=2, description="IATA airline code")
    airlinename: Optional[str] = Field(None, max_length=30, description="Airline name")
    base_airport: int = Field(..., description="Base airport ID")


class FlightScheduleModel(BaseModel):
    """
    Static flight schedule data that rarely changes.
    
    This model represents the planned flight information including
    route, timing, and aircraft details.
    """
    model_config = ConfigDict(from_attributes=True)
    
    flight_id: int
    flightno: str = Field(..., max_length=8, description="Flight number")
    from_airport: int = Field(..., description="Departure airport ID")
    to_airport: int = Field(..., description="Arrival airport ID")
    scheduled_departure: datetime = Field(..., description="Scheduled departure time")
    scheduled_arrival: datetime = Field(..., description="Scheduled arrival time")
    airline_id: int = Field(..., description="Operating airline ID")
    airplane_id: int = Field(..., description="Aircraft ID")


class FlightStatusModel(BaseModel):
    """
    Dynamic flight status data that changes frequently.
    
    This model represents real-time flight status information
    including delays, gate assignments, and actual times.
    """
    model_config = ConfigDict(from_attributes=True)
    
    flight_id: int
    status: FlightStatus = Field(default=FlightStatus.SCHEDULED, description="Current flight status")
    actual_departure: Optional[datetime] = Field(None, description="Actual departure time")
    actual_arrival: Optional[datetime] = Field(None, description="Actual arrival time")
    delay_minutes: int = Field(default=0, ge=0, description="Delay in minutes")
    gate: Optional[str] = Field(None, max_length=10, description="Gate assignment")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last status update time")


class FlightModel(BaseModel):
    """
    Complete flight information combining schedule and status.
    
    This model provides a comprehensive view of flight data
    including both static schedule and dynamic status information.
    """
    model_config = ConfigDict(from_attributes=True)
    
    schedule: FlightScheduleModel
    status: FlightStatusModel
    airline: Optional[AirlineModel] = None
    departure_airport: Optional[AirportModel] = None
    arrival_airport: Optional[AirportModel] = None