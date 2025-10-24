"""
Environment configuration loader with validation for the OPN402 workshop.
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class WorkshopConfig(BaseModel):
    """Configuration model for the OPN402 workshop with validation."""

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///workshop_airport.db", description="Database connection URL"
    )

    # Valkey Cache Configuration
    valkey_host: str = Field(default="localhost", description="Valkey server host")
    valkey_port: int = Field(
        default=6379, ge=1, le=65535, description="Valkey server port"
    )
    valkey_password: Optional[str] = Field(
        default=None, description="Valkey server password"
    )
    valkey_database: int = Field(
        default=0, ge=0, le=15, description="Valkey database number"
    )
    valkey_max_connections: int = Field(
        default=10, ge=1, description="Maximum Valkey connections"
    )
    valkey_socket_timeout: int = Field(
        default=5, ge=1, description="Valkey socket timeout in seconds"
    )
    valkey_socket_connect_timeout: int = Field(
        default=5, ge=1, description="Valkey connection timeout in seconds"
    )

    # Workshop Configuration
    workshop_debug: bool = Field(default=False, description="Enable debug mode")
    workshop_log_level: str = Field(default="INFO", description="Logging level")

    # Performance Metrics
    enable_metrics: bool = Field(
        default=True, description="Enable performance metrics collection"
    )
    metrics_collection_interval: int = Field(
        default=1, ge=1, description="Metrics collection interval in seconds"
    )

    # External API Simulation
    weather_api_base_latency_ms: int = Field(
        default=250, ge=0, description="Base API latency in milliseconds"
    )
    weather_api_max_latency_ms: int = Field(
        default=500, ge=0, description="Maximum API latency in milliseconds"
    )
    weather_api_failure_rate: float = Field(
        default=0.05, ge=0.0, le=1.0, description="API failure rate (0.0-1.0)"
    )

    @validator("workshop_log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @validator("weather_api_max_latency_ms")
    def validate_max_latency(cls, v: int, values: dict) -> int:
        """Ensure max latency is greater than or equal to base latency."""
        if (
            "weather_api_base_latency_ms" in values
            and v < values["weather_api_base_latency_ms"]
        ):
            raise ValueError(
                "Maximum latency must be greater than or equal to base latency"
            )
        return v

    class Config:
        env_prefix = ""  # No prefix for environment variables


def load_config(env_file: Optional[str] = None) -> WorkshopConfig:
    """
    Load configuration from environment variables and .env file.

    Args:
        env_file: Optional path to .env file. If None, looks for .env in current directory.

    Returns:
        WorkshopConfig: Validated configuration object

    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Load environment variables from .env file if it exists
    if env_file is None:
        env_file = ".env"

    if os.path.exists(env_file):
        load_dotenv(env_file)

    # Create configuration from environment variables
    config_data: Dict[str, Any] = {
        "database_url": os.getenv("DATABASE_URL", "sqlite:///workshop_airport.db"),
        "valkey_host": os.getenv("VALKEY_HOST", "localhost"),
        "valkey_port": int(os.getenv("VALKEY_PORT", "6379")),
        "valkey_password": os.getenv("VALKEY_PASSWORD") or None,
        "valkey_database": int(os.getenv("VALKEY_DATABASE", "0")),
        "valkey_max_connections": int(os.getenv("VALKEY_MAX_CONNECTIONS", "10")),
        "valkey_socket_timeout": int(os.getenv("VALKEY_SOCKET_TIMEOUT", "5")),
        "valkey_socket_connect_timeout": int(
            os.getenv("VALKEY_SOCKET_CONNECT_TIMEOUT", "5")
        ),
        "workshop_debug": os.getenv("WORKSHOP_DEBUG", "false").lower()
        in ("true", "1", "yes", "on"),
        "workshop_log_level": os.getenv("WORKSHOP_LOG_LEVEL", "INFO"),
        "enable_metrics": os.getenv("ENABLE_METRICS", "true").lower()
        in ("true", "1", "yes", "on"),
        "metrics_collection_interval": int(
            os.getenv("METRICS_COLLECTION_INTERVAL", "1")
        ),
        "weather_api_base_latency_ms": int(
            os.getenv("WEATHER_API_BASE_LATENCY_MS", "250")
        ),
        "weather_api_max_latency_ms": int(
            os.getenv("WEATHER_API_MAX_LATENCY_MS", "500")
        ),
        "weather_api_failure_rate": float(
            os.getenv("WEATHER_API_FAILURE_RATE", "0.05")
        ),
    }

    try:
        return WorkshopConfig(**config_data)
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def validate_required_settings(config: WorkshopConfig) -> None:
    """
    Validate that all required settings are properly configured.

    Args:
        config: Configuration object to validate

    Raises:
        ValueError: If required settings are missing or invalid
    """
    # Validate database URL format
    if not config.database_url:
        raise ValueError("DATABASE_URL is required")

    # Validate Valkey connection settings
    if not config.valkey_host:
        raise ValueError("VALKEY_HOST is required")

    # Additional validation can be added here as needed
    print(f"✓ Configuration validated successfully")
    print(f"  Database: {config.database_url}")
    print(f"  Valkey: {config.valkey_host}:{config.valkey_port}")
    print(f"  Debug mode: {config.workshop_debug}")
    print(f"  Metrics enabled: {config.enable_metrics}")


# Global configuration instance
_config: Optional[WorkshopConfig] = None


def get_config() -> WorkshopConfig:
    """
    Get the global configuration instance, loading it if necessary.

    Returns:
        WorkshopConfig: The global configuration object
    """
    global _config
    if _config is None:
        _config = load_config()
        validate_required_settings(_config)
    return _config
