"""Flight-related models."""

from typing import Optional
from datetime import datetime, time
from sqlmodel import SQLModel, Field


class Flight(SQLModel, table=True):
    """Individual flight with departure/arrival times."""
    
    __tablename__ = "flight"
    
    flight_id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    flightno: str = Field(max_length=8)
    from_airport_id: int = Field(foreign_key="airport.airport_id", index=True, sa_column_kwargs={"name": "from"})
    to_airport_id: int = Field(foreign_key="airport.airport_id", index=True, sa_column_kwargs={"name": "to"})
    departure: datetime = Field(index=True)
    arrival: datetime = Field(index=True)
    airline_id: int = Field(foreign_key="airline.airline_id", index=True)
    airplane_id: int = Field(foreign_key="airplane.airplane_id", index=True)



class FlightSchedule(SQLModel, table=True):
    """Recurring flight schedule with weekday flags."""
    
    __tablename__ = "flightschedule"
    
    flightno: str = Field(max_length=8, primary_key=True)
    from_airport_id: int = Field(foreign_key="airport.airport_id", index=True, sa_column_kwargs={"name": "from"})
    to_airport_id: int = Field(foreign_key="airport.airport_id", index=True, sa_column_kwargs={"name": "to"})
    departure: time
    arrival: time
    airline_id: int = Field(foreign_key="airline.airline_id", index=True)
    monday: bool = Field(default=False)
    tuesday: bool = Field(default=False)
    wednesday: bool = Field(default=False)
    thursday: bool = Field(default=False)
    friday: bool = Field(default=False)
    saturday: bool = Field(default=False)
    sunday: bool = Field(default=False)



class FlightLog(SQLModel, table=True):
    """Audit log for flight changes."""
    
    __tablename__ = "flight_log"
    
    log_date: datetime = Field(primary_key=True)
    user: str = Field(max_length=100, primary_key=True)
    flight_id: int = Field(primary_key=True)
    flightno_old: str = Field(max_length=8)
    flightno_new: str = Field(max_length=8)
    from_old: int
    to_old: int
    from_new: int
    to_new: int
    departure_old: datetime
    arrival_old: datetime
    departure_new: datetime
    arrival_new: datetime
    airplane_id_old: int
    airplane_id_new: int
    airline_id_old: int
    airline_id_new: int
    comment: Optional[str] = Field(default=None, max_length=200)
