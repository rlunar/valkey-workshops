"""
Cache utilities for key naming conventions and TTL management.

This module provides utilities for consistent cache key generation,
TTL calculation with jitter, and cache operation helpers.
"""

import hashlib
import json
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class CacheKeyPrefix(str, Enum):
    """Standard cache key prefixes for different data types."""
    
    # Database query caching
    FLIGHT_SEARCH = "flight:search"
    FLIGHT_SCHEDULE = "flight:schedule"
    FLIGHT_STATUS = "flight:status"
    FLIGHT_MANIFEST = "flight:manifest"
    
    # Airport and airline data
    AIRPORT_INFO = "airport:info"
    AIRPORT_DAILY = "airport:daily"
    AIRLINE_INFO = "airline:info"
    
    # Passenger and booking data
    PASSENGER_INFO = "passenger:info"
    BOOKING_INFO = "booking:info"
    PASSENGER_MANIFEST = "passenger:manifest"
    
    # Seat reservation system
    SEAT_MAP = "seat:map"
    SEAT_RESERVATION = "seat:reservation"
    SEAT_LOCK = "seat:lock"
    
    # Leaderboard system
    LEADERBOARD = "leaderboard"
    PASSENGER_SCORE = "passenger:score"
    
    # External API caching
    WEATHER_API = "weather:api"
    WEATHER_CITY = "weather:city"
    
    # Russian doll caching
    NESTED_CACHE = "nested"
    CACHE_DEPENDENCY = "dependency"
    
    # Performance metrics
    METRICS = "metrics"
    PERFORMANCE = "performance"
    
    # Session management
    SESSION = "session"
    USER_PREFS = "user:prefs"


class TTLPreset(int, Enum):
    """Standard TTL presets in seconds for different data types."""
    
    # Very short-lived data (near real-time updates, use Pub/Sub for true real-time)
    NEAR_REAL_TIME = 30     # 30 seconds
    FLIGHT_STATUS = 300     # 5 minutes
    
    # Short-lived data (frequently changing)
    SEAT_RESERVATION = 60   # 1 minute (seat hold time)
    WEATHER_DATA = 900      # 15 minutes
    LEADERBOARD = 600       # 10 minutes
    
    # Medium-lived data (moderately changing)
    FLIGHT_MANIFEST = 1800  # 30 minutes
    SEARCH_RESULTS = 3600   # 1 hour
    
    # Long-lived data (rarely changing)
    FLIGHT_SCHEDULE = 21600 # 6 hours
    AIRPORT_INFO = 86400    # 24 hours
    AIRLINE_INFO = 86400    # 24 hours
    
    # Very long-lived data (static or semi-static)
    PASSENGER_INFO = 604800 # 1 week
    CONFIGURATION = 2592000 # 30 days


class CacheKeyBuilder:
    """
    Builder class for generating consistent cache keys.
    
    Provides methods for creating standardized cache keys with proper
    namespacing, parameter encoding, and hash generation.
    """
    
    @staticmethod
    def build_key(prefix: Union[CacheKeyPrefix, str], *parts: Any, **params: Any) -> str:
        """
        Build a cache key with prefix, parts, and parameters.
        
        Args:
            prefix: Key prefix (CacheKeyPrefix enum or string)
            *parts: Key parts to join with colons
            **params: Additional parameters to include in key
            
        Returns:
            str: Generated cache key
            
        Example:
            build_key(CacheKeyPrefix.FLIGHT_SEARCH, "LAX", "JFK", date="2024-01-15")
            # Returns: "flight:search:LAX:JFK:date=2024-01-15"
        """
        # Convert enum to its value, or use string as-is
        prefix_str = prefix.value if isinstance(prefix, CacheKeyPrefix) else str(prefix)
        key_parts = [prefix_str]
        
        # Add positional parts
        for part in parts:
            if part is not None:
                key_parts.append(str(part))
        
        # Add keyword parameters (sorted for consistency)
        if params:
            param_parts = []
            for key, value in sorted(params.items()):
                if value is not None:
                    param_parts.append(f"{key}={value}")
            if param_parts:
                key_parts.extend(param_parts)
        
        return ":".join(key_parts)
    
    @staticmethod
    def build_hash_key(prefix: Union[CacheKeyPrefix, str], data: Dict[str, Any]) -> str:
        """
        Build a cache key using hash of data for complex parameters.
        
        Args:
            prefix: Key prefix
            data: Data dictionary to hash
            
        Returns:
            str: Cache key with hash suffix
            
        Example:
            build_hash_key(CacheKeyPrefix.FLIGHT_SEARCH, {"from": "LAX", "to": "JFK"})
            # Returns: "flight:search:hash:a1b2c3d4..."
        """
        # Create deterministic hash of data
        data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:12]
        
        # Convert enum to its value, or use string as-is
        prefix_str = prefix.value if isinstance(prefix, CacheKeyPrefix) else str(prefix)
        return f"{prefix_str}:hash:{data_hash}"
    
    @staticmethod
    def build_pattern(prefix: Union[CacheKeyPrefix, str], *parts: str) -> str:
        """
        Build a key pattern for scanning/matching multiple keys.
        
        Args:
            prefix: Key prefix
            *parts: Pattern parts (use '*' for wildcards)
            
        Returns:
            str: Key pattern for Redis SCAN operations
            
        Example:
            build_pattern(CacheKeyPrefix.FLIGHT_STATUS, "*")
            # Returns: "flight:status:*"
        """
        # Convert enum to its value, or use string as-is
        prefix_str = prefix.value if isinstance(prefix, CacheKeyPrefix) else str(prefix)
        pattern_parts = [prefix_str]
        pattern_parts.extend(parts)
        return ":".join(pattern_parts)


