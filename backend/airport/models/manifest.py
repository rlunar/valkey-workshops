"""
Passenger manifest and Russian doll cache models for the airport workshop application.

This module contains models for flight manifests, passenger entries, and nested
cache structures used in the Russian doll caching demonstration.
"""

from datetime import datetime, date
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from .flight import FlightModel
from .airport import AirportModel
from .passenger import PassengerModel, BookingModel


class PassengerManifestEntryModel(BaseModel):
    """
    Individual passenger entry in flight manifest.
    
    Represents a single passenger's information within
    a flight's passenger manifest including booking details
    and special requirements.
    """
    model_config = ConfigDict(from_attributes=True)
    
    booking: BookingModel
    passenger: PassengerModel
    seat_assignment: Optional[str] = Field(None, description="Assigned seat (e.g., '12A')")
    check_in_status: bool = Field(default=False, description="Whether passenger has checked in")
    boarding_group: Optional[str] = Field(None, description="Boarding group assignment")
    special_assistance: Optional[List[str]] = Field(
        default=None, 
        description="Special assistance requirements"
    )


class FlightManifestModel(BaseModel):
    """
    Complete passenger manifest for a flight.
    
    Represents the full passenger list for a flight with
    seat assignments and manifest statistics for Russian
    doll caching demonstrations.
    """
    model_config = ConfigDict(from_attributes=True)
    
    flight_id: int = Field(..., description="Flight identifier")
    flight_number: str = Field(..., description="Flight number")
    total_passengers: int = Field(..., ge=0, description="Total number of passengers")
    checked_in_count: int = Field(default=0, ge=0, description="Number of checked-in passengers")
    passengers: List[PassengerManifestEntryModel] = Field(
        default_factory=list, 
        description="List of passenger manifest entries"
    )
    seat_map: Dict[str, Optional[int]] = Field(
        default_factory=dict, 
        description="Seat to passenger_id mapping"
    )
    cached_at: datetime = Field(default_factory=datetime.now, description="Cache creation time")
    cache_ttl_seconds: int = Field(default=1800, description="Cache TTL (30 minutes)")


class AirportDailyFlightsModel(BaseModel):
    """
    Nested cache structure for airport daily flights.
    
    Represents the top-level Russian doll cache structure
    containing airport information and all flights for a specific day.
    """
    model_config = ConfigDict(from_attributes=True)
    
    airport: AirportModel
    flight_date: date = Field(..., description="Date for flight data")
    departing_flights: List[FlightModel] = Field(
        default_factory=list, 
        description="Flights departing from this airport"
    )
    arriving_flights: List[FlightModel] = Field(
        default_factory=list, 
        description="Flights arriving at this airport"
    )
    cached_at: datetime = Field(default_factory=datetime.now, description="Cache creation time")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL (1 hour for schedule data)")


class NestedFlightDataModel(BaseModel):
    """
    Nested flight data structure for Russian doll caching.
    
    Combines flight schedule, status, and manifest data
    in a hierarchical structure for cache dependency demonstrations.
    """
    model_config = ConfigDict(from_attributes=True)
    
    flight: FlightModel
    manifest: Optional[FlightManifestModel] = None
    weather_data: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Weather data for departure/arrival airports"
    )
    cached_fragments: Dict[str, datetime] = Field(
        default_factory=dict, 
        description="Timestamps of cached fragments"
    )
    cache_dependencies: List[str] = Field(
        default_factory=list, 
        description="List of dependent cache keys"
    )