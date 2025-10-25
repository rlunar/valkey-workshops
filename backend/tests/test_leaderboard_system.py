"""
Test for the real-time leaderboard system implementation.

This test validates the leaderboard functionality implemented in task 7,
including sorted set operations, atomic updates, pagination, and memory optimization.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from airport.services.leaderboard import LeaderboardSystem, LeaderboardEntry, LeaderboardStats


class MockValkeyClient:
    """Mock Valkey client for testing leaderboard functionality."""
    
    def __init__(self):
        self.data = {}
        self.sorted_sets = {}
        self.hash_data = {}
        self.is_connected = True
        self._client = MagicMock()
        
    async def ensure_connection(self):
        """Mock connection check."""
        pass
    
    @property
    def client(self):
        """Mock client property."""
        mock_client = MagicMock()
        
        # Mock ZADD operation
        def zadd(key, mapping):
            if key not in self.sorted_sets:
                self.sorted_sets[key] = {}
            self.sorted_sets[key].update(mapping)
            return len(mapping)
        
        # Mock ZINCRBY operation
        def zincrby(key, increment, member):
            if key not in self.sorted_sets:
                self.sorted_sets[key] = {}
            current_score = self.sorted_sets[key].get(member, 0)
            new_score = current_score + increment
            self.sorted_sets[key][member] = new_score
            return new_score
        
        # Mock ZREVRANGE operation
        def zrevrange(key, start, end, withscores=False):
            if key not in self.sorted_sets:
                return []
            
            # Sort by score descending
            sorted_items = sorted(
                self.sorted_sets[key].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Apply range
            if end == -1:
                range_items = sorted_items[start:]
            else:
                range_items = sorted_items[start:end+1]
            
            if withscores:
                return [(k.encode(), v) for k, v in range_items]
            else:
                return [k.encode() for k, v in range_items]
        
        # Mock ZREVRANK operation
        def zrevrank(key, member):
            if key not in self.sorted_sets or member not in self.sorted_sets[key]:
                return None
            
            # Sort by score descending and find rank
            sorted_items = sorted(
                self.sorted_sets[key].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            for i, (k, v) in enumerate(sorted_items):
                if k == member:
                    return i
            return None
        
        # Mock ZSCORE operation
        def zscore(key, member):
            if key not in self.sorted_sets or member not in self.sorted_sets[key]:
                return None
            return self.sorted_sets[key][member]
        
        # Mock ZCARD operation
        def zcard(key):
            if key not in self.sorted_sets:
                return 0
            return len(self.sorted_sets[key])
        
        # Mock ZRANGE operation
        def zrange(key, start, end, withscores=False):
            if key not in self.sorted_sets:
                return []
            
            # Sort by score ascending
            sorted_items = sorted(
                self.sorted_sets[key].items(), 
                key=lambda x: x[1]
            )
            
            # Apply range
            if end == -1:
                range_items = sorted_items[start:]
            else:
                range_items = sorted_items[start:end+1]
            
            if withscores:
                return [(k.encode(), v) for k, v in range_items]
            else:
                return [k.encode() for k, v in range_items]
        
        # Mock HSET operation
        def hset(key, mapping=None, **kwargs):
            if key not in self.hash_data:
                self.hash_data[key] = {}
            if mapping:
                self.hash_data[key].update(mapping)
            self.hash_data[key].update(kwargs)
            return len(mapping) if mapping else len(kwargs)
        
        # Mock HGETALL operation
        def hgetall(key):
            if key not in self.hash_data:
                return {}
            return {k.encode(): v.encode() for k, v in self.hash_data[key].items()}
        
        # Mock HGET operation
        def hget(key, field):
            if key not in self.hash_data or field not in self.hash_data[key]:
                return None
            return self.hash_data[key][field].encode()
        
        # Mock EXPIRE operation
        def expire(key, seconds):
            return True
        
        # Mock SETEX operation
        def setex(key, seconds, value):
            self.data[key] = value
            return True
        
        # Mock GET operation
        def get(key):
            return self.data.get(key, None)
        
        # Mock MEMORY_USAGE operation (fallback)
        def memory_usage(key):
            return None  # Will trigger fallback estimation
        
        # Mock DELETE operation
        def delete(*keys):
            deleted = 0
            for key in keys:
                if key in self.sorted_sets:
                    del self.sorted_sets[key]
                    deleted += 1
                if key in self.hash_data:
                    del self.hash_data[key]
                    deleted += 1
            return deleted
        
        # Mock KEYS operation
        def keys(pattern):
            all_keys = list(self.sorted_sets.keys()) + list(self.hash_data.keys())
            # Simple pattern matching (just check if pattern prefix matches)
            if pattern.endswith('*'):
                prefix = pattern[:-1]
                return [k.encode() for k in all_keys if k.startswith(prefix)]
            return [k.encode() for k in all_keys if k == pattern]
        
        # Mock EXISTS operation
        def exists(key):
            return key in self.sorted_sets or key in self.hash_data
        
        # Mock pipeline
        class MockPipeline:
            def __init__(self, client):
                self.client = client
                self.commands = []
            
            def zadd(self, key, mapping):
                self.commands.append(('zadd', key, mapping))
                return self
            
            def hset(self, key, mapping=None, **kwargs):
                self.commands.append(('hset', key, mapping or kwargs))
                return self
            
            def expire(self, key, seconds):
                self.commands.append(('expire', key, seconds))
                return self
            
            def delete(self, *keys):
                self.commands.append(('delete', keys))
                return self
            
            def execute(self):
                results = []
                for cmd, *args in self.commands:
                    if cmd == 'zadd':
                        results.append(self.client.zadd(args[0], args[1]))
                    elif cmd == 'hset':
                        results.append(self.client.hset(args[0], args[1]))
                    elif cmd == 'expire':
                        results.append(self.client.expire(args[0], args[1]))
                    elif cmd == 'delete':
                        results.append(self.client.delete(*args[0]))
                return results
        
        def pipeline():
            return MockPipeline(mock_client)
        
        # Assign mock methods
        mock_client.zadd = zadd
        mock_client.zincrby = zincrby
        mock_client.zrevrange = zrevrange
        mock_client.zrevrank = zrevrank
        mock_client.zscore = zscore
        mock_client.zcard = zcard
        mock_client.zrange = zrange
        mock_client.hset = hset
        mock_client.hgetall = hgetall
        mock_client.hget = hget
        mock_client.expire = expire
        mock_client.delete = delete
        mock_client.keys = keys
        mock_client.exists = exists
        mock_client.pipeline = pipeline
        mock_client.setex = setex
        mock_client.get = get
        mock_client.memory_usage = memory_usage
        
        return mock_client


class TestLeaderboardSystem:
    """Test cases for the LeaderboardSystem implementation."""
    
    @pytest.fixture
    def mock_valkey_client(self):
        """Create a mock Valkey client."""
        return MockValkeyClient()
    
    @pytest.fixture
    def leaderboard_system(self, mock_valkey_client):
        """Create a leaderboard system with mock client."""
        return LeaderboardSystem(mock_valkey_client, "test_leaderboard")
    
    @pytest.mark.asyncio
    async def test_update_passenger_score(self, leaderboard_system):
        """Test updating passenger scores with atomic operations."""
        # Test basic score update
        success = await leaderboard_system.update_passenger_score(
            "passenger_1", 
            5, 
            {"name": "John Doe", "firstname": "John", "lastname": "Doe"}
        )
        
        assert success is True
        
        # Verify score was set
        score = await leaderboard_system.get_passenger_score("passenger_1")
        assert score == 5
        
        # Test score update (overwrite)
        success = await leaderboard_system.update_passenger_score("passenger_1", 10)
        assert success is True
        
        score = await leaderboard_system.get_passenger_score("passenger_1")
        assert score == 10
    
    @pytest.mark.asyncio
    async def test_increment_passenger_score(self, leaderboard_system):
        """Test atomic score increments using ZINCRBY."""
        # Test initial increment
        new_score = await leaderboard_system.increment_passenger_score(
            "passenger_1", 
            3,
            {"name": "Alice Smith", "firstname": "Alice", "lastname": "Smith"}
        )
        assert new_score == 3
        
        # Test additional increment
        new_score = await leaderboard_system.increment_passenger_score("passenger_1", 2)
        assert new_score == 5
        
        # Test negative increment (decrement)
        new_score = await leaderboard_system.increment_passenger_score("passenger_1", -1)
        assert new_score == 4
    
    @pytest.mark.asyncio
    async def test_get_top_passengers_with_pagination(self, leaderboard_system):
        """Test top passengers query with pagination using ZREVRANGE."""
        # Add test passengers with different scores
        passengers = [
            ("passenger_1", 10, {"name": "Alice", "firstname": "Alice", "lastname": "Smith"}),
            ("passenger_2", 8, {"name": "Bob", "firstname": "Bob", "lastname": "Jones"}),
            ("passenger_3", 12, {"name": "Charlie", "firstname": "Charlie", "lastname": "Brown"}),
            ("passenger_4", 6, {"name": "Diana", "firstname": "Diana", "lastname": "Wilson"}),
            ("passenger_5", 15, {"name": "Eve", "firstname": "Eve", "lastname": "Davis"}),
        ]
        
        for passenger_id, score, info in passengers:
            await leaderboard_system.update_passenger_score(passenger_id, score, info)
        
        # Test top 3 passengers
        top_3 = await leaderboard_system.get_top_passengers(limit=3)
        
        assert len(top_3) == 3
        assert top_3[0].passenger_id == "passenger_5"  # Score: 15
        assert top_3[0].booking_count == 15
        assert top_3[0].rank == 1
        assert top_3[1].passenger_id == "passenger_3"  # Score: 12
        assert top_3[1].rank == 2
        assert top_3[2].passenger_id == "passenger_1"  # Score: 10
        assert top_3[2].rank == 3
        
        # Test pagination with offset
        next_2 = await leaderboard_system.get_top_passengers(limit=2, offset=3)
        
        assert len(next_2) == 2
        assert next_2[0].passenger_id == "passenger_2"  # Score: 8
        assert next_2[0].rank == 4
        assert next_2[1].passenger_id == "passenger_4"  # Score: 6
        assert next_2[1].rank == 5
    
    @pytest.mark.asyncio
    async def test_get_passenger_rank(self, leaderboard_system):
        """Test individual passenger rank lookup using ZREVRANK."""
        # Add test passengers
        passengers = [
            ("passenger_1", 10),
            ("passenger_2", 8),
            ("passenger_3", 12),
        ]
        
        for passenger_id, score in passengers:
            await leaderboard_system.update_passenger_score(passenger_id, score)
        
        # Test ranks (1-based)
        rank_1 = await leaderboard_system.get_passenger_rank("passenger_3")  # Score: 12
        assert rank_1 == 1
        
        rank_2 = await leaderboard_system.get_passenger_rank("passenger_1")  # Score: 10
        assert rank_2 == 2
        
        rank_3 = await leaderboard_system.get_passenger_rank("passenger_2")  # Score: 8
        assert rank_3 == 3
        
        # Test non-existent passenger
        rank_none = await leaderboard_system.get_passenger_rank("nonexistent")
        assert rank_none is None
    
    @pytest.mark.asyncio
    async def test_get_passengers_in_range(self, leaderboard_system):
        """Test range queries for specific rank ranges."""
        # Add test passengers
        passengers = [
            ("passenger_1", 10),
            ("passenger_2", 8),
            ("passenger_3", 12),
            ("passenger_4", 6),
            ("passenger_5", 15),
        ]
        
        for passenger_id, score in passengers:
            await leaderboard_system.update_passenger_score(passenger_id, score)
        
        # Test range query (ranks 2-4)
        range_passengers = await leaderboard_system.get_passengers_in_range(2, 4)
        
        assert len(range_passengers) == 3
        assert range_passengers[0].rank == 2  # passenger_3 (score: 12)
        assert range_passengers[1].rank == 3  # passenger_1 (score: 10)
        assert range_passengers[2].rank == 4  # passenger_2 (score: 8)
    
    @pytest.mark.asyncio
    async def test_leaderboard_statistics(self, leaderboard_system):
        """Test leaderboard statistics generation."""
        # Add test data
        passengers = [
            ("passenger_1", 5),
            ("passenger_2", 10),
            ("passenger_3", 3),
        ]
        
        for passenger_id, score in passengers:
            await leaderboard_system.update_passenger_score(passenger_id, score)
        
        # Test statistics
        stats = await leaderboard_system.get_leaderboard_stats()
        
        assert stats is not None
        assert stats.total_passengers == 3
        assert stats.total_bookings == 18  # 5 + 10 + 3
        assert stats.top_score == 10
        assert stats.average_score == 6.0  # 18 / 3
        assert isinstance(stats.last_updated, datetime)
    
    @pytest.mark.asyncio
    async def test_reset_leaderboard(self, leaderboard_system):
        """Test leaderboard reset functionality."""
        # Add test data
        await leaderboard_system.update_passenger_score("passenger_1", 5)
        await leaderboard_system.update_passenger_score("passenger_2", 10)
        
        # Verify data exists
        stats_before = await leaderboard_system.get_leaderboard_stats()
        assert stats_before.total_passengers == 2
        
        # Test reset
        reset_success = await leaderboard_system.reset_leaderboard(archive=False)
        assert reset_success is True
        
        # Verify leaderboard is empty
        stats_after = await leaderboard_system.get_leaderboard_stats()
        assert stats_after.total_passengers == 0
        
        # Verify scores are gone
        score = await leaderboard_system.get_passenger_score("passenger_1")
        assert score is None
    
    @pytest.mark.asyncio
    async def test_memory_optimization(self, leaderboard_system):
        """Test memory optimization features."""
        # Add test data
        passengers = [
            ("passenger_1", 5),
            ("passenger_2", 0),  # Zero score passenger
            ("passenger_3", 10),
        ]
        
        for passenger_id, score in passengers:
            await leaderboard_system.update_passenger_score(
                passenger_id, 
                score, 
                {"name": f"Test {passenger_id}"}
            )
        
        # Test memory optimization
        optimization_results = await leaderboard_system.optimize_memory()
        
        assert "initial_memory_bytes" in optimization_results
        assert "final_memory_bytes" in optimization_results
        assert "memory_saved_bytes" in optimization_results
        assert "optimization_timestamp" in optimization_results
        assert optimization_results["initial_memory_bytes"] >= 0
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, leaderboard_system):
        """Test performance metrics tracking."""
        # Perform some operations to generate metrics
        await leaderboard_system.update_passenger_score("passenger_1", 5)
        await leaderboard_system.get_passenger_rank("passenger_1")
        await leaderboard_system.get_top_passengers(limit=5)
        
        # Get performance metrics
        metrics = await leaderboard_system.get_performance_metrics()
        
        assert "cache_hits" in metrics
        assert "cache_misses" in metrics
        assert "hit_ratio" in metrics
        assert "total_requests" in metrics
        assert "leaderboard_stats" in metrics
        assert "last_updated" in metrics
        
        # Verify metrics are reasonable
        assert metrics["cache_hits"] >= 0
        assert metrics["cache_misses"] >= 0
        assert 0 <= metrics["hit_ratio"] <= 1


# Simple test runner for manual execution
if __name__ == "__main__":
    async def run_basic_test():
        """Run a basic test to verify functionality."""
        print("Testing LeaderboardSystem...")
        
        # Create mock client and leaderboard
        mock_client = MockValkeyClient()
        leaderboard = LeaderboardSystem(mock_client, "test")
        
        try:
            # Test basic operations
            print("1. Testing score update...")
            success = await leaderboard.update_passenger_score(
                "test_passenger", 
                10, 
                {"name": "Test User", "firstname": "Test", "lastname": "User"}
            )
            assert success is True
            print("   ✓ Score update successful")
            
            print("2. Testing score increment...")
            new_score = await leaderboard.increment_passenger_score("test_passenger", 5)
            assert new_score == 15
            print(f"   ✓ Score incremented to {new_score}")
            
            print("3. Testing rank lookup...")
            rank = await leaderboard.get_passenger_rank("test_passenger")
            assert rank == 1
            print(f"   ✓ Passenger rank: {rank}")
            
            print("4. Testing top passengers...")
            top = await leaderboard.get_top_passengers(limit=5)
            assert len(top) == 1
            assert top[0].booking_count == 15
            print(f"   ✓ Top passengers: {len(top)} entries")
            
            print("5. Testing statistics...")
            stats = await leaderboard.get_leaderboard_stats()
            assert stats.total_passengers == 1
            assert stats.total_bookings == 15
            print(f"   ✓ Stats: {stats.total_passengers} passengers, {stats.total_bookings} bookings")
            
            print("\n✅ All tests passed!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            raise
    
    # Run the test
    asyncio.run(run_basic_test())


class TestAirportTrafficLeaderboard:
    """Test cases for the AirportTrafficLeaderboard implementation."""
    
    @pytest.fixture
    def mock_valkey_client(self):
        """Create a mock Valkey client."""
        return MockValkeyClient()
    
    @pytest.fixture
    def airport_leaderboard(self, mock_valkey_client):
        """Create an airport traffic leaderboard with mock client."""
        from airport.services.leaderboard import AirportTrafficLeaderboard
        return AirportTrafficLeaderboard(mock_valkey_client, "test_airport_traffic")
    
    @pytest.mark.asyncio
    async def test_update_airport_traffic(self, airport_leaderboard):
        """Test updating airport traffic counts."""
        # Test basic traffic update
        success = await airport_leaderboard.update_airport_traffic(
            "LAX", 
            inbound_count=100, 
            outbound_count=80,
            airport_info={"name": "Los Angeles International", "city": "Los Angeles", "country": "USA"}
        )
        
        assert success is True
        
        # Verify traffic was recorded
        top_airports = await airport_leaderboard.get_top_airports_by_traffic(limit=5)
        assert len(top_airports) == 1
        assert top_airports[0].airport_code == "LAX"
        assert top_airports[0].total_passengers == 180  # 100 + 80
        assert top_airports[0].inbound_passengers == 100
        assert top_airports[0].outbound_passengers == 80
        assert top_airports[0].rank == 1
    
    @pytest.mark.asyncio
    async def test_increment_airport_traffic(self, airport_leaderboard):
        """Test atomic airport traffic increments."""
        # Initial traffic
        result = await airport_leaderboard.increment_airport_traffic(
            "JFK", 
            inbound_increment=50, 
            outbound_increment=30,
            airport_info={"name": "John F. Kennedy International", "city": "New York"}
        )
        
        assert result is not None
        assert result["total"] == 80
        assert result["inbound"] == 50
        assert result["outbound"] == 30
        
        # Additional increment
        result = await airport_leaderboard.increment_airport_traffic(
            "JFK", 
            inbound_increment=20, 
            outbound_increment=10
        )
        
        assert result is not None
        assert result["total"] == 110  # 80 + 30
        assert result["inbound"] == 70  # 50 + 20
        assert result["outbound"] == 40  # 30 + 10
    
    @pytest.mark.asyncio
    async def test_airport_traffic_ranking(self, airport_leaderboard):
        """Test airport ranking by traffic."""
        # Add multiple airports
        airports = [
            ("LAX", 100, 80, {"name": "Los Angeles International"}),
            ("JFK", 120, 90, {"name": "John F. Kennedy International"}),
            ("ORD", 80, 70, {"name": "O'Hare International"}),
            ("ATL", 150, 140, {"name": "Hartsfield-Jackson Atlanta International"}),
        ]
        
        for airport_code, inbound, outbound, info in airports:
            await airport_leaderboard.update_airport_traffic(airport_code, inbound, outbound, info)
        
        # Test top airports (should be ordered by total traffic)
        top_airports = await airport_leaderboard.get_top_airports_by_traffic(limit=4)
        
        assert len(top_airports) == 4
        assert top_airports[0].airport_code == "ATL"  # 290 total
        assert top_airports[0].total_passengers == 290
        assert top_airports[0].rank == 1
        
        assert top_airports[1].airport_code == "JFK"  # 210 total
        assert top_airports[1].total_passengers == 210
        assert top_airports[1].rank == 2
        
        assert top_airports[2].airport_code == "LAX"  # 180 total
        assert top_airports[2].rank == 3
        
        assert top_airports[3].airport_code == "ORD"  # 150 total
        assert top_airports[3].rank == 4
        
        # Test individual airport rank
        rank = await airport_leaderboard.get_airport_rank("JFK")
        assert rank == 2


class TestPassengerMilesLeaderboard:
    """Test cases for the PassengerMilesLeaderboard implementation."""
    
    @pytest.fixture
    def mock_valkey_client(self):
        """Create a mock Valkey client."""
        return MockValkeyClient()
    
    @pytest.fixture
    def miles_leaderboard(self, mock_valkey_client):
        """Create a passenger miles leaderboard with mock client."""
        from airport.services.leaderboard import PassengerMilesLeaderboard
        return PassengerMilesLeaderboard(mock_valkey_client, "test_passenger_miles")
    
    @pytest.mark.asyncio
    async def test_add_flight_miles(self, miles_leaderboard):
        """Test adding flight miles to passengers."""
        # Test adding miles for first flight
        result = await miles_leaderboard.add_flight_miles(
            "passenger_1", 
            2500,
            {"name": "John Doe", "firstname": "John", "lastname": "Doe"}
        )
        
        assert result is not None
        assert result["total_miles"] == 2500
        assert result["total_flights"] == 1
        
        # Test adding miles for second flight
        result = await miles_leaderboard.add_flight_miles("passenger_1", 1800)
        
        assert result is not None
        assert result["total_miles"] == 4300  # 2500 + 1800
        assert result["total_flights"] == 2
    
    @pytest.mark.asyncio
    async def test_passenger_miles_ranking(self, miles_leaderboard):
        """Test passenger ranking by total miles."""
        # Add multiple passengers with different miles
        passengers = [
            ("passenger_1", [2500, 1800, 3200], {"name": "Alice Smith"}),  # Total: 7500, 3 flights
            ("passenger_2", [5000, 2200], {"name": "Bob Jones"}),          # Total: 7200, 2 flights
            ("passenger_3", [1200, 800, 1500, 2000], {"name": "Charlie Brown"}),  # Total: 5500, 4 flights
            ("passenger_4", [8000], {"name": "Diana Wilson"}),             # Total: 8000, 1 flight
        ]
        
        for passenger_id, flights, info in passengers:
            for miles in flights:
                await miles_leaderboard.add_flight_miles(passenger_id, miles, info)
        
        # Test top passengers by miles
        top_passengers = await miles_leaderboard.get_top_passengers_by_miles(limit=4)
        
        assert len(top_passengers) == 4
        assert top_passengers[0].passenger_id == "passenger_4"  # 8000 miles
        assert top_passengers[0].total_miles == 8000
        assert top_passengers[0].total_flights == 1
        assert top_passengers[0].average_miles_per_flight == 8000.0
        assert top_passengers[0].rank == 1
        
        assert top_passengers[1].passenger_id == "passenger_1"  # 7500 miles
        assert top_passengers[1].total_miles == 7500
        assert top_passengers[1].total_flights == 3
        assert top_passengers[1].average_miles_per_flight == 2500.0
        assert top_passengers[1].rank == 2
        
        assert top_passengers[2].passenger_id == "passenger_2"  # 7200 miles
        assert top_passengers[2].rank == 3
        
        assert top_passengers[3].passenger_id == "passenger_3"  # 5500 miles
        assert top_passengers[3].rank == 4
        
        # Test individual passenger rank
        rank = await miles_leaderboard.get_passenger_miles_rank("passenger_1")
        assert rank == 2
    
    @pytest.mark.asyncio
    async def test_passenger_miles_stats(self, miles_leaderboard):
        """Test comprehensive passenger miles statistics."""
        # Add flights for a passenger
        flights = [2500, 1800, 3200, 1500]
        for miles in flights:
            await miles_leaderboard.add_flight_miles(
                "test_passenger", 
                miles,
                {"name": "Test User", "firstname": "Test", "lastname": "User"}
            )
        
        # Get comprehensive stats
        stats = await miles_leaderboard.get_passenger_miles_stats("test_passenger")
        
        assert stats is not None
        assert stats["passenger_id"] == "test_passenger"
        assert stats["passenger_name"] == "Test User"
        assert stats["total_miles"] == 9000  # Sum of all flights
        assert stats["total_flights"] == 4
        assert stats["average_miles_per_flight"] == 2250.0  # 9000 / 4
        assert stats["rank"] == 1  # Only passenger in this test


class TestMultiLeaderboardManager:
    """Test cases for the MultiLeaderboardManager implementation."""
    
    @pytest.fixture
    def mock_valkey_client(self):
        """Create a mock Valkey client."""
        return MockValkeyClient()
    
    @pytest.fixture
    def multi_manager(self, mock_valkey_client):
        """Create a multi-leaderboard manager with mock client."""
        from airport.services.leaderboard import MultiLeaderboardManager
        return MultiLeaderboardManager(mock_valkey_client)
    
    @pytest.mark.asyncio
    async def test_comprehensive_performance_report(self, multi_manager):
        """Test comprehensive performance reporting across all leaderboards."""
        # Add some data to generate performance metrics
        await multi_manager.passenger_bookings.update_passenger_score("passenger_1", 5)
        await multi_manager.airport_traffic.update_airport_traffic("LAX", 100, 80)
        await multi_manager.passenger_miles.add_flight_miles("passenger_1", 2500)
        
        # Generate performance report
        report = await multi_manager.get_comprehensive_performance_report()
        
        assert "report_timestamp" in report
        assert "total_operations_measured" in report
        assert "operation_summaries" in report
        assert "leaderboard_stats" in report
        assert "overall_performance" in report
        
        # Verify structure
        assert isinstance(report["total_operations_measured"], int)
        assert isinstance(report["operation_summaries"], dict)
        assert "passenger_bookings" in report["leaderboard_stats"]


# Enhanced test runner for manual execution
if __name__ == "__main__":
    async def run_enhanced_tests():
        """Run enhanced tests including new leaderboard types."""
        print("Testing Enhanced Leaderboard System...")
        
        # Create mock client
        mock_client = MockValkeyClient()
        
        try:
            # Test airport traffic leaderboard
            print("\n1. Testing Airport Traffic Leaderboard...")
            from airport.services.leaderboard import AirportTrafficLeaderboard
            airport_lb = AirportTrafficLeaderboard(mock_client, "test_airport")
            
            success = await airport_lb.update_airport_traffic(
                "LAX", 100, 80, 
                {"name": "Los Angeles International", "city": "Los Angeles"}
            )
            assert success is True
            print("   ✓ Airport traffic update successful")
            
            top_airports = await airport_lb.get_top_airports_by_traffic(limit=5)
            assert len(top_airports) == 1
            assert top_airports[0].total_passengers == 180
            print(f"   ✓ Top airports query: {top_airports[0].airport_name} with {top_airports[0].total_passengers} passengers")
            
            # Test passenger miles leaderboard
            print("\n2. Testing Passenger Miles Leaderboard...")
            from airport.services.leaderboard import PassengerMilesLeaderboard
            miles_lb = PassengerMilesLeaderboard(mock_client, "test_miles")
            
            result = await miles_lb.add_flight_miles(
                "passenger_1", 2500,
                {"name": "John Doe", "firstname": "John", "lastname": "Doe"}
            )
            assert result["total_miles"] == 2500
            assert result["total_flights"] == 1
            print(f"   ✓ Flight miles added: {result['total_miles']} miles, {result['total_flights']} flights")
            
            top_passengers = await miles_lb.get_top_passengers_by_miles(limit=5)
            assert len(top_passengers) == 1
            assert top_passengers[0].total_miles == 2500
            print(f"   ✓ Top passengers by miles: {top_passengers[0].passenger_name} with {top_passengers[0].total_miles} miles")
            
            # Test multi-leaderboard manager
            print("\n3. Testing Multi-Leaderboard Manager...")
            from airport.services.leaderboard import MultiLeaderboardManager
            manager = MultiLeaderboardManager(mock_client)
            
            # Add some test data
            await manager.passenger_bookings.update_passenger_score("passenger_1", 5)
            await manager.airport_traffic.update_airport_traffic("JFK", 120, 90)
            await manager.passenger_miles.add_flight_miles("passenger_2", 3000)
            
            report = await manager.get_comprehensive_performance_report()
            assert "report_timestamp" in report
            print("   ✓ Comprehensive performance report generated")
            
            print("\n✅ All enhanced tests passed!")
            print(f"   - Airport traffic leaderboard: functional")
            print(f"   - Passenger miles leaderboard: functional")
            print(f"   - Multi-leaderboard manager: functional")
            print(f"   - Performance monitoring: active")
            
        except Exception as e:
            print(f"\n❌ Enhanced test failed: {e}")
            raise
    
    # Run the enhanced tests
    asyncio.run(run_enhanced_tests())