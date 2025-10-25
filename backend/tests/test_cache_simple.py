"""
Simple cache integration tests without async dependencies.

Tests the basic cache utilities, configuration, and key management
without requiring a running Valkey instance or async test support.
"""

import pytest
import os
from unittest.mock import patch
from datetime import datetime, timedelta

from airport.cache import (
    ValkeyConfig,
    CacheKeyPrefix,
    TTLPreset,
    CacheKeyBuilder,
    TTLCalculator,
    CacheKeyManager,
    key_manager
)


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


class TestCacheKeyPrefix:
    """Test cache key prefix enum."""
    
    def test_prefix_values(self):
        """Test that prefix values are correct."""
        assert CacheKeyPrefix.FLIGHT_STATUS == "flight:status"
        assert CacheKeyPrefix.FLIGHT_SEARCH == "flight:search"
        assert CacheKeyPrefix.SEAT_MAP == "seat:map"
        assert CacheKeyPrefix.WEATHER_CITY == "weather:city"
        assert CacheKeyPrefix.LEADERBOARD == "leaderboard"


class TestTTLPreset:
    """Test TTL preset enum."""
    
    def test_ttl_values(self):
        """Test that TTL values are correct."""
        assert TTLPreset.NEAR_REAL_TIME == 30
        assert TTLPreset.FLIGHT_STATUS == 300
        assert TTLPreset.SEAT_RESERVATION == 60
        assert TTLPreset.WEATHER_DATA == 900
        assert TTLPreset.SEARCH_RESULTS == 3600
        assert TTLPreset.FLIGHT_SCHEDULE == 21600
        assert TTLPreset.AIRPORT_INFO == 86400


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
        assert "flight:search:LAX:JFK" in key
        assert "date=2024-01-15" in key
        assert "passengers=2" in key
    
    def test_build_key_with_none_values(self):
        """Test building keys ignores None values."""
        key = CacheKeyBuilder.build_key(
            CacheKeyPrefix.FLIGHT_STATUS,
            "AA123",
            None,
            "active",
            test_param=None,
            valid_param="value"
        )
        assert key == "flight:status:AA123:active:valid_param=value"
    
    def test_build_hash_key(self):
        """Test building hash-based keys."""
        data = {"from": "LAX", "to": "JFK", "date": "2024-01-15"}
        key = CacheKeyBuilder.build_hash_key(CacheKeyPrefix.FLIGHT_SEARCH, data)
        
        assert key.startswith("flight:search:hash:")
        assert len(key.split(":")[-1]) == 12  # MD5 hash truncated to 12 chars
        
        # Same data should produce same hash
        key2 = CacheKeyBuilder.build_hash_key(CacheKeyPrefix.FLIGHT_SEARCH, data)
        assert key == key2
        
        # Different data should produce different hash
        data2 = {"from": "SFO", "to": "NYC", "date": "2024-01-16"}
        key3 = CacheKeyBuilder.build_hash_key(CacheKeyPrefix.FLIGHT_SEARCH, data2)
        assert key != key3
    
    def test_build_pattern(self):
        """Test building key patterns for scanning."""
        pattern = CacheKeyBuilder.build_pattern(CacheKeyPrefix.FLIGHT_STATUS, "*")
        assert pattern == "flight:status:*"
        
        pattern2 = CacheKeyBuilder.build_pattern(CacheKeyPrefix.SEAT_MAP, "AA*", "*")
        assert pattern2 == "seat:map:AA*:*"


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
        
        # Should have some variation
        assert len(set(ttls)) > 1  # Not all the same value
    
    def test_calculate_ttl_with_preset(self):
        """Test TTL calculation with preset values."""
        ttl = TTLCalculator.calculate_ttl_with_jitter(TTLPreset.FLIGHT_STATUS)
        assert 270 <= ttl <= 330  # 300 ± 10%
    
    def test_calculate_ttl_minimum_enforcement(self):
        """Test that minimum TTL is enforced."""
        # Very small base TTL with large negative jitter
        ttl = TTLCalculator.calculate_ttl_with_jitter(10, 0.9, min_ttl=30)
        assert ttl >= 30
    
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
    
    def test_calculate_ttl_milliseconds(self):
        """Test TTL calculation in milliseconds."""
        base_ttl_seconds = 60
        jitter_ms = 1000
        
        ttl_ms = TTLCalculator.calculate_ttl_milliseconds(base_ttl_seconds, jitter_ms)
        
        # Should be around 60000ms ± 1000ms
        assert 59000 <= ttl_ms <= 61000
        assert ttl_ms >= 1000  # Minimum 1 second


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
        assert "passengers=2" in key
        assert "class_preference=economy" in key
    
    def test_flight_status_key(self):
        """Test flight status key generation."""
        key = key_manager.flight_status_key("AA123")
        assert key == "flight:status:AA123"
        
        key2 = key_manager.flight_status_key(456)
        assert key2 == "flight:status:456"
    
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
    
    def test_weather_key(self):
        """Test weather key generation."""
        key = key_manager.weather_key("US", "Los Angeles")
        assert key == "weather:city:US:Los Angeles"
    
    def test_leaderboard_keys(self):
        """Test leaderboard key generation."""
        leaderboard_key = key_manager.leaderboard_key("passenger_bookings")
        assert leaderboard_key == "leaderboard:passenger_bookings"
        
        # Default leaderboard
        default_key = key_manager.leaderboard_key()
        assert default_key == "leaderboard:passenger_bookings"
        
        passenger_score_key = key_manager.passenger_score_key(123)
        assert passenger_score_key == "passenger:score:123"
    
    def test_russian_doll_key(self):
        """Test Russian doll caching key generation."""
        key = key_manager.russian_doll_key("flights", "AA123", "manifest")
        assert key == "nested:flights:AA123:manifest"
    
    def test_dependency_key(self):
        """Test dependency tracking key generation."""
        parent_key = "flight:manifest:AA123"
        child_key = "passenger:info:456"
        
        dep_key = key_manager.dependency_key(parent_key, child_key)
        assert dep_key.startswith("dependency:")
        
        # Should be deterministic
        dep_key2 = key_manager.dependency_key(parent_key, child_key)
        assert dep_key == dep_key2
    
    def test_key_validation(self):
        """Test cache key validation."""
        # Valid keys
        assert key_manager.validate_key("valid:key:123")
        assert key_manager.validate_key("flight:status:AA123")
        assert key_manager.validate_key("a" * 250)  # Max length
        
        # Invalid keys
        assert not key_manager.validate_key("")
        assert not key_manager.validate_key(None)
        assert not key_manager.validate_key("key with spaces")
        assert not key_manager.validate_key("key\nwith\nnewlines")
        assert not key_manager.validate_key("key\twith\ttabs")
        assert not key_manager.validate_key("key\rwith\rreturns")
        assert not key_manager.validate_key("x" * 251)  # Too long
    
    def test_key_info_extraction(self):
        """Test extracting information from cache keys."""
        key = "flight:status:AA123"
        info = key_manager.get_key_info(key)
        
        assert info["key"] == key
        assert info["prefix"] == "flight"
        assert info["type"] == "flight:status"
        assert info["is_valid"] is True
        assert info["parts"] == ["flight", "status", "AA123"]
        assert info["length"] == len(key)
        
        # Test invalid key
        invalid_key = "invalid key with spaces"
        invalid_info = key_manager.get_key_info(invalid_key)
        assert invalid_info["is_valid"] is False
    
    def test_key_consistency(self):
        """Test that key generation is consistent."""
        # Same parameters should generate same keys
        key1 = key_manager.flight_search_key("LAX", "JFK", "2024-01-15", passengers=2)
        key2 = key_manager.flight_search_key("LAX", "JFK", "2024-01-15", passengers=2)
        assert key1 == key2
        
        # Different parameters should generate different keys
        key3 = key_manager.flight_search_key("LAX", "JFK", "2024-01-16", passengers=2)
        assert key1 != key3


