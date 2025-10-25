"""
Integration tests for the leaderboard system.

Tests the real-time leaderboard functionality including sorted sets,
atomic operations, pagination, and memory optimization features.
"""

import asyncio
import pytest
from datetime import datetime
from typing import Dict, Any

from airport.cache.client import ValkeyClient
from airport.cache.config import ValkeyConfig
from airport.services.leaderboard import LeaderboardSystem, LeaderboardManager, create_leaderboard_system


class TestLeaderboardIntegration:
    """Integration tests for leaderboard system functionality."""
    
    @pytest.fixture
    def valkey_client(self):
        """Create a test Valkey client."""
        config = ValkeyConfig(
            host="localhost",
            port=6379,
            database=1,  # Use test database
            password=None
        )
        client = ValkeyClient(config)
        
        try:
            await client.connect()
            yield client
        finally:
            # Clean up test data
            if client.is_connected:
                test_client = client.client
                # Delete all test keys
                test_keys = test_client.keys("leaderboard:test_*")
                if test_keys:
                    test_client.delete(*test_keys)
            await client.disconnect()
    
    @pytest.fixture
    def leaderboard_system(self, valkey_client):
        """Create a test leaderboard system."""
        return LeaderboardSystem(valkey_client, "test_leaderboard")
    
    async def test_basic_leaderboard_operations(self, leaderboard_system):
        """Test basic leaderboard operations."""
        # Test passenger score updates
        success = await leaderboard_system.update_passenger_score(
            "passenger_1", 
            5, 
            {"name": "John Doe", "firstname": "John", "lastname": "Doe"}
        )
        assert success is True
        
        # Test score increment
        new_score = await leaderboard_system.increment_passenger_score(
            "passenger_1", 
            2,
            {"name": "John Doe", "firstname": "John", "lastname": "Doe"}
        )
        assert new_score == 7
        
        # Test getting passenger score
        score = await leaderboard_system.get_passenger_score("passenger_1")
        assert score == 7
        
        # Test getting passenger rank
        rank = await leaderboard_system.get_passenger_rank("passenger_1")
        assert rank == 1
    
    async def test_leaderboard_pagination(self, leaderboard_system):
        """Test leaderboard pagination functionality."""
        # Add multiple passengers
        passengers = [
            ("passenger_1", 10, {"name": "Alice", "firstname": "Alice", "lastname": "Smith"}),
            ("passenger_2", 8, {"name": "Bob", "firstname": "Bob", "lastname": "Jones"}),
            ("passenger_3", 12, {"name": "Charlie", "firstname": "Charlie", "lastname": "Brown"}),
            ("passenger_4", 6, {"name": "Diana", "firstname": "Diana", "lastname": "Wilson"}),
            ("passenger_5", 15, {"name": "Eve", "firstname": "Eve", "lastname": "Davis"}),
        ]
        
        for passenger_id, score, info in passengers:
            await leaderboard_system.update_passenger_score(passenger_id, score, info)
        
        # Test top passengers (should be ordered by score descending)
        top_3 = await leaderboard_system.get_top_passengers(limit=3)
        assert len(top_3) == 3
        assert top_3[0].passenger_id == "passenger_5"  # Score: 15
        assert top_3[0].booking_count == 15
        assert top_3[0].rank == 1
        assert top_3[1].passenger_id == "passenger_3"  # Score: 12
        assert top_3[1].rank == 2
        assert top_3[2].passenger_id == "passenger_1"  # Score: 10
        assert top_3[2].rank == 3
        
        # Test pagination with offset
        next_2 = await leaderboard_system.get_top_passengers(limit=2, offset=3)
        assert len(next_2) == 2
        assert next_2[0].passenger_id == "passenger_2"  # Score: 8
        assert next_2[0].rank == 4
        assert next_2[1].passenger_id == "passenger_4"  # Score: 6
        assert next_2[1].rank == 5
        
        # Test range queries
        middle_range = await leaderboard_system.get_passengers_in_range(2, 4)
        assert len(middle_range) == 3
        assert middle_range[0].rank == 2
        assert middle_range[2].rank == 4
    
    async def test_leaderboard_statistics(self, leaderboard_system):
        """Test leaderboard statistics and performance metrics."""
        # Add some test data
        passengers = [
            ("passenger_1", 5, {"name": "Test 1"}),
            ("passenger_2", 10, {"name": "Test 2"}),
            ("passenger_3", 3, {"name": "Test 3"}),
        ]
        
        for passenger_id, score, info in passengers:
            await leaderboard_system.update_passenger_score(passenger_id, score, info)
        
        # Test statistics
        stats = await leaderboard_system.get_leaderboard_stats()
        assert stats is not None
        assert stats.total_passengers == 3
        assert stats.total_bookings == 18  # 5 + 10 + 3
        assert stats.top_score == 10
        assert stats.average_score == 6.0  # 18 / 3
        assert stats.memory_usage_bytes > 0
        
        # Test performance metrics
        metrics = await leaderboard_system.get_performance_metrics()
        assert "cache_hits" in metrics
        assert "cache_misses" in metrics
        assert "hit_ratio" in metrics
        assert "leaderboard_stats" in metrics
    
    async def test_leaderboard_reset_and_archive(self, leaderboard_system):
        """Test leaderboard reset and archival functionality."""
        # Add some test data
        await leaderboard_system.update_passenger_score("passenger_1", 5, {"name": "Test"})
        await leaderboard_system.update_passenger_score("passenger_2", 10, {"name": "Test"})
        
        # Verify data exists
        stats_before = await leaderboard_system.get_leaderboard_stats()
        assert stats_before.total_passengers == 2
        
        # Test reset with archive
        reset_success = await leaderboard_system.reset_leaderboard(archive=True)
        assert reset_success is True
        
        # Verify leaderboard is empty
        stats_after = await leaderboard_system.get_leaderboard_stats()
        assert stats_after.total_passengers == 0
        
        # Check that archives exist
        archives = await leaderboard_system.get_archived_leaderboards()
        assert len(archives) >= 1
        assert archives[0]["total_entries"] == 2
    
    async def test_memory_optimization(self, leaderboard_system):
        """Test memory optimization features."""
        # Add test data
        passengers = [
            ("passenger_1", 5, {"name": "Test 1"}),
            ("passenger_2", 0, {"name": "Test 2"}),  # Zero score passenger
            ("passenger_3", 10, {"name": "Test 3"}),
        ]
        
        for passenger_id, score, info in passengers:
            await leaderboard_system.update_passenger_score(passenger_id, score, info)
        
        # Test memory optimization
        optimization_results = await leaderboard_system.optimize_memory()
        assert "initial_memory_bytes" in optimization_results
        assert "final_memory_bytes" in optimization_results
        assert "memory_saved_bytes" in optimization_results
        assert optimization_results["initial_memory_bytes"] >= 0
    
    async def test_leaderboard_manager(self, valkey_client):
        """Test leaderboard manager functionality."""
        manager = LeaderboardManager(valkey_client)
        
        # Create leaderboards
        lb1 = await manager.create_leaderboard("test_lb1")
        lb2 = await manager.create_leaderboard("test_lb2")
        
        assert lb1 is not None
        assert lb2 is not None
        
        # Add some data
        await lb1.update_passenger_score("passenger_1", 5, {"name": "Test 1"})
        await lb2.update_passenger_score("passenger_2", 10, {"name": "Test 2"})
        
        # Test listing leaderboards
        leaderboards = await manager.list_leaderboards()
        assert len(leaderboards) >= 2
        
        # Test global statistics
        global_stats = await manager.get_global_stats()
        assert global_stats["total_leaderboards"] >= 2
        assert global_stats["total_passengers"] >= 2
        assert global_stats["total_bookings"] >= 15
    
    async def test_high_frequency_simulation(self, leaderboard_system):
        """Test high-frequency update simulation."""
        # Run a small simulation
        results = await leaderboard_system.simulate_high_frequency_updates(
            num_passengers=10, 
            updates_per_passenger=5
        )
        
        assert "simulation_duration_seconds" in results
        assert "successful_updates" in results
        assert "updates_per_second" in results
        assert results["total_updates_attempted"] == 50  # 10 * 5
        assert results["successful_updates"] > 0
        
        # Verify final state
        stats = await leaderboard_system.get_leaderboard_stats()
        assert stats.total_passengers == 10
        assert stats.total_bookings == 50  # Each passenger should have 5 bookings


