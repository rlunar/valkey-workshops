# Tests for Valkey Airport Workshop

This directory contains comprehensive tests for both the database and cache systems of the Valkey caching workshop. The tests validate SQLAlchemy models, database configuration, cache operations, and integration functionality.

## 🚀 Quick Start

### Run All Tests (Recommended)

```bash
uv run python tests/run_tests.py
```

This comprehensive test runner validates both database and cache systems with live demonstrations.

### Individual System Tests

```bash
# Database tests only
uv run python tests/run_database_tests.py

# Cache tests only  
uv run pytest tests/test_cache_simple.py -v

# Cache demo
uv run python tests/test_cache_demo.py
```

## Test Structure

### 🏃‍♂️ Test Runners

- **`run_tests.py`** - **Comprehensive test runner for database + cache systems** ⭐
- **`run_database_tests.py`** - Database-only test runner
- **`TEST_RUNNER_GUIDE.md`** - Detailed guide for using the test runners

### 🗄️ Database Test Files

- **`test_database_simple.py`** - Essential database functionality tests (recommended for CI/CD)
- **`test_database_models.py`** - Comprehensive model validation and relationship tests
- **`test_database_config.py`** - Database configuration and connection management tests
- **`test_database_integration.py`** - End-to-end integration tests with complex scenarios

### 💾 Cache Test Files

- **`test_cache_simple.py`** - Core cache functionality tests (32 tests) ⭐
- **`test_cache_integration.py`** - Advanced async cache tests (requires pytest-asyncio)
- **`test_cache_demo.py`** - Interactive cache system demonstration

### 📚 Documentation

- **`README.md`** - This documentation file
- **`CACHE_INTEGRATION_SUMMARY.md`** - Detailed cache implementation summary

## Running Tests

### Quick Validation (Recommended)

For a fast validation of core functionality:

```bash
uv run pytest tests/test_database_simple.py -v
```

### Full Test Suite

To run all database tests:

```bash
uv run python tests/run_database_tests.py
```

### Individual Test Categories

Run specific test categories:

```bash
# Model tests only
uv run pytest tests/test_database_models.py -v

# Configuration tests only  
uv run pytest tests/test_database_config.py -v

# Integration tests only
uv run pytest tests/test_database_integration.py -v
```

### Focused Testing

Run specific test classes or methods:

```bash
# Test specific model
uv run pytest tests/test_database_models.py::TestAirportModel -v

# Test specific functionality
uv run pytest tests/test_database_simple.py::TestDatabaseCore::test_model_creation_and_relationships -v
```

## Test Coverage

### Database Models (`test_database_models.py`)

- **Airport Model**: Creation, constraints, relationships, indexing
- **Airline Model**: IATA codes, base airport relationships
- **Flight Model**: Schedule data, multi-airport relationships
- **Passenger Model**: Passport validation, booking relationships
- **Booking Model**: Seat assignments, pricing, unique constraints
- **Model Utilities**: Table creation/deletion, metadata management

### Database Configuration (`test_database_config.py`)

- **Multi-RDBMS Support**: SQLite, MySQL, PostgreSQL configuration
- **Environment Variables**: .env file loading and URL construction
- **Connection Pooling**: Database-specific pool settings
- **Session Management**: Context managers, transaction handling
- **Error Handling**: Connection failures, invalid configurations
- **Global Configuration**: Singleton pattern, initialization

### Integration Testing (`test_database_integration.py`)

- **Complete Workflows**: End-to-end booking scenarios
- **Query Optimization**: Index usage validation
- **Relationship Navigation**: Complex multi-table queries
- **Data Integrity**: Foreign key constraints, cascading operations
- **Session Context**: Transaction management, rollback scenarios

### Simple Core Tests (`test_database_simple.py`)

- **Essential Functionality**: Core model and configuration features
- **Relationship Validation**: Basic foreign key relationships
- **Query Patterns**: Common workshop query scenarios
- **Constraint Testing**: Unique constraints and validation
- **Utility Functions**: Table management, string representations

## Test Data and Fixtures

### Sample Data Patterns

Tests use realistic airport industry data:

- **Airports**: LAX, SFO, JFK with proper IATA/ICAO codes
- **Airlines**: AA (American), DL (Delta) with base airports
- **Flights**: Realistic schedules with proper timing
- **Passengers**: Valid passport formats and names
- **Bookings**: Standard seat assignments (1A, 12B, etc.)

### Database Isolation

- Each test uses isolated in-memory SQLite databases
- Fixtures ensure clean state between tests
- No shared database state between test runs

## Workshop Integration

These tests validate the database layer used in the Valkey caching workshop:

### Caching Scenarios Tested

1. **Flight Search Queries**: Route-based and date-based searches
2. **Airport Lookups**: IATA/ICAO code resolution
3. **Booking Operations**: Seat availability and reservation
4. **Passenger Manifests**: Flight passenger lists
5. **Airline Operations**: Fleet and schedule management

### Performance Patterns

Tests validate indexes and query patterns for:

- Route searches (from_airport + to_airport + date)
- Airline flight listings (airline_id + date)
- Airport code lookups (IATA/ICAO indexes)
- Passenger booking history (passenger_id relationships)

## Troubleshooting

### Common Issues

1. **SQLAlchemy Version Compatibility**
   - Tests use SQLAlchemy 2.0+ syntax
   - Raw SQL requires `text()` wrapper
   - Declarative base import from `sqlalchemy.orm`

2. **Test Isolation**
   - Use unique identifiers in tests
   - Clean up database connections
   - Avoid shared global state

3. **Foreign Key Constraints**
   - SQLite requires explicit foreign key enabling
   - Tests account for database-specific behavior
   - Constraint validation varies by database type

### Debug Mode

Run tests with additional debugging:

```bash
# Verbose output with SQL logging
uv run pytest tests/test_database_simple.py -v -s --tb=long

# Show all warnings
uv run pytest tests/test_database_simple.py -v -W default
```

## Contributing

When adding new tests:

1. **Follow Naming Conventions**: `test_<functionality>_<specific_case>`
2. **Use Descriptive Docstrings**: Explain what the test validates
3. **Ensure Isolation**: Each test should be independent
4. **Add to Simple Tests**: Include essential functionality in `test_database_simple.py`
5. **Update Documentation**: Add new test categories to this README

### Test Categories

- **Unit Tests**: Individual model/function validation
- **Integration Tests**: Multi-component interaction
- **Configuration Tests**: Environment and setup validation
- **Performance Tests**: Query optimization and indexing

## Dependencies

Tests require:

- `pytest` - Test framework
- `sqlalchemy` - Database ORM
- `pymysql` - MySQL driver (for configuration tests)
- `psycopg2-binary` - PostgreSQL driver (for configuration tests)

All dependencies are managed via `uv` and defined in `pyproject.toml`.