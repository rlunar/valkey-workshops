"""
Flughafen DB SQLModel classes

The Flughafen DB by Stefan Proell, Eva Zangerle, Wolfgang Gassler 
is licensed under CC BY 4.0. To view a copy of this license, 
visit https://creativecommons.org/licenses/by/4.0
"""

from .airport import Airport, AirportType
from .airport_geo import AirportGeo, DSTType
from .airline import Airline
from .country import Country
from .airplane import Airplane
from .airplane_type import AirplaneType
from .flight import Flight
from .flight_log import FlightLog
from .flight_schedule import FlightSchedule
from .passenger import Passenger, PassengerDetails
from .booking import Booking
from .employee import Employee
from .weather import WeatherData
from .route import Route

__all__ = [
    "Airport",
    "AirportType",
    "AirportGeo",
    "DSTType",
    "Airline",
    "Airplane",
    "AirplaneType",
    "Country",
    "Flight",
    "FlightLog",
    "FlightSchedule",
    "Passenger",
    "PassengerDetails",
    "Booking",
    "Employee",
    "WeatherData",
    "Route",
]