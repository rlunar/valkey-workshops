from typing import Optional
from sqlmodel import SQLModel, Field


class Airline(SQLModel, table=True):
    __tablename__ = "airline"
    
    airline_id: Optional[int] = Field(default=None, primary_key=True)
    iata: str = Field(max_length=2, unique=True)
    airlinename: Optional[str] = Field(max_length=30)
    base_airport: int = Field(foreign_key="airport.airport_id", index=True)