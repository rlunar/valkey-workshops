"""
Flughafen DB SQLModel classes

The Flughafen DB by Stefan Proell, Eva Zangerle, Wolfgang Gassler 
is licensed under CC BY 4.0. To view a copy of this license, 
visit https://creativecommons.org/licenses/by/4.0
"""

from .airport import Airport, AirportGeo, AirportReachable
from .airline import Airline
from .airplane import Airplane, AirplaneType
from .flight import Flight, FlightLog, FlightSchedule
from .passenger import Passenger, PassengerDetails
from .booking import Booking
from .employee import Employee
from .weather import WeatherData

__all__ = [
    "Airport",
    "AirportGeo", 
    "AirportReachable",
    "Airline",
    "Airplane",
    "AirplaneType",
    "Flight",
    "FlightLog",
    "FlightSchedule",
    "Passenger",
    "PassengerDetails",
    "Booking",
    "Employee",
    "WeatherData",
]