# Run tests if executed directly
if __name__ == "__main__":
    async def run_tests():
        """Run basic functionality tests."""
        print("Testing leaderboard system...")
        
        # Create test client
        config = ValkeyConfig(host="localhost", port=6379, database=1)
        client = ValkeyClient(config)
        
        try:
            await client.connect()
            print("✓ Connected to Valkey")
            
            # Create leaderboard
            leaderboard = LeaderboardSystem(client, "test_manual")
            
            # Test basic operations
            success = await leaderboard.update_passenger_score(
                "test_passenger", 
                5, 
                {"name": "Test User", "firstname": "Test", "lastname": "User"}
            )
            print(f"✓ Update passenger score: {success}")
            
            # Test increment
            new_score = await leaderboard.increment_passenger_score("test_passenger", 3)
            print(f"✓ Increment score: {new_score}")
            
            # Test rank
            rank = await leaderboard.get_passenger_rank("test_passenger")
            print(f"✓ Get rank: {rank}")
            
            # Test top passengers
            top = await leaderboard.get_top_passengers(limit=5)
            print(f"✓ Get top passengers: {len(top)} entries")
            
            # Test statistics
            stats = await leaderboard.get_leaderboard_stats()
            print(f"✓ Get statistics: {stats.total_passengers} passengers, {stats.total_bookings} bookings")
            
            # Clean up
            await leaderboard.reset_leaderboard(archive=False)
            print("✓ Cleaned up test data")
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
        finally:
            await client.disconnect()
            print("✓ Disconnected from Valkey")
    
    # Run the tests
    asyncio.run(run_tests())