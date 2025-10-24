"""
Cache performance and metrics models for the airport workshop application.

This module contains models for cache performance monitoring, TTL distribution,
and cache effectiveness measurement used throughout the workshop demonstrations.
"""

from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class CacheMetricsModel(BaseModel):
    """
    Cache performance metrics model.
    
    Tracks cache effectiveness, performance statistics,
    and resource utilization for workshop demonstrations.
    """
    model_config = ConfigDict(from_attributes=True)
    
    hit_count: int = Field(default=0, ge=0, description="Number of cache hits")
    miss_count: int = Field(default=0, ge=0, description="Number of cache misses")
    hit_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Cache hit ratio")
    avg_response_time_ms: float = Field(default=0.0, ge=0.0, description="Average response time in milliseconds")
    memory_usage_mb: float = Field(default=0.0, ge=0.0, description="Memory usage in megabytes")
    key_count: int = Field(default=0, ge=0, description="Number of keys in cache")
    expiration_events: int = Field(default=0, ge=0, description="Number of key expirations")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last metrics update")


class TTLDistributionModel(BaseModel):
    """
    TTL distribution analysis model.
    
    Represents TTL calculation and distribution patterns
    for preventing cache expiration clustering.
    """
    model_config = ConfigDict(from_attributes=True)
    
    base_ttl_seconds: int = Field(..., ge=1, description="Base TTL in seconds")
    jitter_range_ms: int = Field(..., ge=0, description="Jitter range in milliseconds")
    calculated_ttl_ms: int = Field(..., ge=1, description="Final calculated TTL in milliseconds")
    expiration_timestamp: datetime = Field(..., description="Calculated expiration time")
    distribution_type: str = Field(default="normal", description="Distribution type (normal vs clustered)")


class APICacheEntryModel(BaseModel):
    """
    External API cache entry model.
    
    Represents cached responses from external APIs
    with performance and usage tracking.
    """
    model_config = ConfigDict(from_attributes=True)
    
    cache_key: str = Field(..., description="Cache key identifier")
    api_endpoint: str = Field(..., description="Original API endpoint")
    response_data: Dict[str, Any] = Field(..., description="Cached response data")
    cached_at: datetime = Field(default_factory=datetime.now, description="Cache creation time")
    ttl_seconds: int = Field(..., ge=1, description="Time to live in seconds")
    hit_count: int = Field(default=0, ge=0, description="Number of times accessed")
    last_accessed: datetime = Field(default_factory=datetime.now, description="Last access time")


class WeatherModel(BaseModel):
    """
    Weather API response model for external API caching demonstration.
    
    Represents weather data from the simulated weather API
    with response time tracking.
    """
    model_config = ConfigDict(from_attributes=True)
    
    country: str = Field(..., description="Country name")
    city: str = Field(..., description="City name")
    temperature_c: float = Field(..., ge=-50, le=60, description="Temperature in Celsius")
    humidity_percent: int = Field(..., ge=0, le=100, description="Humidity percentage")
    condition: str = Field(..., description="Weather condition")
    wind_speed_kmh: float = Field(..., ge=0, description="Wind speed in km/h")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data timestamp")
    api_response_time_ms: int = Field(..., ge=0, description="API response time in milliseconds")