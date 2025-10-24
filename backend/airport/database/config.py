"""
Database configuration and connection management for the airport workshop system.

This module provides RDBMS-agnostic database configuration with support for:
- SQLite (default for workshop portability)
- MySQL/MariaDB (production-ready option)
- PostgreSQL (advanced features)

Configuration is loaded from environment variables with sensible defaults.
Includes connection pooling, session management, and error handling.
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from contextlib import contextmanager
from pathlib import Path

from .models import Base, create_all_tables

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """
    Database configuration manager supporting multiple RDBMS backends.
    
    Supports SQLite (default), MySQL, and PostgreSQL with automatic
    connection pooling and session management. Configuration is loaded
    from environment variables with workshop-friendly defaults.
    """
    
    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        """
        Initialize database configuration.
        
        Args:
            database_url: Optional database URL override
            echo: Enable SQL query logging for debugging
        """
        self.database_url = database_url or self._build_database_url()
        self.echo = echo
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._is_initialized = False
        
        # Database-specific configuration
        self.db_type = self._detect_database_type()
        self.engine_kwargs = self._get_engine_kwargs()
        
        logger.info(f"Database configuration initialized for {self.db_type}")
    
    def _build_database_url(self) -> str:
        """
        Build database URL from environment variables.
        
        Environment variables:
        - DATABASE_URL: Complete database URL (takes precedence)
        - DB_TYPE: Database type (sqlite, mysql, postgresql)
        - DB_HOST: Database host (default: localhost)
        - DB_PORT: Database port (default: varies by type)
        - DB_NAME: Database name (default: workshop_airport)
        - DB_USER: Database username
        - DB_PASSWORD: Database password
        
        Returns:
            Complete database URL string
        """
        # Check for complete DATABASE_URL first
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return database_url
        
        # Build URL from individual components
        db_type = os.getenv('DB_TYPE', 'sqlite').lower()
        
        if db_type == 'sqlite':
            # SQLite configuration - default for workshop portability
            db_name = os.getenv('DB_NAME', 'workshop_airport.db')
            # Ensure the database file is in the backend directory
            db_path = Path(__file__).parent.parent / db_name
            return f"sqlite:///{db_path}"
        
        elif db_type in ['mysql', 'mariadb']:
            # MySQL/MariaDB configuration
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '3306')
            database = os.getenv('DB_NAME', 'workshop_airport')
            username = os.getenv('DB_USER', 'root')
            password = os.getenv('DB_PASSWORD', '')
            
            # Use pymysql driver for better compatibility
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        
        elif db_type == 'postgresql':
            # PostgreSQL configuration
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '5432')
            database = os.getenv('DB_NAME', 'workshop_airport')
            username = os.getenv('DB_USER', 'postgres')
            password = os.getenv('DB_PASSWORD', '')
            
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def _detect_database_type(self) -> str:
        """Detect database type from URL."""
        if self.database_url.startswith('sqlite'):
            return 'sqlite'
        elif self.database_url.startswith('mysql'):
            return 'mysql'
        elif self.database_url.startswith('postgresql'):
            return 'postgresql'
        else:
            return 'unknown'
    
    def _get_engine_kwargs(self) -> Dict[str, Any]:
        """
        Get database-specific engine configuration.
        
        Returns:
            Dictionary of engine configuration parameters
        """
        kwargs = {
            'echo': self.echo,
            'future': True,  # Use SQLAlchemy 2.0 style
        }
        
        if self.db_type == 'sqlite':
            # SQLite-specific configuration
            kwargs.update({
                'poolclass': StaticPool,
                'connect_args': {
                    'check_same_thread': False,  # Allow multi-threading
                    'timeout': 30,  # Connection timeout
                },
                'pool_pre_ping': True,  # Verify connections before use
            })
        
        elif self.db_type in ['mysql', 'postgresql']:
            # Connection pooling for server databases
            pool_size = int(os.getenv('DB_POOL_SIZE', '10'))
            max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '20'))
            pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
            pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # 1 hour
            
            kwargs.update({
                'poolclass': QueuePool,
                'pool_size': pool_size,
                'max_overflow': max_overflow,
                'pool_timeout': pool_timeout,
                'pool_recycle': pool_recycle,
                'pool_pre_ping': True,  # Verify connections before use
            })
            
            if self.db_type == 'mysql':
                kwargs['connect_args'] = {
                    'charset': 'utf8mb4',
                    'connect_timeout': 30,
                }
        
        return kwargs
    
    def initialize(self) -> None:
        """
        Initialize database engine and session factory.
        
        Raises:
            SQLAlchemyError: If database connection fails
        """
        if self._is_initialized:
            return
        
        try:
            # Create engine with configuration
            self.engine = create_engine(self.database_url, **self.engine_kwargs)
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
                expire_on_commit=False  # Keep objects accessible after commit
            )
            
            # Set up event listeners for connection management
            self._setup_event_listeners()
            
            self._is_initialized = True
            logger.info(f"Database engine initialized successfully ({self.db_type})")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise SQLAlchemyError(f"Database initialization failed: {e}")
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for connection management."""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Configure SQLite-specific settings."""
            if self.db_type == 'sqlite':
                cursor = dbapi_connection.cursor()
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys=ON")
                # Set journal mode for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
        
        @event.listens_for(self.engine, "engine_connect")
        def receive_engine_connect(conn):
            """Log successful connections."""
            logger.debug("Database connection established")
    
    def create_tables(self) -> None:
        """
        Create all database tables if they don't exist.
        
        Raises:
            SQLAlchemyError: If table creation fails
        """
        if not self._is_initialized:
            self.initialize()
        
        try:
            create_all_tables(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise SQLAlchemyError(f"Table creation failed: {e}")
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy session instance
            
        Raises:
            SQLAlchemyError: If session creation fails
        """
        if not self._is_initialized:
            self.initialize()
        
        try:
            return self.SessionLocal()
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise SQLAlchemyError(f"Session creation failed: {e}")
    
    @contextmanager
    def get_session_context(self):
        """
        Get a database session with automatic cleanup.
        
        Usage:
            with db_config.get_session_context() as session:
                # Use session here
                pass
        
        Yields:
            SQLAlchemy session with automatic commit/rollback
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """
        Test database connectivity.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self._is_initialized:
                self.initialize()
            
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get database connection information for monitoring.
        
        Returns:
            Dictionary with connection details
        """
        info = {
            'database_type': self.db_type,
            'database_url': self.database_url.split('@')[-1] if '@' in self.database_url else self.database_url,
            'is_initialized': self._is_initialized,
            'echo_enabled': self.echo,
        }
        
        if self.engine and hasattr(self.engine.pool, 'size'):
            info.update({
                'pool_size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
            })
        
        return info
    
    def close(self) -> None:
        """Close database connections and clean up resources."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database configuration instance
