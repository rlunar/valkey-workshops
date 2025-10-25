# Test Runner Guide

## 🚀 Comprehensive Test Runner

The `run_tests.py` script provides a comprehensive test suite for both database and cache systems in the Valkey Airport Workshop.

### Usage

```bash
# Run all tests
uv run python tests/run_tests.py

# Or make it executable and run directly
chmod +x tests/run_tests.py
./tests/run_tests.py
```

### Test Phases

The test runner executes in 4 phases:

#### 🔧 Phase 1: Quick Validations
- **Database Setup Validation**: Tests imports, configuration, initialization, table creation, and basic operations
- **Cache Setup Validation**: Tests imports, configuration, key generation, TTL calculation, and validation

#### 🗄️ Phase 2: Database Tests
- **test_database_models.py**: Tests all database models, relationships, and constraints
- **test_database_integration.py**: Tests complete database workflows and complex operations

#### 💾 Phase 3: Cache Tests  
- **test_cache_simple.py**: Tests all cache utilities, key management, TTL calculation, and core functionality (32 tests)

#### 🎭 Phase 4: Live Demonstrations
- **Cache System Demo**: Live demonstration of cache operations including:
  - Basic set/get/exists operations
  - Workshop-specific scenarios (flight search, seat reservations)
  - Statistics collection and health monitoring
  - Graceful degradation with fallback cache

### Output Format

The test runner provides:
- ✅ **Success indicators** for passing tests
- ❌ **Failure indicators** with error details
- ⏰ **Timeout indicators** for tests that take too long
- 💥 **Error indicators** for unexpected failures
- 📊 **Comprehensive summary** with statistics

### Example Output

```
🚀 Valkey Airport Workshop - Comprehensive Test Suite
======================================================================

🔧 PHASE 1: Quick Validations
===================================
✅ Database imports successful
✅ Cache configuration created
...

📊 Database Tests:
----------------
  ✅ tests/test_database_models.py: PASSED
  ✅ tests/test_database_integration.py: PASSED

📊 Cache Tests:
-------------
  ✅ tests/test_cache_simple.py: PASSED

📈 Overall Results:
   Total test files: 3
   Passed: 3
   Failed: 0
   Success rate: 100.0%

🏆 SUCCESS: All systems are ready for the Valkey Airport Workshop!
```

### Individual Test Runners

You can also run individual test categories:

```bash
# Database tests only
uv run python tests/run_database_tests.py

# Cache demo only  
uv run python tests/test_cache_demo.py

# Specific test files
uv run pytest tests/test_cache_simple.py -v
uv run pytest tests/test_database_models.py -v
```

### Troubleshooting

#### Common Issues

1. **Database constraint errors**: The test runner handles unique constraint issues automatically
2. **Cache connection warnings**: These are expected when Valkey is not running (fallback mode works)
3. **Async warnings**: Minor warnings about coroutines that don't affect functionality

#### Exit Codes

- **0**: All tests passed successfully
- **1**: Some tests failed or validation errors occurred

### Test Coverage

The comprehensive test suite covers:

#### Database System
- ✅ Model definitions and relationships
- ✅ Database configuration and initialization  
- ✅ CRUD operations and transactions
- ✅ Foreign key constraints and cascading
- ✅ Query optimization and indexing
- ✅ Session management and context managers

#### Cache System
- ✅ Valkey configuration and connection management
- ✅ Key generation and naming conventions
- ✅ TTL calculation with jitter
- ✅ Cache operations (get, set, delete, exists)
- ✅ Error handling and graceful degradation
- ✅ Circuit breaker and retry logic
- ✅ Performance monitoring and statistics
- ✅ Workshop-specific caching scenarios

### Workshop Readiness

When all tests pass, the system is ready for:
- Flight search result caching
- Seat reservation with distributed locking
- Weather API result caching  
- Passenger leaderboard caching
- Russian doll caching patterns
- Performance monitoring and health checks

🎉 **Ready for the Valkey Airport Workshop!**