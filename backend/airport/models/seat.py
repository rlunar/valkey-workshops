"""
Seat reservation models for the airport workshop application.

This module contains models for seat management, reservations, and bitmap operations
used in the seat reservation demonstration use case.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from .enums import SeatStatus, SeatClass


class SeatModel(BaseModel):
    """
    Individual seat information model.
    
    Represents a single seat on an aircraft with its properties,
    status, and reservation information.
    """
    model_config = ConfigDict(from_attributes=True)
    
    seat_number: int = Field(..., ge=1, description="Seat number (1-based)")
    seat_code: str = Field(..., description="Seat code (e.g., '12A', '15F')")
    seat_class: SeatClass = Field(..., description="Seat class category")
    status: SeatStatus = Field(default=SeatStatus.AVAILABLE, description="Current seat status")
    reserved_by: Optional[str] = Field(None, description="User ID if reserved")
    reserved_at: Optional[datetime] = Field(None, description="Reservation timestamp")
    booking_id: Optional[int] = Field(None, description="Booking ID if confirmed")


class SeatReservationModel(BaseModel):
    """
    Seat reservation with distributed lock information.
    
    Represents a temporary seat reservation with lock details
    for the distributed locking demonstration.
    """
    model_config = ConfigDict(from_attributes=True)
    
    flight_id: str = Field(..., description="Flight identifier")
    seat_number: int = Field(..., ge=1, description="Reserved seat number")
    user_id: str = Field(..., description="User making the reservation")
    reservation_id: str = Field(..., description="Unique reservation identifier")
    reserved_at: datetime = Field(default_factory=datetime.now, description="Reservation timestamp")
    expires_at: datetime = Field(..., description="Reservation expiration time")
    lock_key: str = Field(..., description="Valkey lock key")
    is_confirmed: bool = Field(default=False, description="Whether reservation is confirmed")


class FlightSeatMapModel(BaseModel):
    """
    Complete seat map for a flight using bitmap operations.
    
    Represents the entire seating configuration for a flight
    with bitmap-based seat availability tracking.
    """
    model_config = ConfigDict(from_attributes=True)
    
    flight_id: str = Field(..., description="Flight identifier")
    aircraft_type: str = Field(..., description="Aircraft model/type")
    total_seats: int = Field(..., ge=1, description="Total number of seats")
    available_seats: int = Field(..., ge=0, description="Number of available seats")
    reserved_seats: int = Field(..., ge=0, description="Number of reserved seats")
    booked_seats: int = Field(..., ge=0, description="Number of confirmed bookings")
    seat_bitmap: str = Field(..., description="Base64 encoded bitmap for seat status")
    seats: List[SeatModel] = Field(default_factory=list, description="Detailed seat information")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")