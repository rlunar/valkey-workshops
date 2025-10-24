"""
Simulation models for the airport workshop application.

This module contains models for concurrent booking simulations,
race condition demonstrations, and performance testing scenarios.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ConcurrentBookingSimulationModel(BaseModel):
    """
    Results from concurrent booking simulation.
    
    Tracks the results of multi-user seat booking simulations
    for demonstrating race conditions and distributed locking.
    """
    model_config = ConfigDict(from_attributes=True)
    
    simulation_id: str = Field(..., description="Unique simulation identifier")
    flight_id: str = Field(..., description="Target flight for simulation")
    num_concurrent_users: int = Field(..., ge=1, description="Number of concurrent users simulated")
    successful_reservations: int = Field(..., ge=0, description="Number of successful reservations")
    failed_reservations: int = Field(..., ge=0, description="Number of failed reservation attempts")
    race_conditions_detected: int = Field(..., ge=0, description="Number of race conditions detected")
    average_response_time_ms: float = Field(..., ge=0.0, description="Average response time in milliseconds")
    lock_contention_events: int = Field(..., ge=0, description="Number of lock contention events")
    simulation_duration_ms: int = Field(..., ge=0, description="Total simulation duration in milliseconds")
    started_at: datetime = Field(default_factory=datetime.now, description="Simulation start time")
    completed_at: Optional[datetime] = Field(None, description="Simulation completion time")


class UserSimulationModel(BaseModel):
    """
    Individual user simulation within concurrent booking test.
    
    Represents a single simulated user's booking attempt
    with detailed timing and result information.
    """
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str = Field(..., description="Simulated user identifier")
    target_seat: int = Field(..., ge=1, description="Target seat number")
    attempt_start: datetime = Field(default_factory=datetime.now, description="Attempt start time")
    attempt_end: Optional[datetime] = Field(None, description="Attempt completion time")
    success: bool = Field(default=False, description="Whether the booking was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    lock_wait_time_ms: int = Field(default=0, ge=0, description="Time spent waiting for lock")
    total_response_time_ms: int = Field(default=0, ge=0, description="Total response time")


class PerformanceTestResultModel(BaseModel):
    """
    Performance test results for cache effectiveness measurement.
    
    Captures performance metrics for comparing cached vs non-cached
    operations across different workshop scenarios.
    """
    model_config = ConfigDict(from_attributes=True)
    
    test_id: str = Field(..., description="Unique test identifier")
    test_type: str = Field(..., description="Type of performance test")
    scenario_name: str = Field(..., description="Workshop scenario being tested")
    cached_operations: int = Field(..., ge=0, description="Number of cached operations")
    uncached_operations: int = Field(..., ge=0, description="Number of uncached operations")
    avg_cached_response_ms: float = Field(..., ge=0.0, description="Average cached response time")
    avg_uncached_response_ms: float = Field(..., ge=0.0, description="Average uncached response time")
    performance_improvement_ratio: float = Field(..., ge=0.0, description="Performance improvement ratio")
    cache_hit_ratio: float = Field(..., ge=0.0, le=1.0, description="Cache hit ratio during test")
    test_duration_seconds: int = Field(..., ge=0, description="Total test duration")
    started_at: datetime = Field(default_factory=datetime.now, description="Test start time")
    completed_at: Optional[datetime] = Field(None, description="Test completion time")


class LoadTestConfigModel(BaseModel):
    """
    Configuration for load testing scenarios.
    
    Defines parameters for stress testing cache performance
    and system behavior under various load conditions.
    """
    model_config = ConfigDict(from_attributes=True)
    
    concurrent_users: int = Field(..., ge=1, le=1000, description="Number of concurrent users")
    operations_per_user: int = Field(..., ge=1, description="Operations per user")
    ramp_up_seconds: int = Field(default=0, ge=0, description="Ramp-up time in seconds")
    test_duration_seconds: int = Field(..., ge=1, description="Test duration in seconds")
    cache_enabled: bool = Field(default=True, description="Whether caching is enabled")
    target_operations: List[str] = Field(..., description="List of operations to test")
    expected_response_time_ms: int = Field(default=100, ge=1, description="Expected response time threshold")