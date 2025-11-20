"""SQLModel classes for the Flughafen Airport Database."""

from .airline import Airline
from .airplane import Airplane, AirplaneType
from .airport import Airport, AirportGeo, AirportReachable
from .flight import Flight, FlightSchedule, FlightLog
from .booking import Booking
from .passenger import Passenger, PassengerDetails
from .employee import Employee
from .weather import WeatherData

__all__ = [
    "Airline",
    "Airplane",
    "AirplaneType",
    "Airport",
    "AirportGeo",
    "AirportReachable",
    "Flight",
    "FlightSchedule",
    "FlightLog",
    "Booking",
    "Passenger",
    "PassengerDetails",
    "Employee",
    "WeatherData",
]
