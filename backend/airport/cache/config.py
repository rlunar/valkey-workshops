"""
Valkey cache configuration and connection management.

This module provides configuration classes for Valkey connections,
including environment variable support, connection pooling, and retry logic.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ValkeyConfig:
    """
    Configuration class for Valkey connections with environment variable support.
    
    Supports connection pooling, retry logic, and environment-specific parameters.
    """
    
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    decode_responses: bool = True
    
    @classmethod
    def from_env(cls) -> "ValkeyConfig":
        """
        Create ValkeyConfig from environment variables.
        
        Returns:
            ValkeyConfig: Configuration instance with values from environment
        """
        return cls(
            host=os.getenv("VALKEY_HOST", "localhost"),
            port=int(os.getenv("VALKEY_PORT", "6379")),
            password=os.getenv("VALKEY_PASSWORD") or None,
            database=int(os.getenv("VALKEY_DATABASE", "0")),
            max_connections=int(os.getenv("VALKEY_MAX_CONNECTIONS", "10")),
            socket_timeout=float(os.getenv("VALKEY_SOCKET_TIMEOUT", "5.0")),
            socket_connect_timeout=float(os.getenv("VALKEY_SOCKET_CONNECT_TIMEOUT", "5.0")),
            retry_on_timeout=os.getenv("VALKEY_RETRY_ON_TIMEOUT", "true").lower() == "true",
            health_check_interval=int(os.getenv("VALKEY_HEALTH_CHECK_INTERVAL", "30")),
            decode_responses=os.getenv("VALKEY_DECODE_RESPONSES", "true").lower() == "true"
        )
    
    def to_connection_kwargs(self) -> Dict[str, Any]:
        """
        Convert configuration to Valkey connection parameters.
        
        Returns:
            Dict[str, Any]: Connection parameters for Valkey client
        """
        kwargs = {
            "host": self.host,
            "port": self.port,
            "db": self.database,
            "socket_timeout": self.socket_timeout,
            "socket_connect_timeout": self.socket_connect_timeout,
            "retry_on_timeout": self.retry_on_timeout,
            "decode_responses": self.decode_responses,
        }
        
        if self.password:
            kwargs["password"] = self.password
            
        return kwargs
    
    def to_connection_pool_kwargs(self) -> Dict[str, Any]:
        """
        Convert configuration to Valkey connection pool parameters.
        
        Returns:
            Dict[str, Any]: Connection pool parameters for Valkey client
        """
        kwargs = self.to_connection_kwargs()
        kwargs["max_connections"] = self.max_connections
        return kwargs
    
    def __str__(self) -> str:
        """String representation hiding sensitive information."""
        password_display = "***" if self.password else "None"
        return (
            f"ValkeyConfig(host={self.host}, port={self.port}, "
            f"db={self.database}, password={password_display}, "
            f"max_connections={self.max_connections})"
        )


class ValkeyConnectionError(Exception):
    """Custom exception for Valkey connection issues."""
    pass


class ValkeyTimeoutError(Exception):
    """Custom exception for Valkey timeout issues."""
    pass


class ValkeyConfigurationError(Exception):
    """Custom exception for Valkey configuration issues."""
    pass