class TTLCalculator:
    """
    Utility class for TTL calculation with jitter and distribution.
    
    Provides methods for calculating TTL values with jitter to prevent
    cache stampedes and expiration clustering.
    """
    
    @staticmethod
    def calculate_ttl_with_jitter(
        base_ttl: Union[int, TTLPreset], 
        jitter_percent: float = 0.1,
        min_ttl: int = 30
    ) -> int:
        """
        Calculate TTL with random jitter to prevent expiration clustering.
        
        Args:
            base_ttl: Base TTL in seconds
            jitter_percent: Jitter as percentage of base TTL (0.0 to 1.0)
            min_ttl: Minimum TTL to ensure
            
        Returns:
            int: TTL with jitter applied
            
        Example:
            calculate_ttl_with_jitter(3600, 0.1)  # 3600 ± 10% (3240-3960 seconds)
        """
        base_seconds = int(base_ttl)
        jitter_range = int(base_seconds * jitter_percent)
        
        # Apply random jitter (both positive and negative)
        jitter = random.randint(-jitter_range, jitter_range)
        final_ttl = base_seconds + jitter
        
        # Ensure minimum TTL
        return max(final_ttl, min_ttl)
    
    @staticmethod
    def calculate_ttl_milliseconds(
        base_ttl_seconds: int,
        jitter_ms: int = 1000
    ) -> int:
        """
        Calculate TTL in milliseconds with millisecond-level jitter.
        
        Used for preventing expiration clustering at second boundaries.
        
        Args:
            base_ttl_seconds: Base TTL in seconds
            jitter_ms: Jitter range in milliseconds
            
        Returns:
            int: TTL in milliseconds
        """
        base_ms = base_ttl_seconds * 1000
        jitter = random.randint(-jitter_ms, jitter_ms)
        return max(base_ms + jitter, 1000)  # Minimum 1 second
    
    @staticmethod
    def calculate_expiration_time(ttl_seconds: int) -> datetime:
        """
        Calculate expiration datetime from TTL.
        
        Args:
            ttl_seconds: TTL in seconds
            
        Returns:
            datetime: Expiration timestamp
        """
        return datetime.now() + timedelta(seconds=ttl_seconds)
    
    @staticmethod
    def get_remaining_ttl(expiration_time: datetime) -> int:
        """
        Get remaining TTL from expiration time.
        
        Args:
            expiration_time: Expiration timestamp
            
        Returns:
            int: Remaining TTL in seconds (0 if expired)
        """
        remaining = expiration_time - datetime.now()
        return max(0, int(remaining.total_seconds()))


