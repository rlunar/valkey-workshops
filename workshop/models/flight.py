from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Flight(SQLModel, table=True):
    __tablename__ = "flight"
    
    flight_id: Optional[int] = Field(default=None, primary_key=True)
    flightno: str = Field(max_length=8)
    from_airport: int = Field(alias="from", index=True)  # Reference to airport, no FK constraint
    to_airport: int = Field(alias="to", index=True)  # Reference to airport, no FK constraint
    departure: datetime = Field(index=True)
    arrival: datetime = Field(index=True)
    airline_id: int = Field(index=True)  # Reference to airline, no FK constraint
    airplane_id: int = Field(index=True)  # Reference to airplane, no FK constraint