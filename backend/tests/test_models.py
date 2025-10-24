"""
Pytest tests for Pydantic models.
Run with: uv run pytest tests/test_models.py -v
"""

import pytest
from airport.models import *
from datetime import datetime, date
from decimal import Decimal
from pydantic import ValidationError


class TestFlightModels:
    """Test flight-related models."""
    
    def test_airport_model(self):
        """Test AirportModel creation and validation."""
        airport = AirportModel(
            airport_id=1,
            icao='KSEA',
            iata='SEA',
            name='Seattle-Tacoma International Airport'
        )
        assert airport.airport_id == 1
        assert airport.icao == 'KSEA'
        assert airport.iata == 'SEA'
        assert airport.name == 'Seattle-Tacoma International Airport'
    
    def test_flight_schedule_model(self):
        """Test FlightScheduleModel creation."""
        now = datetime.now()
        schedule = FlightScheduleModel(
            flight_id=123,
            flightno='AS1234',
            from_airport=1,
            to_airport=2,
            scheduled_departure=now,
            scheduled_arrival=now,
            airline_id=1,
            airplane_id=1
        )
        assert schedule.flight_id == 123
        assert schedule.flightno == 'AS1234'
        assert schedule.from_airport == 1
        assert schedule.to_airport == 2
    
    def test_flight_status_model(self):
        """Test FlightStatusModel with enums."""
        status = FlightStatusModel(
            flight_id=123,
            status=FlightStatus.BOARDING,
            delay_minutes=15,
            gate="A12"
        )
        assert status.flight_id == 123
        assert status.status == FlightStatus.BOARDING
        assert status.delay_minutes == 15
        assert status.gate == "A12"


class TestPassengerModels:
    """Test passenger and booking models."""
    
    def test_passenger_model(self):
        """Test PassengerModel creation."""
        passenger = PassengerModel(
            passenger_id=1,
            passportno='A12345678',
            firstname='John',
            lastname='Doe'
        )
        assert passenger.passenger_id == 1
        assert passenger.passportno == 'A12345678'
        assert passenger.firstname == 'John'
        assert passenger.lastname == 'Doe'
    
    def test_booking_model(self):
        """Test BookingModel with decimal pricing."""
        booking = BookingModel(
            booking_id=1,
            flight_id=123,
            seat='12A',
            passenger_id=1,
            price=Decimal('299.99'),
            special_requirements=['vegetarian', 'window_seat']
        )
        assert booking.booking_id == 1
        assert booking.seat == '12A'
        assert booking.price == Decimal('299.99')
        assert 'vegetarian' in booking.special_requirements


class TestSeatModels:
    """Test seat reservation models."""
    
    def test_seat_model(self):
        """Test SeatModel with enums."""
        seat = SeatModel(
            seat_number=12,
            seat_code='12A',
            seat_class=SeatClass.ECONOMY,
            status=SeatStatus.AVAILABLE
        )
        assert seat.seat_number == 12
        assert seat.seat_code == '12A'
        assert seat.seat_class == SeatClass.ECONOMY
        assert seat.status == SeatStatus.AVAILABLE
    
    def test_seat_reservation_model(self):
        """Test SeatReservationModel for distributed locking."""
        now = datetime.now()
        reservation = SeatReservationModel(
            flight_id='AS1234',
            seat_number=12,
            user_id='user123',
            reservation_id='res456',
            expires_at=now,
            lock_key='seat:AS1234:12'
        )
        assert reservation.flight_id == 'AS1234'
        assert reservation.seat_number == 12
        assert reservation.user_id == 'user123'
        assert reservation.lock_key == 'seat:AS1234:12'


class TestCacheModels:
    """Test cache and performance models."""
    
    def test_cache_metrics_model(self):
        """Test CacheMetricsModel with performance data."""
        metrics = CacheMetricsModel(
            hit_count=150,
            miss_count=50,
            hit_ratio=0.75,
            avg_response_time_ms=25.5,
            memory_usage_mb=128.0,
            key_count=1000
        )
        assert metrics.hit_count == 150
        assert metrics.miss_count == 50
        assert metrics.hit_ratio == 0.75
        assert metrics.avg_response_time_ms == 25.5
    
    def test_weather_model(self):
        """Test WeatherModel for external API caching."""
        weather = WeatherModel(
            country='USA',
            city='Seattle',
            temperature_c=18.5,
            humidity_percent=65,
            condition='cloudy',
            wind_speed_kmh=12.0,
            api_response_time_ms=150
        )
        assert weather.country == 'USA'
        assert weather.city == 'Seattle'
        assert weather.temperature_c == 18.5
        assert weather.condition == 'cloudy'


class TestValidation:
    """Test model validation constraints."""
    
    def test_negative_seat_number_rejected(self):
        """Test that negative seat numbers are rejected."""
        with pytest.raises(ValidationError):
            SeatModel(
                seat_number=-1,
                seat_code='1A',
                seat_class=SeatClass.FIRST
            )
    
    def test_invalid_icao_code_rejected(self):
        """Test that invalid ICAO codes are rejected."""
        with pytest.raises(ValidationError):
            AirportModel(
                airport_id=1,
                icao='TOOLONG',  # Too long for ICAO
                name='Test Airport'
            )
    
    def test_invalid_hit_ratio_rejected(self):
        """Test that hit ratios outside 0-1 range are rejected."""
        with pytest.raises(ValidationError):
            CacheMetricsModel(hit_ratio=1.5)  # > 1.0


class TestComplexModels:
    """Test complex nested models."""
    
    def test_flight_manifest_model(self):
        """Test Russian doll cache structure with nested models."""
        manifest = FlightManifestModel(
            flight_id=123,
            flight_number='AS1234',
            total_passengers=1,
            passengers=[
                PassengerManifestEntryModel(
                    booking=BookingModel(
                        booking_id=1,
                        flight_id=123,
                        seat='12A',
                        passenger_id=1,
                        price=Decimal('299.99')
                    ),
                    passenger=PassengerModel(
                        passenger_id=1,
                        passportno='A12345678',
                        firstname='John',
                        lastname='Doe'
                    ),
                    seat_assignment='12A',
                    check_in_status=True
                )
            ]
        )
        assert manifest.flight_id == 123
        assert manifest.flight_number == 'AS1234'
        assert manifest.total_passengers == 1
        assert len(manifest.passengers) == 1
        assert manifest.passengers[0].seat_assignment == '12A'
    
    def test_cache_dependency_model(self):
        """Test cache dependency tracking."""
        dependency = CacheDependencyModel(
            parent_key='flight:AS1234',
            child_key='manifest:AS1234',
            dependency_type=DependencyType.PARENT_CHILD
        )
        assert dependency.parent_key == 'flight:AS1234'
        assert dependency.child_key == 'manifest:AS1234'
        assert dependency.dependency_type == DependencyType.PARENT_CHILD
        assert dependency.is_active is True
    
    def test_model_serialization(self):
        """Test that models can be serialized to JSON."""
        airport = AirportModel(
            airport_id=1,
            icao='KSEA',
            name='Seattle Airport'
        )
        
        # Test model_dump (Pydantic v2)
        data = airport.model_dump()
        assert isinstance(data, dict)
        assert data['airport_id'] == 1
        assert data['icao'] == 'KSEA'
        
        # Test round-trip serialization
        new_airport = AirportModel(**data)
        assert new_airport.airport_id == airport.airport_id
        assert new_airport.icao == airport.icao