"""
Valkey client implementation with health checks and automatic reconnection.

This module provides a robust Valkey client with connection pooling,
health monitoring, and automatic recovery from connection failures.
"""

import asyncio
import logging
import time
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager

import valkey
from valkey.connection import ConnectionPool
from valkey.exceptions import ConnectionError, TimeoutError, ResponseError

from .config import ValkeyConfig, ValkeyConnectionError, ValkeyTimeoutError

logger = logging.getLogger(__name__)


class ValkeyClient:
    """
    Robust Valkey client with health checks and automatic reconnection.
    
    Features:
    - Connection pooling with configurable pool size
    - Automatic health checks and reconnection
    - Graceful error handling and retry logic
    - Connection state monitoring
    """
    
    def __init__(self, config: Optional[ValkeyConfig] = None):
        """
        Initialize Valkey client with configuration.
        
        Args:
            config: ValkeyConfig instance, defaults to environment-based config
        """
        self.config = config or ValkeyConfig.from_env()
        self._client: Optional[valkey.Valkey] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._is_connected = False
        self._last_health_check = 0.0
        self._connection_attempts = 0
        self._max_connection_attempts = 5
        self._reconnect_delay = 1.0  # Start with 1 second delay
        self._max_reconnect_delay = 30.0  # Max 30 seconds between attempts
        
        logger.info(f"Initializing Valkey client: {self.config}")
    
    async def connect(self) -> None:
        """
        Establish connection to Valkey server with retry logic.
        
        Raises:
            ValkeyConnectionError: If connection cannot be established after max attempts
        """
        if self._is_connected and self._client:
            return
        
        self._connection_attempts = 0
        
        while self._connection_attempts < self._max_connection_attempts:
            try:
                self._connection_attempts += 1
                logger.info(f"Attempting Valkey connection (attempt {self._connection_attempts})")
                
                # Create connection pool
                self._connection_pool = ConnectionPool(**self.config.to_connection_pool_kwargs())
                
                # Create client with connection pool
                self._client = valkey.Valkey(connection_pool=self._connection_pool)
                
                # Test connection
                await self._test_connection()
                
                self._is_connected = True
                self._connection_attempts = 0
                self._reconnect_delay = 1.0  # Reset delay on successful connection
                
                logger.info("Successfully connected to Valkey server")
                return
                
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.warning(
                    f"Valkey connection attempt {self._connection_attempts} failed: {e}"
                )
                
                if self._connection_attempts >= self._max_connection_attempts:
                    error_msg = (
                        f"Failed to connect to Valkey after {self._max_connection_attempts} attempts. "
                        f"Last error: {e}"
                    )
                    logger.error(error_msg)
                    raise ValkeyConnectionError(error_msg) from e
                
                # Exponential backoff with jitter
                delay = min(self._reconnect_delay * (2 ** (self._connection_attempts - 1)), 
                           self._max_reconnect_delay)
                logger.info(f"Retrying connection in {delay:.1f} seconds...")
                await asyncio.sleep(delay)
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from Valkey server."""
        if self._connection_pool:
            try:
                self._connection_pool.disconnect()
                logger.info("Disconnected from Valkey server")
            except Exception as e:
                logger.warning(f"Error during Valkey disconnect: {e}")
            finally:
                self._connection_pool = None
                self._client = None
                self._is_connected = False
    
    async def _test_connection(self) -> None:
        """
        Test Valkey connection with a simple ping.
        
        Raises:
            ValkeyConnectionError: If ping fails
        """
        if not self._client:
            raise ValkeyConnectionError("Client not initialized")
        
        try:
            result = self._client.ping()
            if not result:
                raise ValkeyConnectionError("Ping returned False")
        except Exception as e:
            raise ValkeyConnectionError(f"Connection test failed: {e}") from e
    
    async def health_check(self, force: bool = False) -> bool:
        """
        Perform health check on Valkey connection.
        
        Args:
            force: Force health check even if recently performed
            
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        current_time = time.time()
        
        # Skip if recently checked (unless forced)
        if not force and (current_time - self._last_health_check) < self.config.health_check_interval:
            return self._is_connected
        
        self._last_health_check = current_time
        
        if not self._client or not self._is_connected:
            logger.debug("Health check failed: not connected")
            return False
        
        try:
            self._test_connection()
            logger.debug("Health check passed")
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self._is_connected = False
            return False
    
    async def ensure_connection(self) -> None:
        """
        Ensure connection is available, reconnect if necessary.
        
        Raises:
            ValkeyConnectionError: If connection cannot be established
        """
        if not await self.health_check():
            logger.info("Connection unhealthy, attempting reconnection...")
            self._is_connected = False
            await self.connect()
    
    @property
    def is_connected(self) -> bool:
        """Check if client is currently connected."""
        return self._is_connected and self._client is not None
    
    @property
    def client(self) -> valkey.Valkey:
        """
        Get the underlying Valkey client.
        
        Returns:
            valkey.Valkey: The Valkey client instance
            
        Raises:
            ValkeyConnectionError: If client is not connected
        """
        if not self._client or not self._is_connected:
            raise ValkeyConnectionError("Client not connected. Call connect() first.")
        return self._client
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information and statistics.
        
        Returns:
            Dict[str, Any]: Connection information
        """
        info = {
            "is_connected": self._is_connected,
            "config": str(self.config),
            "connection_attempts": self._connection_attempts,
            "last_health_check": self._last_health_check,
        }
        
        if self._client and self._is_connected:
            try:
                # Get server info
                server_info = self._client.info()
                info.update({
                    "server_version": server_info.get("redis_version", "unknown"),
                    "connected_clients": server_info.get("connected_clients", 0),
                    "used_memory": server_info.get("used_memory_human", "unknown"),
                    "uptime_seconds": server_info.get("uptime_in_seconds", 0),
                })
            except Exception as e:
                logger.warning(f"Failed to get server info: {e}")
                info["server_info_error"] = str(e)
        
        return info
    
    @asynccontextmanager
    async def connection_context(self):
        """
        Context manager for automatic connection management.
        
        Usage:
            async with client.connection_context():
                # Use client operations here
                pass
        """
        try:
            await self.ensure_connection()
            yield self
        except Exception as e:
            logger.error(f"Error in connection context: {e}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Global client instance for convenience
_global_client: Optional[ValkeyClient] = None


async def get_client(config: Optional[ValkeyConfig] = None) -> ValkeyClient:
    """
    Get or create a global Valkey client instance.
    
    Args:
        config: Optional ValkeyConfig, uses environment config if not provided
        
    Returns:
        ValkeyClient: Global client instance
    """
    global _global_client
    
    if _global_client is None:
        _global_client = ValkeyClient(config)
        await _global_client.connect()
    
    return _global_client


async def close_global_client() -> None:
    """Close the global client connection."""
    global _global_client
    
    if _global_client:
        await _global_client.disconnect()
        _global_client = None