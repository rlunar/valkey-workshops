from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Flight(SQLModel, table=True):
    __tablename__ = "flight"
    
    flight_id: Optional[int] = Field(default=None, primary_key=True)
    flightno: str = Field(max_length=8)
    from_airport: int = Field(alias="from", foreign_key="airport.airport_id", index=True)
    to_airport: int = Field(alias="to", foreign_key="airport.airport_id", index=True)
    departure: datetime = Field(index=True)
    arrival: datetime = Field(index=True)
    airline_id: int = Field(foreign_key="airline.airline_id", index=True)
    airplane_id: int = Field(foreign_key="airplane.airplane_id", index=True)