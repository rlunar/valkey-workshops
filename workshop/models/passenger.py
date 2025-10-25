from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field


class Passenger(SQLModel, table=True):
    __tablename__ = "passenger"
    
    passenger_id: Optional[int] = Field(default=None, primary_key=True)
    passportno: str = Field(max_length=9, unique=True)
    firstname: str = Field(max_length=100)
    lastname: str = Field(max_length=100)


class PassengerDetails(SQLModel, table=True):
    __tablename__ = "passengerdetails"
    
    passenger_id: int = Field(primary_key=True, foreign_key="passenger.passenger_id")
    birthdate: date
    sex: Optional[str] = Field(max_length=1)
    street: str = Field(max_length=100)
    city: str = Field(max_length=100)
    zip: int = Field(ge=0, le=99999)  # smallint
    country: str = Field(max_length=100)
    emailaddress: Optional[str] = Field(max_length=120)
    telephoneno: Optional[str] = Field(max_length=30)