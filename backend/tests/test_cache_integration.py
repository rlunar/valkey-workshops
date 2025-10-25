"""
Integration tests for the Valkey cache system.

Tests the complete cache setup including configuration, client connection,
manager operations, error handling, and graceful degradation.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from airport.cache import (
    ValkeyConfig,
    ValkeyClient,
    CacheManager,
    CacheKeyPrefix,
    TTLPreset,
    CacheKeyBuilder,
    TTLCalculator,
    CacheKeyManager,
    key_manager,
    get_cache_manager,
    close_global_cache_manager
)
from airport.cache.config import ValkeyConnectionError, ValkeyTimeoutError


@pytest.fixture
def valkey_config():
    """Create a test Valkey configuration."""
    return ValkeyConfig(
        host="localhost",
        port=6379,
        database=15,  # Use test database
        password=None,
        max_connections=5,
        socket_timeout=2.0,
        socket_connect_timeout=2.0
    )


@pytest.fixture
async def mock_valkey_client():
    """Create a mock Valkey client for testing without actual Redis."""
    mock_client = Mock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.setex = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.exists = AsyncMock(return_value=1)
    mock_client.ttl = AsyncMock(return_value=300)
    mock_client.info = AsyncMock(return_value={
        "redis_version": "7.0.0",
        "connected_clients": 1,
        "used_memory_human": "1M",
        "uptime_in_seconds": 3600
    })
    mock_client.scan_iter = AsyncMock(return_value=iter(["test:key:1", "test:key:2"]))
    return mock_client


@pytest.fixture
async def cache_manager_with_mock(mock_valkey_client):
    """Create a cache manager with mocked Valkey client."""
    config = ValkeyConfig(host="localhost", port=6379, database=15)
    
    # Create a real ValkeyClient but mock its internal client
    valkey_client = ValkeyClient(config)
    valkey_client._client = mock_valkey_client
    valkey_client._is_connected = True
    
    cache_manager = CacheManager(client=valkey_client, enable_fallback=True)
    await cache_manager.initialize()
    
    yield cache_manager
    
    await cache_manager.close()


@pytest.fixture
async def fallback_cache_manager():
    """Create a cache manager with fallback enabled but no client."""
    cache_manager = CacheManager(client=None, enable_fallback=True)
    await cache_manager.initialize()
    
    yield cache_manager
    
    await cache_manager.close()


class TestValkeyConfig:
    """Test Valkey configuration functionality."""
    
    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        config = ValkeyConfig()
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.database == 0
        assert config.max_connections == 10
        assert config.socket_timeout == 5.0
    
    def test_config_from_env(self):
        """Test creating config from environment variables."""
        with patch.dict('os.environ', {
            'VALKEY_HOST': 'test-host',
            'VALKEY_PORT': '6380',
            'VALKEY_PASSWORD': 'test-pass',
            'VALKEY_DATABASE': '5',
            'VALKEY_MAX_CONNECTIONS': '20'
        }):
            config = ValkeyConfig.from_env()
            assert config.host == "test-host"
            assert config.port == 6380
            assert config.password == "test-pass"
            assert config.database == 5
            assert config.max_connections == 20
    
    def test_config_to_connection_kwargs(self):
        """Test converting config to connection parameters."""
        config = ValkeyConfig(
            host="test-host",
            port=6380,
            password="test-pass",
            database=5
        )
        
        kwargs = config.to_connection_kwargs()
        assert kwargs["host"] == "test-host"
        assert kwargs["port"] == 6380
        assert kwargs["password"] == "test-pass"
        assert kwargs["db"] == 5
        assert "max_connections" not in kwargs  # Only in pool kwargs
    
    def test_config_to_connection_pool_kwargs(self):
        """Test converting config to connection pool parameters."""
        config = ValkeyConfig(max_connections=15)
        kwargs = config.to_connection_pool_kwargs()
        assert kwargs["max_connections"] == 15
    
    def test_config_string_representation(self):
        """Test config string representation hides password."""
        config = ValkeyConfig(password="secret123")
        config_str = str(config)
        assert "secret123" not in config_str
        assert "***" in config_str


class TestCacheKeyBuilder:
    """Test cache key building utilities."""
    
    def test_build_basic_key(self):
        """Test building basic cache keys."""
        key = CacheKeyBuilder.build_key(CacheKeyPrefix.FLIGHT_STATUS, "AA123")
        assert key == "flight:status:AA123"
    
    def test_build_key_with_multiple_parts(self):
        """Test building keys with multiple parts."""
        key = CacheKeyBuilder.build_key(
            CacheKeyPrefix.FLIGHT_SEARCH, 
            "LAX", 
            "JFK", 
            "2024-01-15"
        )
        assert key == "flight:search:LAX:JFK:2024-01-15"
    
    def test_build_key_with_parameters(self):
        """Test building keys with keyword parameters."""
        key = CacheKeyBuilder.build_key(
            CacheKeyPrefix.FLIGHT_SEARCH,
            "LAX",
            "JFK",
            date="2024-01-15",
            passengers=2
        )
        assert "date=2024-01-15" in key
        assert "passengers=2" in key
    
    def test_build_hash_key(self):
        """Test building hash-based keys."""
        data = {"from": "LAX", "to": "JFK", "date": "2024-01-15"}
        key = CacheKeyBuilder.build_hash_key(CacheKeyPrefix.FLIGHT_SEARCH, data)
        
        assert key.startswith("flight:search:hash:")
        assert len(key.split(":")[-1]) == 12  # MD5 hash truncated to 12 chars
    
    def test_build_pattern(self):
        """Test building key patterns for scanning."""
        pattern = CacheKeyBuilder.build_pattern(CacheKeyPrefix.FLIGHT_STATUS, "*")
        assert pattern == "flight:status:*"


class TestTTLCalculator:
    """Test TTL calculation utilities."""
    
    def test_calculate_ttl_with_jitter(self):
        """Test TTL calculation with jitter."""
        base_ttl = 3600
        jitter_percent = 0.1
        
        # Run multiple times to test randomness
        ttls = []
        for _ in range(10):
            ttl = TTLCalculator.calculate_ttl_with_jitter(base_ttl, jitter_percent)
            ttls.append(ttl)
        
        # All TTLs should be within jitter range
        min_expected = base_ttl - (base_ttl * jitter_percent)
        max_expected = base_ttl + (base_ttl * jitter_percent)
        
        for ttl in ttls:
            assert min_expected <= ttl <= max_expected
            assert ttl >= 30  # Minimum TTL
    
    def test_calculate_ttl_with_preset(self):
        """Test TTL calculation with preset values."""
        ttl = TTLCalculator.calculate_ttl_with_jitter(TTLPreset.FLIGHT_STATUS)
        assert 270 <= ttl <= 330  # 300 ± 10%
    
    def test_calculate_expiration_time(self):
        """Test expiration time calculation."""
        ttl_seconds = 3600
        expiration = TTLCalculator.calculate_expiration_time(ttl_seconds)
        
        expected_time = datetime.now() + timedelta(seconds=ttl_seconds)
        # Allow 1 second tolerance for test execution time
        assert abs((expiration - expected_time).total_seconds()) < 1
    
    def test_get_remaining_ttl(self):
        """Test remaining TTL calculation."""
        future_time = datetime.now() + timedelta(seconds=300)
        remaining = TTLCalculator.get_remaining_ttl(future_time)
        assert 299 <= remaining <= 300
        
        # Test expired time
        past_time = datetime.now() - timedelta(seconds=100)
        remaining = TTLCalculator.get_remaining_ttl(past_time)
        assert remaining == 0


class TestCacheKeyManager:
    """Test high-level cache key management."""
    
    def test_flight_search_key(self):
        """Test flight search key generation."""
        key = key_manager.flight_search_key(
            "LAX", "JFK", "2024-01-15",
            passengers=2, class_preference="economy"
        )
        assert key.startswith("flight:search:")
        assert "LAX" in key
        assert "JFK" in key
        assert "2024-01-15" in key
    
    def test_seat_reservation_keys(self):
        """Test seat reservation key generation."""
        flight_id = "AA123_20240115"
        seat_number = 12
        user_id = "user_456"
        
        seat_map_key = key_manager.seat_map_key(flight_id)
        reservation_key = key_manager.seat_reservation_key(flight_id, seat_number)
        lock_key = key_manager.seat_lock_key(flight_id, seat_number, user_id)
        
        assert seat_map_key == f"seat:map:{flight_id}"
        assert reservation_key == f"seat:reservation:{flight_id}:{seat_number}"
        assert lock_key == f"seat:lock:{flight_id}:{seat_number}:{user_id}"
    
    def test_key_validation(self):
        """Test cache key validation."""
        # Valid keys
        assert key_manager.validate_key("valid:key:123")
        assert key_manager.validate_key("flight:status:AA123")
        
        # Invalid keys
        assert not key_manager.validate_key("")
        assert not key_manager.validate_key(None)
        assert not key_manager.validate_key("key with spaces")
        assert not key_manager.validate_key("key\nwith\nnewlines")
        assert not key_manager.validate_key("x" * 300)  # Too long
    
    def test_key_info_extraction(self):
        """Test extracting information from cache keys."""
        key = "flight:status:AA123"
        info = key_manager.get_key_info(key)
        
        assert info["key"] == key
        assert info["prefix"] == "flight"
        assert info["type"] == "flight:status"
        assert info["is_valid"] is True
        assert len(info["parts"]) == 3


class TestCacheManagerBasicOperations:
    """Test basic cache manager operations."""
    
    @pytest.mark.asyncio
    async def test_set_and_get_operations(self, cache_manager_with_mock):
        """Test basic set and get operations."""
        cache = cache_manager_with_mock
        
        # Mock the get operation to return our test data
        test_data = {"user_id": 123, "name": "John Doe"}
        cache.client.client.get.return_value = json.dumps(test_data)
        
        # Test set operation
        success = await cache.set("test:user:123", test_data, ttl=300)
        assert success is True
        
        # Verify set was called with correct parameters
        cache.client.client.setex.assert_called_once()
        
        # Test get operation
        retrieved = await cache.get("test:user:123")
        assert retrieved == test_data
    
    @pytest.mark.asyncio
    async def test_delete_operation(self, cache_manager_with_mock):
        """Test delete operation."""
        cache = cache_manager_with_mock
        
        success = await cache.delete("test:key")
        assert success is True
        
        cache.client.client.delete.assert_called_once_with("test:key")
    
    @pytest.mark.asyncio
    async def test_exists_operation(self, cache_manager_with_mock):
        """Test exists operation."""
        cache = cache_manager_with_mock
        
        exists = await cache.exists("test:key")
        assert exists is True
        
        cache.client.client.exists.assert_called_once_with("test:key")
    
    @pytest.mark.asyncio
    async def test_get_ttl_operation(self, cache_manager_with_mock):
        """Test TTL retrieval."""
        cache = cache_manager_with_mock
        
        ttl = await cache.get_ttl("test:key")
        assert ttl == 300
        
        cache.client.client.ttl.assert_called_once_with("test:key")
    
    @pytest.mark.asyncio
    async def test_ttl_with_jitter(self, cache_manager_with_mock):
        """Test TTL calculation with jitter."""
        cache = cache_manager_with_mock
        
        # Set with jitter enabled (default)
        await cache.set("test:key", "value", ttl=3600, jitter=True)
        
        # Verify setex was called (TTL should be close to 3600 but with jitter)
        cache.client.client.setex.assert_called_once()
        call_args = cache.client.client.setex.call_args
        ttl_used = call_args[0][1]  # Second argument is TTL
        
        # TTL should be within jitter range (3600 ± 10%)
        assert 3240 <= ttl_used <= 3960


class TestCacheManagerErrorHandling:
    """Test cache manager error handling and graceful degradation."""
    
    @pytest.mark.asyncio
    async def test_fallback_operations(self, fallback_cache_manager):
        """Test fallback cache operations when Valkey is unavailable."""
        cache = fallback_cache_manager
        
        # Test set operation with fallback
        success = await cache.set("fallback:key", {"data": "test"}, ttl=300)
        assert success is True
        
        # Test get operation with fallback
        retrieved = await cache.get("fallback:key")
        assert retrieved == {"data": "test"}
        
        # Test exists with fallback
        exists = await cache.exists("fallback:key")
        assert exists is True
        
        # Test delete with fallback
        deleted = await cache.delete("fallback:key")
        assert deleted is True
        
        # Verify key is gone
        exists_after_delete = await cache.exists("fallback:key")
        assert exists_after_delete is False
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, cache_manager_with_mock):
        """Test circuit breaker pattern."""
        cache = cache_manager_with_mock
        cache.circuit_breaker_threshold = 3  # Lower threshold for testing
        
        # Mock client to raise connection errors
        from valkey.exceptions import ConnectionError
        cache.client.client.get.side_effect = ConnectionError("Connection failed")
        
        # Trigger circuit breaker by causing consecutive failures
        for i in range(5):
            result = await cache.get(f"test:key:{i}")
            assert result is None  # Should return None due to error
        
        # Circuit breaker should now be open
        assert cache.is_circuit_open is True
        assert cache.consecutive_failures >= cache.circuit_breaker_threshold
        
        # Next operation should use fallback without trying cache
        result = await cache.get("test:key:fallback")
        assert result is None  # No fallback data available
        
        # Stats should reflect degraded operations
        stats = await cache.get_stats()
        assert stats["degraded_operations"] > 0
    
    @pytest.mark.asyncio
    async def test_error_categorization(self, cache_manager_with_mock):
        """Test that different error types are categorized correctly."""
        cache = cache_manager_with_mock
        
        from valkey.exceptions import ConnectionError, TimeoutError, ResponseError
        
        # Test connection error
        cache.client.client.get.side_effect = ConnectionError("Connection failed")
        await cache.get("test:key")
        
        # Test timeout error
        cache.client.client.get.side_effect = TimeoutError("Timeout")
        await cache.get("test:key")
        
        # Test response error
        cache.client.client.get.side_effect = ResponseError("Invalid response")
        await cache.get("test:key")
        
        stats = await cache.get_stats()
        assert stats["connection_errors"] >= 1
        assert stats["timeout_errors"] >= 1
        assert stats["other_errors"] >= 1
    
    @pytest.mark.asyncio
    async def test_fallback_cache_expiration(self, fallback_cache_manager):
        """Test that fallback cache respects TTL."""
        cache = fallback_cache_manager
        
        # Set with short TTL
        await cache.set("expire:key", "test_value", ttl=1)
        
        # Should exist immediately
        assert await cache.exists("expire:key")
        assert await cache.get("expire:key") == "test_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired now
        assert await cache.get("expire:key") is None
        assert not await cache.exists("expire:key")


class TestCacheManagerAdvancedFeatures:
    """Test advanced cache manager features."""
    
    @pytest.mark.asyncio
    async def test_pattern_clearing(self, cache_manager_with_mock):
        """Test clearing keys by pattern."""
        cache = cache_manager_with_mock
        
        # Mock scan_iter to return test keys
        test_keys = ["test:key:1", "test:key:2", "test:other:3"]
        cache.client.client.scan_iter.return_value = iter(test_keys)
        cache.client.client.delete.return_value = len(test_keys)
        
        deleted_count = await cache.clear_pattern("test:key:*")
        assert deleted_count == len(test_keys)
        
        # Verify scan was called with correct pattern
        cache.client.client.scan_iter.assert_called_with(match="test:key:*")
    
    @pytest.mark.asyncio
    async def test_statistics_collection(self, cache_manager_with_mock):
        """Test statistics collection and reporting."""
        cache = cache_manager_with_mock
        
        # Perform various operations to generate stats
        cache.client.client.get.return_value = json.dumps({"test": "data"})
        
        await cache.set("stats:key:1", "value1")
        await cache.get("stats:key:1")  # Hit
        await cache.get("stats:key:missing")  # Miss (returns None)
        await cache.delete("stats:key:1")
        
        stats = await cache.get_stats()
        
        assert stats["set_count"] >= 1
        assert stats["hit_count"] >= 1
        assert stats["delete_count"] >= 1
        assert stats["total_operations"] >= 3
        assert 0 <= stats["hit_ratio"] <= 1
        assert stats["uptime_seconds"] > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, cache_manager_with_mock):
        """Test comprehensive health check."""
        cache = cache_manager_with_mock
        
        # Mock successful operations for health check
        cache.client.client.get.return_value = json.dumps({"timestamp": "test"})
        
        health = await cache.health_check()
        
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "cache_available" in health
        assert "circuit_breaker_open" in health
        assert isinstance(health["errors"], list)
    
    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, cache_manager_with_mock):
        """Test transaction context manager."""
        cache = cache_manager_with_mock
        
        async with cache.transaction():
            await cache.set("transaction:key", "value")
            result = await cache.get("transaction:key")
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_connection_info_retrieval(self, cache_manager_with_mock):
        """Test connection information retrieval."""
        cache = cache_manager_with_mock
        
        stats = await cache.get_stats()
        
        assert "connection_info" in stats
        connection_info = stats["connection_info"]
        assert "is_connected" in connection_info
        assert "server_version" in connection_info


class TestCacheIntegrationScenarios:
    """Test realistic cache integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_flight_search_caching_scenario(self, cache_manager_with_mock):
        """Test complete flight search caching scenario."""
        cache = cache_manager_with_mock
        
        # Simulate flight search
        search_params = {
            "from_airport": "LAX",
            "to_airport": "JFK",
            "departure_date": "2024-01-15",
            "passengers": 2
        }
        
        search_key = key_manager.flight_search_key(**search_params)
        
        # Simulate expensive search results
        search_results = {
            "flights": [
                {
                    "flight_number": "AA123",
                    "departure": "2024-01-15T08:00:00",
                    "arrival": "2024-01-15T16:30:00",
                    "price": 299.99
                }
            ],
            "search_time": datetime.now().isoformat(),
            "total_results": 1
        }
        
        # Cache search results
        success = await cache.set(search_key, search_results, ttl=TTLPreset.SEARCH_RESULTS)
        assert success is True
        
        # Mock get to return our cached data
        cache.client.client.get.return_value = json.dumps(search_results)
        
        # Retrieve cached results
        cached_results = await cache.get(search_key)
        assert cached_results["total_results"] == 1
        assert len(cached_results["flights"]) == 1
    
    @pytest.mark.asyncio
    async def test_seat_reservation_locking_scenario(self, cache_manager_with_mock):
        """Test seat reservation with distributed locking."""
        cache = cache_manager_with_mock
        
        flight_id = "AA123_20240115"
        seat_number = 12
        user_id = "user_456"
        
        # Generate reservation keys
        reservation_key = key_manager.seat_reservation_key(flight_id, seat_number)
        lock_key = key_manager.seat_lock_key(flight_id, seat_number, user_id)
        
        # Create seat reservation
        reservation_data = {
            "user_id": user_id,
            "seat_number": seat_number,
            "reserved_at": datetime.now().isoformat(),
            "flight_id": flight_id
        }
        
        # Set reservation with short TTL (seat hold time)
        await cache.set(reservation_key, reservation_data, ttl=TTLPreset.SEAT_RESERVATION)
        await cache.set(lock_key, "locked", ttl=TTLPreset.SEAT_RESERVATION)
        
        # Verify reservation exists
        assert await cache.exists(reservation_key)
        assert await cache.exists(lock_key)
        
        # Check TTL
        ttl = await cache.get_ttl(reservation_key)
        assert ttl is not None
        assert ttl <= TTLPreset.SEAT_RESERVATION
    
    @pytest.mark.asyncio
    async def test_weather_api_caching_scenario(self, cache_manager_with_mock):
        """Test external API result caching."""
        cache = cache_manager_with_mock
        
        # Weather API caching
        weather_key = key_manager.weather_key("US", "Los Angeles")
        
        weather_data = {
            "temperature": 72,
            "condition": "sunny",
            "humidity": 45,
            "cached_at": datetime.now().isoformat()
        }
        
        # Cache weather data
        await cache.set(weather_key, weather_data, ttl=TTLPreset.WEATHER_DATA)
        
        # Mock get to return cached weather
        cache.client.client.get.return_value = json.dumps(weather_data)
        
        # Retrieve cached weather
        cached_weather = await cache.get(weather_key)
        assert cached_weather["temperature"] == 72
        assert cached_weather["condition"] == "sunny"
    
    @pytest.mark.asyncio
    async def test_leaderboard_caching_scenario(self, cache_manager_with_mock):
        """Test leaderboard caching scenario."""
        cache = cache_manager_with_mock
        
        # Leaderboard caching
        leaderboard_key = key_manager.leaderboard_key("passenger_bookings")
        
        leaderboard_data = {
            "top_passengers": [
                {"passenger_id": 1, "bookings": 15, "name": "John Doe"},
                {"passenger_id": 2, "bookings": 12, "name": "Jane Smith"},
                {"passenger_id": 3, "bookings": 10, "name": "Bob Wilson"}
            ],
            "last_updated": datetime.now().isoformat(),
            "total_passengers": 150
        }
        
        # Cache leaderboard
        await cache.set(leaderboard_key, leaderboard_data, ttl=TTLPreset.LEADERBOARD)
        
        # Individual passenger scores
        for passenger in leaderboard_data["top_passengers"]:
            score_key = key_manager.passenger_score_key(passenger["passenger_id"])
            await cache.set(score_key, passenger["bookings"], ttl=TTLPreset.LEADERBOARD)
        
        # Mock get to return leaderboard
        cache.client.client.get.return_value = json.dumps(leaderboard_data)
        
        # Retrieve cached leaderboard
        cached_leaderboard = await cache.get(leaderboard_key)
        assert len(cached_leaderboard["top_passengers"]) == 3
        assert cached_leaderboard["total_passengers"] == 150


