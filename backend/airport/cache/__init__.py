"""
Caching layer for the OPN402 workshop.

This module contains Valkey client configuration, cache managers,
and advanced caching pattern implementations.
"""

from .config import ValkeyConfig, ValkeyConnectionError, ValkeyTimeoutError
from .client import ValkeyClient, get_client, close_global_client
from .utils import (
    CacheKeyPrefix,
    TTLPreset,
    CacheKeyBuilder,
    TTLCalculator,
    CacheKeyManager,
    key_manager
)
from .manager import CacheManager, CacheStats, get_cache_manager, close_global_cache_manager

__all__ = [
    # Configuration
    "ValkeyConfig",
    "ValkeyConnectionError", 
    "ValkeyTimeoutError",
    
    # Client
    "ValkeyClient",
    "get_client",
    "close_global_client",
    
    # Manager
    "CacheManager",
    "CacheStats",
    "get_cache_manager",
    "close_global_cache_manager",
    
    # Utilities
    "CacheKeyPrefix",
    "TTLPreset",
    "CacheKeyBuilder",
    "TTLCalculator", 
    "CacheKeyManager",
    "key_manager",
]
