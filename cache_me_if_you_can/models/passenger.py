"""Passenger-related models."""

from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field


class Passenger(SQLModel, table=True):
    """Passenger with passport information."""
    
    __tablename__ = "passenger"
    
    passenger_id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    passportno: str = Field(max_length=9, unique=True)
    firstname: str = Field(max_length=100)
    lastname: str = Field(max_length=100)


class PassengerDetails(SQLModel, table=True):
    """Extended passenger details with contact information."""
    
    __tablename__ = "passengerdetails"
    
    passenger_id: int = Field(foreign_key="passenger.passenger_id", primary_key=True)
    birthdate: date
    sex: Optional[str] = Field(default=None, max_length=1)
    street: str = Field(max_length=100)
    city: str = Field(max_length=100)
    zip: int
    country: str = Field(max_length=100)
    emailaddress: Optional[str] = Field(default=None, max_length=120)
    telephoneno: Optional[str] = Field(default=None, max_length=30)