class TestGlobalCacheManager:
    """Test global cache manager functionality."""
    
    @pytest.mark.asyncio
    async def test_global_cache_manager_singleton(self):
        """Test that global cache manager works as singleton."""
        # Clean up any existing global manager
        await close_global_cache_manager()
        
        # Create mock config for testing
        config = ValkeyConfig(host="localhost", port=6379, database=15)
        
        # Get global manager twice
        manager1 = await get_cache_manager(config=config)
        manager2 = await get_cache_manager(config=config)
        
        # Should be the same instance
        assert manager1 is manager2
        
        # Clean up
        await close_global_cache_manager()
    
    @pytest.mark.asyncio
    async def test_global_cache_manager_cleanup(self):
        """Test global cache manager cleanup."""
        config = ValkeyConfig(host="localhost", port=6379, database=15)
        
        # Get global manager
        manager = await get_cache_manager(config=config)
        assert manager is not None
        
        # Close global manager
        await close_global_cache_manager()
        
        # Getting manager again should create new instance
        new_manager = await get_cache_manager(config=config)
        assert new_manager is not manager
        
        # Clean up
        await close_global_cache_manager()


@pytest.mark.asyncio
async def test_complete_cache_workflow():
    """Test a complete cache workflow from configuration to operations."""
    # Create configuration
    config = ValkeyConfig(
        host="localhost",
        port=6379,
        database=15,
        max_connections=5
    )
    
    # Create cache manager with fallback enabled
    cache_manager = CacheManager(config=config, enable_fallback=True)
    await cache_manager.initialize()
    
    try:
        # Test basic operations (will use fallback if Valkey not available)
        test_key = "workflow:test"
        test_data = {
            "message": "Complete workflow test",
            "timestamp": datetime.now().isoformat()
        }
        
        # Set data
        success = await cache_manager.set(test_key, test_data, ttl=300)
        assert success is True
        
        # Get data
        retrieved = await cache_manager.get(test_key)
        assert retrieved is not None
        
        # Check existence
        exists = await cache_manager.exists(test_key)
        assert exists is True
        
        # Get statistics
        stats = await cache_manager.get_stats()
        assert stats["total_operations"] > 0
        
        # Health check
        health = await cache_manager.health_check()
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        
        # Clean up test data
        await cache_manager.delete(test_key)
        
    finally:
        await cache_manager.close()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])