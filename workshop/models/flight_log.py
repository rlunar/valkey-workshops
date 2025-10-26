from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class FlightLog(SQLModel, table=True):
    __tablename__ = "flight_log"
    
    log_date: datetime = Field(primary_key=True)
    user: str = Field(max_length=100, primary_key=True)
    flight_id: int = Field(primary_key=True, index=True)  # Reference to flight, no FK constraint
    flightno_old: str = Field(max_length=8)
    flightno_new: str = Field(max_length=8)
    from_old: int = Field(index=True)  # Reference to airport, no FK constraint
    to_old: int = Field(index=True)  # Reference to airport, no FK constraint
    from_new: int = Field(index=True)  # Reference to airport, no FK constraint
    to_new: int = Field(index=True)  # Reference to airport, no FK constraint
    departure_old: datetime
    arrival_old: datetime
    departure_new: datetime
    arrival_new: datetime
    airplane_id_old: int = Field(index=True)  # Reference to airplane, no FK constraint
    airplane_id_new: int = Field(index=True)  # Reference to airplane, no FK constraint
    airline_id_old: int = Field(index=True)  # Reference to airline, no FK constraint
    airline_id_new: int = Field(index=True)  # Reference to airline, no FK constraint
    comment: Optional[str] = Field(max_length=200)