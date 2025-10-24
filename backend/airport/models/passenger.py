"""
Passenger and booking-related Pydantic models for the airport workshop application.

This module contains models for passenger information, bookings, and related
data structures with proper validation and field constraints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from .flight import FlightModel


class PassengerModel(BaseModel):
    """
    Passenger information model with validation.
    
    Contains personal information and identification details
    for passengers in the airport system.
    """
    model_config = ConfigDict(from_attributes=True)
    
    passenger_id: int
    passportno: str = Field(..., max_length=9, description="Passport number")
    firstname: str = Field(..., max_length=100, description="First name")
    lastname: str = Field(..., max_length=100, description="Last name")


class BookingModel(BaseModel):
    """
    Flight booking model with comprehensive booking information.
    
    Represents a passenger's booking for a specific flight including
    seat assignment, pricing, and special requirements.
    """
    model_config = ConfigDict(from_attributes=True)
    
    booking_id: int
    flight_id: int = Field(..., description="Associated flight ID")
    seat: Optional[str] = Field(None, max_length=4, description="Seat assignment (e.g., '12A')")
    passenger_id: int = Field(..., description="Associated passenger ID")
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2, description="Booking price")
    booking_date: datetime = Field(default_factory=datetime.now, description="Booking creation date")
    special_requirements: Optional[List[str]] = Field(
        default=None, 
        description="Special requirements (meals, accessibility, etc.)"
    )
    
    # Optional related objects
    flight: Optional[FlightModel] = None
    passenger: Optional[PassengerModel] = None