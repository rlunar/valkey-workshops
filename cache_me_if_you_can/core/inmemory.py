"""Centralized connection management for Valkey, Redis, and Memcached."""

import os
import ssl
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a strict, human-friendly boolean environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


class InMemoryCache:
    """Factory and wrapper for in-memory cache connections."""

    def __init__(
        self,
        cache_type: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        decode_responses: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[int] = None,
        tls: Optional[bool] = None,
        tls_ca_certs: Optional[str] = None,
        tls_certfile: Optional[str] = None,
        tls_keyfile: Optional[str] = None,
        connect_timeout: Optional[float] = None,
        socket_timeout: Optional[float] = None,
        health_check_interval: Optional[int] = None,
        allow_flush_all: Optional[bool] = None,
    ):
        """Initialize a cache client from arguments or environment variables."""
        self.cache_type = (cache_type or os.getenv("CACHE_ENGINE", "redis")).lower()
        self.host = host or os.getenv("CACHE_HOST", "localhost")
        self.port = port if port is not None else int(os.getenv("CACHE_PORT", "6379"))
        self.decode_responses = decode_responses
        self.username = username if username is not None else os.getenv("CACHE_USERNAME")
        self.password = password if password is not None else os.getenv("CACHE_PASSWORD")
        self.database = (
            database if database is not None else int(os.getenv("CACHE_DB", "0"))
        )
        self.tls = tls if tls is not None else _env_bool("CACHE_TLS", False)
        self.tls_ca_certs = tls_ca_certs or os.getenv("CACHE_TLS_CA_CERTS")
        self.tls_certfile = tls_certfile or os.getenv("CACHE_TLS_CERTFILE")
        self.tls_keyfile = tls_keyfile or os.getenv("CACHE_TLS_KEYFILE")
        self.connect_timeout = (
            connect_timeout
            if connect_timeout is not None
            else float(os.getenv("CACHE_CONNECT_TIMEOUT", "5"))
        )
        self.socket_timeout = (
            socket_timeout
            if socket_timeout is not None
            else float(os.getenv("CACHE_SOCKET_TIMEOUT", "5"))
        )
        self.health_check_interval = (
            health_check_interval
            if health_check_interval is not None
            else int(os.getenv("CACHE_HEALTH_CHECK_INTERVAL", "30"))
        )
        self.allow_flush_all = (
            allow_flush_all
            if allow_flush_all is not None
            else _env_bool("CACHE_ALLOW_FLUSH_ALL", False)
        )
        self.client = self._create_client()

    def _create_client(self) -> Any:
        """Create the configured cache client."""
        if self.cache_type in {"redis", "valkey"}:
            try:
                import valkey
            except ImportError:
                import redis as valkey

            client_kwargs = {
                "host": self.host,
                "port": self.port,
                "db": self.database,
                "username": self.username,
                "password": self.password,
                "decode_responses": self.decode_responses,
                "socket_connect_timeout": self.connect_timeout,
                "socket_timeout": self.socket_timeout,
                "health_check_interval": self.health_check_interval,
            }
            if self.tls:
                client_kwargs.update(
                    {
                        "ssl": True,
                        "ssl_cert_reqs": ssl.CERT_REQUIRED,
                        "ssl_ca_certs": self.tls_ca_certs,
                        "ssl_certfile": self.tls_certfile,
                        "ssl_keyfile": self.tls_keyfile,
                    }
                )
            return valkey.Redis(**client_kwargs)

        if self.cache_type == "memcached":
            from pymemcache.client import base

            return base.Client(
                (self.host, self.port),
                connect_timeout=self.connect_timeout,
                timeout=self.socket_timeout,
            )

        raise ValueError(f"Unsupported CACHE_ENGINE: {self.cache_type}")

    def get(self, key: str) -> Optional[str]:
        """Get a value; transport and authentication failures propagate."""
        if self.cache_type in {"redis", "valkey"}:
            return self.client.get(key)
        value = self.client.get(key)
        return value.decode() if value else None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value with an optional TTL and return backend success."""
        if self.cache_type in {"redis", "valkey"}:
            result = (
                self.client.setex(key, ttl, value)
                if ttl is not None
                else self.client.set(key, value)
            )
            return bool(result)
        return bool(self.client.set(key, value.encode(), expire=ttl or 0))

    def delete(self, key: str) -> bool:
        """Delete a key; backend failures propagate."""
        return bool(self.client.delete(key))

    def flush_all(self) -> None:
        """Clear the selected cache only when explicitly enabled."""
        if not self.allow_flush_all:
            raise PermissionError(
                "Cache flush is disabled; set CACHE_ALLOW_FLUSH_ALL=true only "
                "for an isolated workshop cache"
            )
        if self.cache_type in {"redis", "valkey"}:
            self.client.flushdb()
        else:
            self.client.flush_all()

    def close(self) -> None:
        """Close the cache connection; failures propagate."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_cache_client(
    cache_type: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    **kwargs: Any,
) -> InMemoryCache:
    """Create an InMemoryCache from explicit values and environment defaults."""
    return InMemoryCache(
        cache_type=cache_type,
        host=host,
        port=port,
        **kwargs,
    )
