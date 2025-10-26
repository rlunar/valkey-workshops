from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class FlightLog(SQLModel, table=True):
    __tablename__ = "flight_log"
    
    log_date: datetime = Field(primary_key=True)
    user: str = Field(max_length=100, primary_key=True)
    flight_id: int = Field(primary_key=True, foreign_key="flight.flight_id")
    flightno_old: str = Field(max_length=8)
    flightno_new: str = Field(max_length=8)
    from_old: int = Field(foreign_key="airport.airport_id")
    to_old: int = Field(foreign_key="airport.airport_id")
    from_new: int = Field(foreign_key="airport.airport_id")
    to_new: int = Field(foreign_key="airport.airport_id")
    departure_old: datetime
    arrival_old: datetime
    departure_new: datetime
    arrival_new: datetime
    airplane_id_old: int = Field(foreign_key="airplane.airplane_id")
    airplane_id_new: int = Field(foreign_key="airplane.airplane_id")
    airline_id_old: int = Field(foreign_key="airline.airline_id")
    airline_id_new: int = Field(foreign_key="airline.airline_id")
    comment: Optional[str] = Field(max_length=200)