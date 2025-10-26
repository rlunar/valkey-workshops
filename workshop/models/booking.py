from typing import Optional
from decimal import Decimal
from sqlmodel import SQLModel, Field


class Booking(SQLModel, table=True):
    __tablename__ = "booking"
    
    booking_id: Optional[int] = Field(default=None, primary_key=True)
    flight_id: int = Field(index=True)  # Reference to flight, no FK constraint
    seat: Optional[str] = Field(max_length=4)
    passenger_id: int = Field(index=True)  # Reference to passenger, no FK constraint
    price: Decimal = Field(max_digits=10, decimal_places=2)
    
    class Config:
        # Unique constraint on flight_id + seat combination
        table_args = (
            {"mysql_engine": "InnoDB"},
        )