class CacheKeyManager:
    """
    Manager class for cache key operations and utilities.
    
    Provides high-level methods for key generation, validation,
    and batch operations.
    """
    
    def __init__(self):
        self.key_builder = CacheKeyBuilder()
        self.ttl_calculator = TTLCalculator()
    
    def flight_search_key(
        self, 
        from_airport: str, 
        to_airport: str, 
        departure_date: str,
        **filters: Any
    ) -> str:
        """Generate cache key for flight search results."""
        return self.key_builder.build_key(
            CacheKeyPrefix.FLIGHT_SEARCH,
            from_airport,
            to_airport,
            departure_date,
            **filters
        )
    
    def flight_status_key(self, flight_id: Union[str, int]) -> str:
        """Generate cache key for flight status."""
        return self.key_builder.build_key(CacheKeyPrefix.FLIGHT_STATUS, flight_id)
    
    def flight_manifest_key(self, flight_id: Union[str, int]) -> str:
        """Generate cache key for flight passenger manifest."""
        return self.key_builder.build_key(CacheKeyPrefix.FLIGHT_MANIFEST, flight_id)
    
    def seat_map_key(self, flight_id: Union[str, int]) -> str:
        """Generate cache key for flight seat map."""
        return self.key_builder.build_key(CacheKeyPrefix.SEAT_MAP, flight_id)
    
    def seat_reservation_key(self, flight_id: Union[str, int], seat_number: int) -> str:
        """Generate cache key for seat reservation."""
        return self.key_builder.build_key(
            CacheKeyPrefix.SEAT_RESERVATION, 
            flight_id, 
            seat_number
        )
    
    def seat_lock_key(self, flight_id: Union[str, int], seat_number: int, user_id: str) -> str:
        """Generate cache key for seat reservation lock."""
        return self.key_builder.build_key(
            CacheKeyPrefix.SEAT_LOCK,
            flight_id,
            seat_number,
            user_id
        )
    
    def weather_key(self, country: str, city: str) -> str:
        """Generate cache key for weather data."""
        return self.key_builder.build_key(CacheKeyPrefix.WEATHER_CITY, country, city)
    
    def leaderboard_key(self, leaderboard_type: str = "passenger_bookings") -> str:
        """Generate cache key for leaderboard."""
        return self.key_builder.build_key(CacheKeyPrefix.LEADERBOARD, leaderboard_type)
    
    def passenger_score_key(self, passenger_id: Union[str, int]) -> str:
        """Generate cache key for passenger score."""
        return self.key_builder.build_key(CacheKeyPrefix.PASSENGER_SCORE, passenger_id)
    
    def russian_doll_key(self, *parts: str) -> str:
        """Generate cache key for Russian doll caching."""
        return self.key_builder.build_key(CacheKeyPrefix.NESTED_CACHE, *parts)
    
    def dependency_key(self, parent_key: str, child_key: str) -> str:
        """Generate cache key for dependency tracking."""
        parent_hash = hashlib.md5(parent_key.encode()).hexdigest()[:8]
        child_hash = hashlib.md5(child_key.encode()).hexdigest()[:8]
        return self.key_builder.build_key(
            CacheKeyPrefix.CACHE_DEPENDENCY,
            parent_hash,
            child_hash
        )
    
    def validate_key(self, key: str) -> bool:
        """
        Validate cache key format and length.
        
        Args:
            key: Cache key to validate
            
        Returns:
            bool: True if key is valid
        """
        if not key or not isinstance(key, str):
            return False
        
        # Check length (Redis key limit is ~512MB, but practical limit is much lower)
        if len(key) > 250:
            return False
        
        # Check for invalid characters (Redis allows most characters, but some are problematic)
        invalid_chars = ['\n', '\r', '\t', ' ']
        if any(char in key for char in invalid_chars):
            return False
        
        return True
    
    def get_key_info(self, key: str) -> Dict[str, Any]:
        """
        Extract information from cache key.
        
        Args:
            key: Cache key to analyze
            
        Returns:
            Dict[str, Any]: Key information
        """
        parts = key.split(':')
        
        info = {
            "key": key,
            "parts": parts,
            "prefix": parts[0] if parts else None,
            "length": len(key),
            "is_valid": self.validate_key(key),
        }
        
        # Try to identify key type
        if len(parts) >= 2:
            prefix_type = f"{parts[0]}:{parts[1]}"
            info["type"] = prefix_type
        
        return info


# Global key manager instance
key_manager = CacheKeyManager()