"""
Cache dependency and invalidation tracking models for the airport workshop application.

This module contains models for tracking cache dependencies, invalidation cascades,
and write-behind cache patterns used in advanced caching demonstrations.
"""

from datetime import datetime
from typing import List, Dict, Set, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class InvalidationType(str, Enum):
    """Types of cache invalidation operations."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CASCADE = "cascade"
    TTL_EXPIRY = "ttl_expiry"
    WRITE_BEHIND = "write_behind"


class DependencyType(str, Enum):
    """Types of cache dependencies."""
    PARENT_CHILD = "parent_child"
    SIBLING = "sibling"
    CROSS_REFERENCE = "cross_reference"
    TEMPORAL = "temporal"


class CacheDependencyModel(BaseModel):
    """
    Cache dependency relationship model.
    
    Represents a dependency relationship between cache keys
    for tracking invalidation cascades and cache coherence.
    """
    model_config = ConfigDict(from_attributes=True)
    
    parent_key: str = Field(..., description="Parent cache key")
    child_key: str = Field(..., description="Dependent child cache key")
    dependency_type: DependencyType = Field(..., description="Type of dependency relationship")
    created_at: datetime = Field(default_factory=datetime.now, description="Dependency creation time")
    last_validated: Optional[datetime] = Field(None, description="Last validation timestamp")
    is_active: bool = Field(default=True, description="Whether dependency is currently active")


class InvalidationEventModel(BaseModel):
    """
    Cache invalidation event tracking model.
    
    Records cache invalidation events for analysis and
    debugging of cache behavior patterns.
    """
    model_config = ConfigDict(from_attributes=True)
    
    event_id: str = Field(..., description="Unique event identifier")
    cache_key: str = Field(..., description="Invalidated cache key")
    invalidation_type: InvalidationType = Field(..., description="Type of invalidation")
    triggered_by: Optional[str] = Field(None, description="What triggered the invalidation")
    cascade_keys: List[str] = Field(
        default_factory=list, 
        description="Keys invalidated in cascade"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="Invalidation timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional event metadata"
    )


class CacheDependencyGraphModel(BaseModel):
    """
    Complete cache dependency graph model.
    
    Represents the entire dependency graph for tracking
    complex cache relationships and invalidation patterns.
    """
    model_config = ConfigDict(from_attributes=True)
    
    graph_id: str = Field(..., description="Unique graph identifier")
    dependencies: List[CacheDependencyModel] = Field(
        default_factory=list, 
        description="List of all dependencies"
    )
    invalidation_history: List[InvalidationEventModel] = Field(
        default_factory=list, 
        description="History of invalidation events"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="Graph creation time")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update time")


class WriteBehindQueueEntryModel(BaseModel):
    """
    Write-behind cache queue entry model.
    
    Represents an entry in the write-behind cache queue
    for delayed cache updates and invalidations.
    """
    model_config = ConfigDict(from_attributes=True)
    
    entry_id: str = Field(..., description="Unique entry identifier")
    cache_key: str = Field(..., description="Target cache key")
    operation: str = Field(..., description="Operation type (update, invalidate, refresh)")
    data: Optional[Dict[str, Any]] = Field(None, description="Data for update operations")
    scheduled_at: datetime = Field(..., description="Scheduled execution time")
    attempts: int = Field(default=0, ge=0, description="Number of execution attempts")
    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts")
    status: str = Field(default="pending", description="Entry status")
    created_at: datetime = Field(default_factory=datetime.now, description="Entry creation time")
    executed_at: Optional[datetime] = Field(None, description="Execution timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class CacheCoherenceModel(BaseModel):
    """
    Cache coherence tracking model.
    
    Tracks cache coherence state across distributed cache
    instances and ensures data consistency.
    """
    model_config = ConfigDict(from_attributes=True)
    
    cache_key: str = Field(..., description="Cache key being tracked")
    version: int = Field(default=1, ge=1, description="Data version number")
    checksum: str = Field(..., description="Data checksum for validation")
    last_modified: datetime = Field(default_factory=datetime.now, description="Last modification time")
    source_instance: str = Field(..., description="Source cache instance")
    replicated_instances: Set[str] = Field(
        default_factory=set, 
        description="Instances with replicated data"
    )
    consistency_level: str = Field(
        default="eventual", 
        description="Required consistency level"
    )


class CacheInvalidationStrategyModel(BaseModel):
    """
    Cache invalidation strategy configuration model.
    
    Defines invalidation strategies for different types
    of data and cache patterns.
    """
    model_config = ConfigDict(from_attributes=True)
    
    strategy_name: str = Field(..., description="Strategy identifier")
    cache_pattern: str = Field(..., description="Cache pattern (russian_doll, write_behind, etc.)")
    invalidation_rules: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Invalidation rules configuration"
    )
    cascade_depth: int = Field(default=3, ge=1, description="Maximum cascade depth")
    delay_seconds: int = Field(default=0, ge=0, description="Invalidation delay")
    batch_size: int = Field(default=100, ge=1, description="Batch processing size")
    retry_policy: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Retry policy configuration"
    )