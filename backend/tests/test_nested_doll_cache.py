#!/usr/bin/env python3
"""
Test suite for nested doll caching system with flight integration.

This module tests the hierarchical caching patterns, dependency management,
and selective invalidation capabilities of the nested doll cache system.
"""

import pytest
import pytest_asyncio
import asyncio
import sys
import os
from datetime import date, datetime
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from airport.services.nested_doll_cache import NestedDollCache, CacheDependencyGraph
from airport.cache.manager import CacheManager
from airport.models.cache_dependency import DependencyType, InvalidationType


class TestCacheDependencyGraph:
    """Test cache dependency graph functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.graph = CacheDependencyGraph()
    
    def test_add_dependency(self):
        """Test adding dependencies between cache keys."""
        self.graph.add_dependency("parent:1", "child:1")
        self.graph.add_dependency("parent:1", "child:2")
        
        children = self.graph.get_children("parent:1")
        assert "child:1" in children
        assert "child:2" in children
        assert len(children) == 2
    
    def test_get_parents(self):
        """Test getting parent dependencies."""
        self.graph.add_dependency("parent:1", "child:1")
        self.graph.add_dependency("parent:2", "child:1")
        
        parents = self.graph.get_parents("child:1")
        assert "parent:1" in parents
        assert "parent:2" in parents
        assert len(parents) == 2
    
    def test_get_all_descendants(self):
        """Test getting all descendants in hierarchy."""
        self.graph.add_dependency("parent:1", "child:1")
        self.graph.add_dependency("parent:1", "child:2")
        self.graph.add_dependency("child:1", "grandchild:1")
        self.graph.add_dependency("child:2", "grandchild:2")
        
        descendants = self.graph.get_all_descendants("parent:1")
        expected = {"child:1", "child:2", "grandchild:1", "grandchild:2"}
        assert descendants == expected
    
    def test_invalidation_cascade(self):
        """Test invalidation cascade ordering."""
        self.graph.add_dependency("parent:1", "child:1")
        self.graph.add_dependency("parent:1", "child:2")
        self.graph.add_dependency("child:1", "grandchild:1")
        
        cascade = self.graph.get_invalidation_cascade("parent:1")
        
        # Parent should be first
        assert cascade[0] == "parent:1"
        
        # Children should come before grandchildren
        parent_idx = cascade.index("parent:1")
        child1_idx = cascade.index("child:1")
        grandchild1_idx = cascade.index("grandchild:1")
        
        assert parent_idx < child1_idx < grandchild1_idx
    
    def test_remove_dependency(self):
        """Test removing dependencies."""
        self.graph.add_dependency("parent:1", "child:1")
        self.graph.add_dependency("parent:1", "child:2")
        
        self.graph.remove_dependency("parent:1", "child:1")
        
        children = self.graph.get_children("parent:1")
        assert "child:1" not in children
        assert "child:2" in children
        
        parents = self.graph.get_parents("child:1")
        assert "parent:1" not in parents


class TestNestedDollCache:
    """Test Nested doll cache functionality."""
    
    @pytest_asyncio.fixture
    async def cache_manager(self):
        """Create cache manager for testing."""
        manager = CacheManager(client=None, enable_fallback=True)
        await manager.initialize()
        yield manager
        await manager.close()
    
    @pytest_asyncio.fixture
    async def nested_doll_cache(self, cache_manager):
        """Create nested doll cache instance."""
        return NestedDollCache(cache_manager)
    
    def test_cache_key_generation(self, nested_doll_cache):
        """Test cache key generation for different data types."""
        # Test airport daily key
        airport_key = nested_doll_cache._generate_cache_key("airport_daily", "SEA", "2024-01-15")
        assert airport_key == "airport:daily:SEA:2024-01-15"
        
        # Test flight schedule key
        flight_key = nested_doll_cache._generate_cache_key("flight_schedule", "123")
        assert flight_key == "flight:schedule:123"
        
        # Test flight status key
        status_key = nested_doll_cache._generate_cache_key("flight_status", "456")
        assert status_key == "flight:status:456"
        
        # Test flight manifest key
        manifest_key = nested_doll_cache._generate_cache_key("flight_manifest", "789")
        assert manifest_key == "flight:manifest:789"
    
    @pytest.mark.asyncio
    async def test_flight_schedule_caching(self, nested_doll_cache):
        """Test flight schedule data caching."""
        flight_id = "123"
        
        # Cache flight schedule
        schedule_key = await nested_doll_cache.cache_flight_schedule_data(flight_id)
        
        # Verify key format
        expected_key = f"flight:schedule:{flight_id}"
        assert schedule_key == expected_key
        
        # Verify data was cached
        cached_data = await nested_doll_cache.cache.get(schedule_key)
        assert cached_data is not None
        assert cached_data["flight_id"] == int(flight_id)
        assert cached_data["data_type"] == "schedule"
        assert "flightno" in cached_data
        assert "scheduled_departure" in cached_data
    
    @pytest.mark.asyncio
    async def test_flight_status_caching(self, nested_doll_cache):
        """Test flight status data caching."""
        flight_id = "123"
        
        # Cache flight status
        status_key = await nested_doll_cache.cache_flight_status_data(flight_id)
        
        # Verify key format
        expected_key = f"flight:status:{flight_id}"
        assert status_key == expected_key
        
        # Verify data was cached
        cached_data = await nested_doll_cache.cache.get(status_key)
        assert cached_data is not None
        assert cached_data["flight_id"] == int(flight_id)
        assert cached_data["data_type"] == "status"
        assert "status" in cached_data
        assert "delay_minutes" in cached_data
    
    @pytest.mark.asyncio
    async def test_nested_flight_data_caching(self, nested_doll_cache):
        """Test nested flight data structure caching."""
        flight_id = "123"
        flight_data = {
            "flight_id": int(flight_id),
            "flightno": "AS123",
            "from_airport": 1,
            "to_airport": 2,
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T12:00:00",
            "airline_id": 1,
            "airplane_id": 1,
            "status": "scheduled"
        }
        
        # Cache nested flight data
        nested_key = await nested_doll_cache._cache_nested_flight_data(flight_data)
        
        # Verify nested structure was created
        nested_data = await nested_doll_cache.cache.get(nested_key)
        assert nested_data is not None
        assert nested_data["flight_id"] == flight_id
        assert "schedule_cache_key" in nested_data
        assert "status_cache_key" in nested_data
        
        # Verify dependencies were created
        schedule_key = nested_data["schedule_cache_key"]
        status_key = nested_data["status_cache_key"]
        
        children = nested_doll_cache.dependency_graph.get_children(nested_key)
        assert schedule_key in children
        assert status_key in children
    
    @pytest.mark.asyncio
    async def test_airport_daily_flights_caching(self, nested_doll_cache):
        """Test airport daily flights caching."""
        airport_id = "1"
        flight_date = date(2024, 1, 15)
        
        # Cache airport daily flights
        airport_data = await nested_doll_cache.cache_airport_daily_flights(airport_id, flight_date)
        
        # Verify structure
        assert airport_data is not None
        assert "airport" in airport_data
        assert "flight_date" in airport_data
        assert "departing_flights" in airport_data
        assert "arriving_flights" in airport_data
        
        # Verify airport info
        assert airport_data["airport"]["airport_id"] == int(airport_id)
        assert airport_data["flight_date"] == flight_date.isoformat()
        
        # Verify flight references
        total_flights = len(airport_data["departing_flights"]) + len(airport_data["arriving_flights"])
        assert total_flights > 0
        
        # Check flight reference structure
        if airport_data["departing_flights"]:
            flight_ref = airport_data["departing_flights"][0]
            assert "flight_id" in flight_ref
            assert "flight_number" in flight_ref
            assert "cache_key" in flight_ref
    
    @pytest.mark.asyncio
    async def test_selective_status_invalidation(self, nested_doll_cache):
        """Test selective invalidation of flight status data."""
        flight_id = "123"
        
        # Cache both schedule and status
        schedule_key = await nested_doll_cache.cache_flight_schedule_data(flight_id)
        status_key = await nested_doll_cache.cache_flight_status_data(flight_id)
        
        # Verify both are cached
        assert await nested_doll_cache.cache.exists(schedule_key)
        assert await nested_doll_cache.cache.exists(status_key)
        
        # Invalidate only status
        invalidated_keys = await nested_doll_cache.invalidate_flight_status(flight_id, "test_delay")
        
        # Verify only status was invalidated
        assert status_key in invalidated_keys
        assert schedule_key not in invalidated_keys
        
        # Verify cache states
        assert not await nested_doll_cache.cache.exists(status_key)
        assert await nested_doll_cache.cache.exists(schedule_key)
    
    @pytest.mark.asyncio
    async def test_cascade_schedule_invalidation(self, nested_doll_cache):
        """Test cascade invalidation when schedule changes."""
        flight_id = "123"
        
        # Cache schedule, status, and nested structure
        schedule_key = await nested_doll_cache.cache_flight_schedule_data(flight_id)
        status_key = await nested_doll_cache.cache_flight_status_data(flight_id)
        
        flight_data = {
            "flight_id": int(flight_id),
            "flightno": "AS123",
            "from_airport": 1,
            "to_airport": 2,
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T12:00:00",
            "airline_id": 1,
            "airplane_id": 1
        }
        nested_key = await nested_doll_cache._cache_nested_flight_data(flight_data)
        
        # Verify all are cached
        assert await nested_doll_cache.cache.exists(schedule_key)
        assert await nested_doll_cache.cache.exists(status_key)
        assert await nested_doll_cache.cache.exists(nested_key)
        
        # Invalidate schedule (should cascade)
        invalidated_keys = await nested_doll_cache.invalidate_flight_schedule(flight_id, "test_schedule_change")
        
        # Verify cascade invalidation
        assert schedule_key in invalidated_keys
        assert status_key in invalidated_keys
        assert nested_key in invalidated_keys
        
        # Verify all are invalidated
        assert not await nested_doll_cache.cache.exists(schedule_key)
        assert not await nested_doll_cache.cache.exists(status_key)
        assert not await nested_doll_cache.cache.exists(nested_key)
    
    @pytest.mark.asyncio
    async def test_flight_manifest_caching(self, nested_doll_cache):
        """Test flight manifest caching with passenger data."""
        flight_id = "123"
        
        # Cache flight manifest
        manifest_key = await nested_doll_cache.cache_flight_manifest(flight_id)
        
        # Verify manifest was cached
        manifest_data = await nested_doll_cache.cache.get(manifest_key)
        assert manifest_data is not None
        assert manifest_data["flight_id"] == int(flight_id)
        assert "passengers" in manifest_data
        assert "seat_map" in manifest_data
        assert "total_passengers" in manifest_data
        
        # Verify passenger entries structure
        if manifest_data["passengers"]:
            passenger_entry = manifest_data["passengers"][0]
            assert "booking" in passenger_entry
            assert "passenger" in passenger_entry
            assert "seat_assignment" in passenger_entry
            assert "boarding_group" in passenger_entry
    
    @pytest.mark.asyncio
    async def test_passenger_cache_invalidation(self, nested_doll_cache):
        """Test cross-cutting passenger cache invalidation."""
        passenger_id = "1"
        
        # Cache passenger details
        passenger_key = await nested_doll_cache.cache_passenger_details(passenger_id)
        
        # Verify passenger was cached
        assert await nested_doll_cache.cache.exists(passenger_key)
        
        # Invalidate passenger caches
        invalidated_keys = await nested_doll_cache.invalidate_passenger_caches(passenger_id, "test_name_change")
        
        # Verify passenger cache was invalidated
        assert passenger_key in invalidated_keys
        assert not await nested_doll_cache.cache.exists(passenger_key)
    
    @pytest.mark.asyncio
    async def test_dependency_graph_info(self, nested_doll_cache):
        """Test dependency graph information retrieval."""
        # Create some dependencies
        nested_doll_cache.dependency_graph.add_dependency("parent:1", "child:1")
        nested_doll_cache.dependency_graph.add_dependency("parent:1", "child:2")
        nested_doll_cache.dependency_graph.add_dependency("child:1", "grandchild:1")
        
        # Get graph info
        graph_info = await nested_doll_cache.get_dependency_graph_info()
        
        # Verify structure
        assert "total_cache_keys" in graph_info
        assert "total_dependencies" in graph_info
        assert "root_keys" in graph_info
        assert "leaf_keys" in graph_info
        assert "dependency_structure" in graph_info
        assert "metrics" in graph_info
        
        # Verify counts
        assert graph_info["total_dependencies"] >= 3
        assert "parent:1" in graph_info["root_keys"]
        assert "grandchild:1" in graph_info["leaf_keys"]
    
    @pytest.mark.asyncio
    async def test_cache_hierarchy_visualization(self, nested_doll_cache):
        """Test cache hierarchy visualization."""
        airport_id = "1"
        flight_date = date(2024, 1, 15)
        
        # Cache some data first
        await nested_doll_cache.cache_airport_daily_flights(airport_id, flight_date)
        
        # Generate visualization
        visualization = await nested_doll_cache.visualize_cache_hierarchy(airport_id, flight_date)
        
        # Verify visualization content
        assert isinstance(visualization, str)
        assert "Nested Doll Cache Hierarchy" in visualization
        assert "Airport Daily Cache" in visualization
        assert "Seattle-Tacoma International Airport" in visualization
        assert "2024-01-15" in visualization
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, nested_doll_cache):
        """Test performance comparison between nested and flat caching."""
        airport_id = "1"
        flight_date = date(2024, 1, 15)
        
        # Run performance comparison
        comparison = await nested_doll_cache.compare_with_flat_caching(airport_id, flight_date)
        
        # Verify comparison structure
        assert "nested_caching" in comparison
        assert "flat_caching" in comparison
        assert "performance_difference" in comparison
        
        # Verify nested caching metrics
        nested = comparison["nested_caching"]
        assert "response_time_ms" in nested
        assert "cache_hits" in nested
        assert "cache_misses" in nested
        assert "fragments_count" in nested
        
        # Verify flat caching metrics
        flat = comparison["flat_caching"]
        assert "response_time_ms" in flat
        assert "cache_hits" in flat
        assert "cache_misses" in flat
        assert flat["fragments_count"] == 1  # Single cache entry
        
        # Verify performance difference
        perf_diff = comparison["performance_difference"]
        assert "time_difference_ms" in perf_diff
        assert "nested_faster" in perf_diff
    
    @pytest.mark.asyncio
    async def test_flight_status_change_simulation(self, nested_doll_cache):
        """Test flight status change simulation."""
        flight_id = "123"
        
        # Cache initial data
        await nested_doll_cache.cache_flight_schedule_data(flight_id)
        await nested_doll_cache.cache_flight_status_data(flight_id)
        
        # Simulate status change
        simulation = await nested_doll_cache.simulate_flight_status_change(
            flight_id, "delayed", delay_minutes=30, gate="A12"
        )
        
        # Verify simulation structure
        assert simulation["flight_id"] == flight_id
        assert "changes" in simulation
        assert "before_state" in simulation
        assert "after_state" in simulation
        assert "performance" in simulation
        
        # Verify changes were applied
        changes = simulation["changes"]
        assert changes["status"] == "delayed"
        assert changes["delay_minutes"] == 30
        assert changes["gate"] == "A12"
        
        # Verify selective invalidation
        assert simulation["after_state"]["schedule_preserved"]
        assert simulation["performance"]["selective_invalidation"]


class TestNestedDollCacheIntegration:
    """Integration tests for Nested doll cache system."""
    
    @pytest_asyncio.fixture
    async def cache_system(self):
        """Set up complete cache system for integration testing."""
        cache_manager = CacheManager(client=None, enable_fallback=True)
        await cache_manager.initialize()
        
        nested_doll = NestedDollCache(cache_manager)
        
        yield nested_doll
        
        await cache_manager.close()
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, cache_system):
        """Test complete Nested doll cache workflow."""
        airport_id = "1"
        flight_date = date(2024, 1, 15)
        flight_id = "123"
        
        # Step 1: Cache airport daily flights (creates nested structure)
        airport_data = await cache_system.cache_airport_daily_flights(airport_id, flight_date)
        assert airport_data is not None
        
        # Step 2: Cache flight manifest
        manifest_key = await cache_system.cache_flight_manifest(flight_id)
        assert manifest_key is not None
        
        # Step 3: Get complete nested structure
        complete_structure = await cache_system.get_nested_airport_structure(airport_id, flight_date)
        assert complete_structure is not None
        assert "departing_flights" in complete_structure
        assert "arriving_flights" in complete_structure
        
        # Step 4: Test selective invalidation
        invalidated = await cache_system.invalidate_flight_status(flight_id, "integration_test")
        assert len(invalidated) > 0
        
        # Step 5: Verify structure still works after partial invalidation
        updated_structure = await cache_system.get_nested_airport_structure(airport_id, flight_date)
        assert updated_structure is not None
    
    @pytest.mark.asyncio
    async def test_complex_dependencies_demo(self, cache_system):
        """Test complex dependencies demonstration."""
        flight_id = "123"
        
        # Run complex dependencies demonstration
        demo = await cache_system.demonstrate_complex_dependencies(flight_id)
        
        # Verify demonstration structure
        assert demo["flight_id"] == flight_id
        assert "scenarios" in demo
        assert "dependency_analysis" in demo
        
        # Verify scenarios were tested
        scenarios = demo["scenarios"]
        assert "passenger_detail_change" in scenarios
        assert "manifest_change" in scenarios
        assert "booking_change" in scenarios
        
        # Verify dependency analysis
        analysis = demo["dependency_analysis"]
        assert "invalidation_patterns" in analysis
        assert "cache_efficiency" in analysis


def run_tests():
    """Run all Nested doll cache tests."""
    print("🧪 Running Nested Doll Cache Tests")
    print("=" * 50)
    
    # Run pytest with verbose output
    import subprocess
    
    try:
        result = subprocess.run([
            "python", "-m", "pytest", 
            __file__, 
            "-v", 
            "--tb=short",
            "-x"  # Stop on first failure
        ], capture_output=True, text=True, timeout=120)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ All Nested doll cache tests passed!")
            return True
        else:
            print("❌ Some Nested doll cache tests failed!")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Tests timed out!")
        return False
    except Exception as e:
        print(f"💥 Error running tests: {e}")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)