_db_config: Optional[DatabaseConfig] = None


def get_database_config(database_url: Optional[str] = None, echo: bool = False) -> DatabaseConfig:
    """
    Get or create the global database configuration instance.
    
    Args:
        database_url: Optional database URL override
        echo: Enable SQL query logging
        
    Returns:
        DatabaseConfig instance
    """
    global _db_config
    
    if _db_config is None:
        _db_config = DatabaseConfig(database_url=database_url, echo=echo)
    
    return _db_config


def initialize_database(database_url: Optional[str] = None, echo: bool = False, create_tables: bool = True) -> DatabaseConfig:
    """
    Initialize the database with tables and sample data.
    
    Args:
        database_url: Optional database URL override
        echo: Enable SQL query logging
        create_tables: Whether to create tables automatically
        
    Returns:
        Initialized DatabaseConfig instance
    """
    db_config = get_database_config(database_url=database_url, echo=echo)
    db_config.initialize()
    
    if create_tables:
        db_config.create_tables()
    
    return db_config


# Convenience functions for session management
def get_db_session() -> Session:
    """Get a database session using the global configuration."""
    return get_database_config().get_session()


@contextmanager
def get_db_session_context():
    """Get a database session context using the global configuration."""
    with get_database_config().get_session_context() as session:
        yield session


# Export public interface
__all__ = [
    'DatabaseConfig',
    'get_database_config',
    'initialize_database',
    'get_db_session',
    'get_db_session_context',
]