class TestCacheUtilitiesIntegration:
    """Test integration between different cache utilities."""
    
    def test_key_builder_with_ttl_calculator(self):
        """Test using key builder with TTL calculator."""
        # Generate a key
        key = CacheKeyBuilder.build_key(
            CacheKeyPrefix.FLIGHT_STATUS,
            "AA123"
        )
        
        # Calculate TTL with jitter
        ttl = TTLCalculator.calculate_ttl_with_jitter(TTLPreset.FLIGHT_STATUS)
        
        # Verify both work together
        assert key == "flight:status:AA123"
        assert 270 <= ttl <= 330
    
    def test_key_manager_with_all_presets(self):
        """Test key manager with all TTL presets."""
        test_cases = [
            (key_manager.flight_status_key("AA123"), TTLPreset.FLIGHT_STATUS),
            (key_manager.seat_reservation_key("AA123", 12), TTLPreset.SEAT_RESERVATION),
            (key_manager.weather_key("US", "LA"), TTLPreset.WEATHER_DATA),
            (key_manager.flight_search_key("LAX", "JFK", "2024-01-15"), TTLPreset.SEARCH_RESULTS),
            (key_manager.leaderboard_key(), TTLPreset.LEADERBOARD),
        ]
        
        for key, ttl_preset in test_cases:
            # Verify key is valid
            assert key_manager.validate_key(key)
            
            # Verify TTL preset is reasonable
            ttl = TTLCalculator.calculate_ttl_with_jitter(ttl_preset)
            assert ttl > 0
            assert ttl <= int(ttl_preset) * 1.1  # Within jitter range
    
    def test_config_with_key_generation(self):
        """Test that config and key generation work together."""
        # Create config
        config = ValkeyConfig(
            host="cache-server",
            port=6380,
            database=5
        )
        
        # Generate keys for this config context
        keys = [
            key_manager.flight_status_key("AA123"),
            key_manager.seat_map_key("AA123_20240115"),
            key_manager.weather_key("US", "Los_Angeles")  # Use underscore instead of space
        ]
        
        # All keys should be valid
        for key in keys:
            assert key_manager.validate_key(key)
            info = key_manager.get_key_info(key)
            assert info["is_valid"]
        
        # Config should be valid
        assert config.host == "cache-server"
        assert config.port == 6380
        assert config.database == 5


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])