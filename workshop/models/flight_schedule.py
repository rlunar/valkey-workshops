from datetime import time
from sqlmodel import SQLModel, Field


class FlightSchedule(SQLModel, table=True):
    __tablename__ = "flightschedule"
    
    flightno: str = Field(max_length=8, primary_key=True)
    from_airport: int = Field(alias="from", index=True)  # Reference to airport, no FK constraint
    to_airport: int = Field(alias="to", index=True)  # Reference to airport, no FK constraint
    departure: time
    arrival: time
    airline_id: int = Field(index=True)  # Reference to airline, no FK constraint
    monday: bool = Field(default=False)
    tuesday: bool = Field(default=False)
    wednesday: bool = Field(default=False)
    thursday: bool = Field(default=False)
    friday: bool = Field(default=False)
    saturday: bool = Field(default=False)
    sunday: bool = Field(default=False)