from typing import Optional
from datetime import datetime, time
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


class FlightSchedule(SQLModel, table=True):
    __tablename__ = "flightschedule"
    
    flightno: str = Field(max_length=8, primary_key=True)
    from_airport: int = Field(alias="from", foreign_key="airport.airport_id", index=True)
    to_airport: int = Field(alias="to", foreign_key="airport.airport_id", index=True)
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