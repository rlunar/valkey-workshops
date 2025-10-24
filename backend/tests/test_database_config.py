"""
Test suite for database configuration and connection management.

Tests database configuration, connection pooling, session management,
and multi-RDBMS support for the airport workshop system.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from airport.database.config import (
    DatabaseConfig,
    get_database_config,
    initialize_database,
    get_db_session,
    get_db_session_context,
)
from airport.database.models import Base, Airport


class TestDatabaseConfig:
    """Test cases for DatabaseConfig class."""
    
    def test_default_sqlite_configuration(self):
        """Test default SQLite configuration."""
        config = DatabaseConfig()
        
        assert config.db_type == 'sqlite'
        assert 'sqlite:///' in config.database_url
        assert 'workshop_airport.db' in config.database_url
        assert not config.echo
        assert not config._is_initialized
    
    def test_custom_database_url(self):
        """Test configuration with custom database URL."""
        custom_url = "sqlite:///custom.db"
        config = DatabaseConfig(database_url=custom_url)
        
        assert config.database_url == custom_url
        assert config.db_type == 'sqlite'
    
    def test_echo_parameter(self):
        """Test echo parameter configuration."""
        config = DatabaseConfig(echo=True)
        assert config.echo is True
    
    @patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@localhost/testdb'})
    def test_database_url_from_env(self):
        """Test database URL from environment variable."""
        config = DatabaseConfig()
        
        assert config.database_url == 'postgresql://user:pass@localhost/testdb'
        assert config.db_type == 'postgresql'
    
    @patch.dict(os.environ, {
        'DB_TYPE': 'mysql',
        'DB_HOST': 'localhost',
        'DB_PORT': '3306',
        'DB_NAME': 'testdb',
        'DB_USER': 'testuser',
        'DB_PASSWORD': 'testpass'
    })
    def test_mysql_url_from_components(self):
        """Test MySQL URL construction from environment components."""
        config = DatabaseConfig()
        
        expected_url = 'mysql+pymysql://testuser:testpass@localhost:3306/testdb?charset=utf8mb4'
        assert config.database_url == expected_url
        assert config.db_type == 'mysql'
    
    @patch.dict(os.environ, {
        'DB_TYPE': 'postgresql',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'testdb',
        'DB_USER': 'testuser',
        'DB_PASSWORD': 'testpass'
    })
    def test_postgresql_url_from_components(self):
        """Test PostgreSQL URL construction from environment components."""
        config = DatabaseConfig()
        
        expected_url = 'postgresql://testuser:testpass@localhost:5432/testdb'
        assert config.database_url == expected_url
        assert config.db_type == 'postgresql'
    
    def test_unsupported_database_type(self):
        """Test error handling for unsupported database types."""
        with patch.dict(os.environ, {'DB_TYPE': 'oracle'}):
            with pytest.raises(ValueError, match="Unsupported database type"):
                DatabaseConfig()
    
    def test_sqlite_engine_kwargs(self):
        """Test SQLite-specific engine configuration."""
        config = DatabaseConfig()
        kwargs = config._get_engine_kwargs()
        
        assert kwargs['echo'] is False
        assert kwargs['future'] is True
        assert kwargs['pool_pre_ping'] is True
        assert 'check_same_thread' in kwargs['connect_args']
        assert kwargs['connect_args']['check_same_thread'] is False
    
    @patch.dict(os.environ, {'DB_TYPE': 'mysql'})
    def test_mysql_engine_kwargs(self):
        """Test MySQL-specific engine configuration."""
        config = DatabaseConfig()
        kwargs = config._get_engine_kwargs()
        
        assert kwargs['pool_pre_ping'] is True
        assert 'pool_size' in kwargs
        assert 'max_overflow' in kwargs
        assert 'charset' in kwargs['connect_args']
    
    @patch.dict(os.environ, {'DB_TYPE': 'postgresql'})
    def test_postgresql_engine_kwargs(self):
        """Test PostgreSQL-specific engine configuration."""
        config = DatabaseConfig()
        kwargs = config._get_engine_kwargs()
        
        assert kwargs['pool_pre_ping'] is True
        assert 'pool_size' in kwargs
        assert 'max_overflow' in kwargs
    
    def test_initialization_success(self):
        """Test successful database initialization."""
        config = DatabaseConfig()
        config.initialize()
        
        assert config._is_initialized is True
        assert config.engine is not None
        assert config.SessionLocal is not None
        
        # Clean up
        config.close()
    
    def test_initialization_idempotent(self):
        """Test that initialization is idempotent."""
        config = DatabaseConfig()
        config.initialize()
        engine1 = config.engine
        
        config.initialize()  # Second call
        engine2 = config.engine
        
        assert engine1 is engine2
        assert config._is_initialized is True
        
        # Clean up
        config.close()
    
    def test_create_tables(self):
        """Test table creation."""
        config = DatabaseConfig()
        config.create_tables()
        
        # Verify tables exist by trying to query them
        with config.get_session_context() as session:
            # This should not raise an error if tables exist
            from sqlalchemy import text
            session.execute(text("SELECT COUNT(*) FROM airport"))
        
        # Clean up
        config.close()
    
    def test_get_session(self):
        """Test session creation."""
        config = DatabaseConfig()
        config.initialize()
        
        session = config.get_session()
        assert session is not None
        
        # Test that session works
        airport = Airport(iata="TST", icao="KTST", name="Test Airport")
        session.add(airport)
        session.commit()
        
        session.close()
        config.close()
    
    def test_session_context_manager(self):
        """Test session context manager."""
        config = DatabaseConfig()
        config.create_tables()
        
        # Test successful transaction
        with config.get_session_context() as session:
            airport = Airport(iata="CM1", icao="KCM1", name="Context Manager Test Airport")
            session.add(airport)
            # Commit happens automatically
        
        # Verify data was committed
        with config.get_session_context() as session:
            result = session.query(Airport).filter_by(iata="CM1").first()
            assert result is not None
            assert result.name == "Context Manager Test Airport"
        
        config.close()
    
    def test_session_context_rollback_on_error(self):
        """Test that session context manager rolls back on error."""
        config = DatabaseConfig()
        config.create_tables()
        
        # Test rollback on exception
        with pytest.raises(ValueError):
            with config.get_session_context() as session:
                airport = Airport(iata="RB1", icao="KRB1", name="Rollback Test Airport")
                session.add(airport)
                raise ValueError("Test error")
        
        # Verify data was not committed
        with config.get_session_context() as session:
            result = session.query(Airport).filter_by(iata="RB1").first()
            assert result is None
        
        config.close()
    
    def test_connection_test_success(self):
        """Test successful connection test."""
        config = DatabaseConfig()
        assert config.test_connection() is True
        config.close()
    
    def test_connection_test_failure(self):
        """Test connection test failure."""
        config = DatabaseConfig(database_url="sqlite:///nonexistent/path/db.sqlite")
        # This might still succeed with SQLite, so let's use an invalid URL
        config.database_url = "invalid://invalid"
        assert config.test_connection() is False
    
    def test_connection_info(self):
        """Test connection information retrieval."""
        config = DatabaseConfig()
        config.initialize()
        
        info = config.get_connection_info()
        
        assert 'database_type' in info
        assert 'database_url' in info
        assert 'is_initialized' in info
        assert 'echo_enabled' in info
        assert info['database_type'] == 'sqlite'
        assert info['is_initialized'] is True
        
        config.close()
    
    def test_close_connections(self):
        """Test connection cleanup."""
        config = DatabaseConfig()
        config.initialize()
        
        engine = config.engine
        assert engine is not None
        
        config.close()
        # After close, the engine should be disposed
        # We can't easily test this without accessing private attributes


class TestGlobalFunctions:
    """Test cases for global configuration functions."""
    
    def test_get_database_config_singleton(self):
        """Test that get_database_config returns singleton instance."""
        # Clear any existing global config
        import airport.database.config
        airport.database.config._db_config = None
        
        config1 = get_database_config()
        config2 = get_database_config()
        
        assert config1 is config2
        
        # Clean up
        config1.close()
    
    def test_initialize_database(self):
        """Test database initialization function."""
        # Clear any existing global config
        import airport.database.config
        airport.database.config._db_config = None
        
        config = initialize_database(create_tables=True)
        
        assert config._is_initialized is True
        assert config.engine is not None
        
        # Test that tables were created
        with config.get_session_context() as session:
            from sqlalchemy import text
            session.execute(text("SELECT COUNT(*) FROM airport"))
        
        # Clean up
        config.close()
    
    def test_get_db_session_global(self):
        """Test global session getter."""
        # Clear any existing global config
        import airport.database.config
        airport.database.config._db_config = None
        
        initialize_database()
        session = get_db_session()
        
        assert session is not None
        session.close()
        
        # Clean up
        get_database_config().close()
    
    def test_get_db_session_context_global(self):
        """Test global session context manager."""
        # Clear any existing global config
        import airport.database.config
        airport.database.config._db_config = None
        
        initialize_database()
        
        with get_db_session_context() as session:
            airport = Airport(iata="GLB", icao="KGLB", name="Global Test Airport")
            session.add(airport)
        
        # Verify data was committed
        with get_db_session_context() as session:
            result = session.query(Airport).filter_by(iata="GLB").first()
            assert result is not None
        
        # Clean up
        get_database_config().close()


class TestEnvironmentConfiguration:
    """Test cases for environment-based configuration."""
    
    def test_default_sqlite_path(self):
        """Test default SQLite database path."""
        config = DatabaseConfig()
        
        # Should create database in backend directory
        assert 'workshop_airport.db' in config.database_url
        # Path should be absolute
        assert str(Path(__file__).parent.parent) in config.database_url
    
    @patch.dict(os.environ, {'DB_NAME': 'custom_workshop.db'})
    def test_custom_sqlite_name(self):
        """Test custom SQLite database name."""
        config = DatabaseConfig()
        
        assert 'custom_workshop.db' in config.database_url
    
    @patch.dict(os.environ, {
        'DB_TYPE': 'mysql',
        'DB_POOL_SIZE': '5',
        'DB_MAX_OVERFLOW': '10',
        'DB_POOL_TIMEOUT': '60',
        'DB_POOL_RECYCLE': '7200'
    })
    def test_custom_pool_settings(self):
        """Test custom connection pool settings."""
        config = DatabaseConfig()
        kwargs = config._get_engine_kwargs()
        
        assert kwargs['pool_size'] == 5
        assert kwargs['max_overflow'] == 10
        assert kwargs['pool_timeout'] == 60
        assert kwargs['pool_recycle'] == 7200


class TestErrorHandling:
    """Test cases for error handling and edge cases."""
    
    def test_invalid_database_url(self):
        """Test handling of invalid database URLs."""
        config = DatabaseConfig(database_url="invalid://url")
        
        with pytest.raises(SQLAlchemyError):
            config.initialize()
    
    def test_session_creation_failure(self):
        """Test session creation failure handling."""
        config = DatabaseConfig()
        # Don't initialize - should return None for SessionLocal
        
        # This will actually auto-initialize, so let's test a different scenario
        # Test with invalid database URL after initialization
        config.database_url = "invalid://url"
        with pytest.raises(SQLAlchemyError):
            config.initialize()
    
    def test_table_creation_failure(self):
        """Test table creation failure handling."""
        config = DatabaseConfig(database_url="invalid://url")
        
        with pytest.raises(SQLAlchemyError):
            config.create_tables()


class TestDatabaseTypes:
    """Test cases for different database type detection and configuration."""
    
    def test_sqlite_detection(self):
        """Test SQLite database type detection."""
        config = DatabaseConfig(database_url="sqlite:///test.db")
        assert config.db_type == 'sqlite'
    
    def test_mysql_detection(self):
        """Test MySQL database type detection."""
        config = DatabaseConfig(database_url="mysql://user:pass@host/db")
        assert config.db_type == 'mysql'
    
    def test_postgresql_detection(self):
        """Test PostgreSQL database type detection."""
        config = DatabaseConfig(database_url="postgresql://user:pass@host/db")
        assert config.db_type == 'postgresql'
    
    def test_unknown_detection(self):
        """Test unknown database type detection."""
        config = DatabaseConfig(database_url="unknown://test")
        assert config.db_type == 'unknown'


@pytest.fixture(autouse=True)
def cleanup_global_config():
    """Clean up global configuration after each test."""
    yield
    # Clean up any global configuration
    import airport.database.config
    if airport.database.config._db_config:
        try:
            airport.database.config._db_config.close()
        except:
            pass
        airport.database.config._db_config = None