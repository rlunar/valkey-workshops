"""Booking model."""

from typing import Optional
from decimal import Decimal
from sqlmodel import SQLModel, Field


class Booking(SQLModel, table=True):
    """Flight booking linking passengers to flights."""
    
    __tablename__ = "booking"
    
    booking_id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    flight_id: int = Field(foreign_key="flight.flight_id", index=True)
    seat: Optional[str] = Field(default=None, max_length=4)
    passenger_id: int = Field(foreign_key="passenger.passenger_id", index=True)
    price: Decimal = Field(max_digits=10, decimal_places=2)
