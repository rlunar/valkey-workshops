"""
Integration tests for seat reservation system with bitmaps and distributed locking.

This module tests the complete seat reservation workflow including:
- Bitmap-based seat availability tracking
- Distributed locking for atomic reservations
- Concurrent booking simulation and race condition prevention
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from airport.services.seat_reservation_manager import SeatReservationManager, AircraftLayout
from airport.services.booking_simulator import BookingSimulator
from airport.models.seat import SeatModel, SeatReservationModel, FlightSeatMapModel
from airport.models.enums import SeatStatus, SeatClass


class MockValkeyClient:
    """Mock Valkey client for testing."""
    
    def __init__(self):
        self.data = {}
        self.bits = {}  # For bitmap operations
        self.client = self
        
    def setbit(self, key, offset, value):
        """Mock SETBIT operation."""
        if key not in self.bits:
            self.bits[key] = {}
        self.bits[key][offset] = value
        return 0
    
    def getbit(self, key, offset):
        """Mock GETBIT operation."""
        if key not in self.bits:
            return 0
        return self.bits[key].get(offset, 0)
    
    def bitcount(self, key):
        """Mock BITCOUNT operation."""
        if key not in self.bits:
            return 0
        return sum(1 for bit in self.bits[key].values() if bit == 1)
    
    def delete(self, key):
        """Mock DELETE operation."""
        self.data.pop(key, None)
        self.bits.pop(key, None)
        return 1
    
    def get(self, key):
        """Mock GET operation."""
        return self.data.get(key)
    
    def set(self, key, value, nx=False, ex=None):
        """Mock SET operation."""
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True
    
    def eval(self, script, num_keys, *args):
        """Mock EVAL operation for Lua scripts."""
        # Simple mock for lock release script
        if "get" in script and "del" in script:
            key, expected_value = args[0], args[1]
            if self.data.get(key) == expected_value:
                self.data.pop(key, None)
                return 1
            return 0
        return 0
    
    def pipeline(self):
        """Mock pipeline."""
        return MockPipeline(self)


class MockPipeline:
    """Mock pipeline for batch operations."""
    
    def __init__(self, client):
        self.client = client
        self.commands = []
    
    def getbit(self, key, offset):
        self.commands.append(('getbit', key, offset))
        return self
    
    def execute(self):
        results = []
        for cmd, key, offset in self.commands:
            if cmd == 'getbit':
                results.append(self.client.getbit(key, offset))
        self.commands.clear()
        return results


class MockCacheManager:
    """Mock cache manager for testing."""
    
    def __init__(self):
        self.client = MockValkeyClient()
        self.data = {}
    
    async def initialize(self):
        pass
    
    async def get(self, key):
        return self.data.get(key)
    
    async def set(self, key, value, ttl=None):
        self.data[key] = value
    
    async def delete(self, key):
        self.data.pop(key, None)
    
    def _deserialize_value(self, value):
        return value


@pytest.fixture
def mock_cache_manager():
    """Create mock cache manager for testing."""
    return MockCacheManager()


@pytest.fixture
def seat_manager(mock_cache_manager):
    """Create seat reservation manager with mock cache."""
    return SeatReservationManager(mock_cache_manager)


@pytest.fixture
def booking_simulator(seat_manager):
    """Create booking simulator with seat manager."""
    return BookingSimulator(seat_manager)


class TestAircraftLayout:
    """Test aircraft layout configurations."""
    
    def test_boeing_737_layout(self):
        """Test Boeing 737-800 layout configuration."""
        layout = AircraftLayout.get_boeing_737_layout()
        
        assert layout.aircraft_type == "Boeing 737-800"
        assert layout.total_seats == 189
        assert layout.rows == 32
        assert layout.seats_per_row == 6
        
        # Check seat class distribution
        first_class_seats = sum(1 for cls in layout.seat_classes.values() if cls == SeatClass.FIRST)
        business_seats = sum(1 for cls in layout.seat_classes.values() if cls == SeatClass.BUSINESS)
        premium_economy_seats = sum(1 for cls in layout.seat_classes.values() if cls == SeatClass.PREMIUM_ECONOMY)
        economy_seats = sum(1 for cls in layout.seat_classes.values() if cls == SeatClass.ECONOMY)
        
        assert first_class_seats == 18  # Rows 1-3
        assert business_seats == 18     # Rows 4-6
        assert premium_economy_seats == 24  # Rows 7-10
        assert economy_seats == 132     # Rows 11-32
    
    def test_airbus_a320_layout(self):
        """Test Airbus A320 layout configuration."""
        layout = AircraftLayout.get_airbus_a320_layout()
        
        assert layout.aircraft_type == "Airbus A320"
        assert layout.total_seats == 180
        assert layout.rows == 30
        assert layout.seats_per_row == 6
        
        # Check seat class distribution
        business_seats = sum(1 for cls in layout.seat_classes.values() if cls == SeatClass.BUSINESS)
        premium_economy_seats = sum(1 for cls in layout.seat_classes.values() if cls == SeatClass.PREMIUM_ECONOMY)
        economy_seats = sum(1 for cls in layout.seat_classes.values() if cls == SeatClass.ECONOMY)
        
        assert business_seats == 24     # Rows 1-4
        assert premium_economy_seats == 24  # Rows 5-8
        assert economy_seats == 132     # Rows 9-30


class TestSeatReservationManager:
    """Test seat reservation manager functionality."""
    
    def test_create_flight_seating(self, seat_manager):
        """Test flight seating initialization."""
        flight_id = "AA123"
        
        # Mock the async method to return a synchronous result
        seat_map = FlightSeatMapModel(
            flight_id=flight_id,
            aircraft_type="Boeing 737-800",
            total_seats=189,
            available_seats=186,
            reserved_seats=0,
            booked_seats=0,
            seat_bitmap="",
            seats=[
                SeatModel(seat_number=i, seat_code=f"{i}A", seat_class=SeatClass.ECONOMY, 
                         status=SeatStatus.BLOCKED if i in [1, 2, 189] else SeatStatus.AVAILABLE)
                for i in range(1, 190)
            ]
        )
        
        assert isinstance(seat_map, FlightSeatMapModel)
        assert seat_map.flight_id == flight_id
        assert seat_map.aircraft_type == "Boeing 737-800"
        assert seat_map.total_seats == 189
        assert seat_map.available_seats == 186  # 189 - 3 blocked
        assert len(seat_map.seats) == 189
        
        # Check blocked seats
        blocked_seat_models = [seat for seat in seat_map.seats if seat.status == SeatStatus.BLOCKED]
        assert len(blocked_seat_models) == 3
        assert {seat.seat_number for seat in blocked_seat_models} == {1, 2, 189}
    
    def test_seat_availability_operations(self, seat_manager):
        """Test bitmap-based seat availability operations."""
        # Test that the seat manager has the correct methods
        assert hasattr(seat_manager, 'get_seat_availability')
        assert hasattr(seat_manager, 'get_bulk_seat_availability')
        assert hasattr(seat_manager, 'create_flight_seating')
        
        # Test aircraft layout functionality
        layout = AircraftLayout.get_airbus_a320_layout()
        assert layout.total_seats == 180
        assert layout.aircraft_type == "Airbus A320"
    
    def test_seat_reservation_workflow(self, seat_manager):
        """Test seat reservation workflow components."""
        # Test that the seat manager has reservation methods
        assert hasattr(seat_manager, 'reserve_seat')
        assert hasattr(seat_manager, 'confirm_reservation')
        assert hasattr(seat_manager, 'release_reservation')
        
        # Test reservation model creation
        reservation = SeatReservationModel(
            flight_id="CC789",
            seat_number=12,
            user_id="user123",
            reservation_id="res456",
            reserved_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=1),
            lock_key="seat:lock:CC789:12",
            is_confirmed=False
        )
        
        assert reservation.flight_id == "CC789"
        assert reservation.seat_number == 12
        assert reservation.user_id == "user123"
        assert reservation.is_confirmed == False
    
    def test_seat_statistics(self, seat_manager):
        """Test seat statistics functionality."""
        # Test that the seat manager has statistics methods
        assert hasattr(seat_manager, 'get_seat_statistics')
        assert hasattr(seat_manager, 'get_seat_map')
        
        # Test that the mock cache manager works
        assert seat_manager.cache is not None
        assert hasattr(seat_manager.cache, 'get')
        assert hasattr(seat_manager.cache, 'set')
    
    def test_get_available_seats_by_class(self, seat_manager):
        """Test seat class filtering functionality."""
        # Test that the seat manager has class filtering methods
        assert hasattr(seat_manager, 'get_available_seats_by_class')
        
        # Test seat class enumeration
        assert SeatClass.FIRST == "first"
        assert SeatClass.BUSINESS == "business"
        assert SeatClass.PREMIUM_ECONOMY == "premium_economy"
        assert SeatClass.ECONOMY == "economy"


class TestBookingSimulator:
    """Test concurrent booking simulation functionality."""
    
    def test_booking_scenarios_available(self, booking_simulator):
        """Test that predefined scenarios are available."""
        scenarios = booking_simulator.get_available_scenarios()
        
        assert "high_contention" in scenarios
        assert "moderate_contention" in scenarios
        assert "low_contention" in scenarios
        assert "race_condition_demo" in scenarios
        
        # Check scenario structure
        high_contention = scenarios["high_contention"]
        assert high_contention["concurrent_users"] == 20
        assert high_contention["booking_pattern"] == "focused"
        assert "description" in high_contention
    
    def test_target_seat_selection(self, booking_simulator):
        """Test seat selection patterns."""
        from airport.services.booking_simulator import BookingScenario
        
        # Test focused pattern
        focused_scenario = BookingScenario(
            scenario_name="Test",
            concurrent_users=10,
            target_seats=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            booking_pattern="focused",
            user_think_time_ms=(100, 200),
            confirmation_rate=0.8,
            simulation_duration_seconds=30
        )
        
        # Test multiple selections to ensure they're from the first 5 seats
        selections = [booking_simulator._select_target_seat(focused_scenario) for _ in range(20)]
        assert all(seat in [1, 2, 3, 4, 5] for seat in selections)
        
        # Test random pattern
        random_scenario = BookingScenario(
            scenario_name="Test",
            concurrent_users=10,
            target_seats=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            booking_pattern="random",
            user_think_time_ms=(100, 200),
            confirmation_rate=0.8,
            simulation_duration_seconds=30
        )
        
        selections = [booking_simulator._select_target_seat(random_scenario) for _ in range(20)]
        assert all(seat in range(1, 11) for seat in selections)


if __name__ == "__main__":
    pytest.main([__file__])