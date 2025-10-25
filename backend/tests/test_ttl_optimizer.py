"""
TTL Optimizer tests for jittered expiration and clustering prevention.

Tests the TTL distribution functionality without requiring a running
Valkey instance by using mock clients and focusing on calculation logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import statistics

from airport.services.ttl_optimizer import TTLOptimizer, TTLDistributionStats
from airport.models.cache import TTLDistributionModel


class TestTTLOptimizer:
    """Test TTL optimizer functionality."""
    
    @pytest.fixture
    def mock_valkey_client(self):
        """Create mock Valkey client."""
        client = Mock()
        client.ensure_connection = AsyncMock()
        client.client = Mock()
        client.client.psetex = Mock(return_value=True)
        client.client.delete = Mock(return_value=1)
        return client
    
    @pytest.fixture
    def ttl_optimizer(self, mock_valkey_client):
        """Create TTL optimizer with mock client."""
        return TTLOptimizer(
            valkey_client=mock_valkey_client,
            base_ttl_ms=5000,
            jitter_range_ms=1000,
            enable_clustering_prevention=True
        )
    
    def test_ttl_optimizer_initialization(self, ttl_optimizer):
        """Test TTL optimizer initialization."""
        assert ttl_optimizer.base_ttl_ms == 5000
        assert ttl_optimizer.jitter_range_ms == 1000
        assert ttl_optimizer.enable_clustering_prevention is True
        assert isinstance(ttl_optimizer.stats, TTLDistributionStats)
    
    def test_calculate_distributed_ttl_with_jitter(self, ttl_optimizer):
        """Test TTL calculation with jitter enabled."""
        base_ttl = 5  # 5 seconds
        
        # Calculate multiple TTLs to test jitter
        ttl_values = []
        for _ in range(100):
            ttl_ms = ttl_optimizer.calculate_distributed_ttl(base_ttl)
            ttl_values.append(ttl_ms)
        
        # All values should be within expected range
        base_ms = base_ttl * 1000
        min_expected = base_ms - ttl_optimizer.jitter_range_ms
        max_expected = base_ms + ttl_optimizer.jitter_range_ms
        
        for ttl_ms in ttl_values:
            assert min_expected <= ttl_ms <= max_expected
            assert ttl_ms >= 1000  # Minimum 1 second
        
        # Should have some variation (not all the same)
        assert len(set(ttl_values)) > 1
        
        # Statistics should be updated
        assert ttl_optimizer.stats.total_keys == 100
        assert ttl_optimizer.stats.distributed_expirations > 0
    
    def test_calculate_distributed_ttl_without_jitter(self, ttl_optimizer):
        """Test TTL calculation with jitter disabled."""
        ttl_optimizer.enable_clustering_prevention = False
        base_ttl = 5  # 5 seconds
        
        # Calculate multiple TTLs
        ttl_values = []
        for _ in range(10):
            ttl_ms = ttl_optimizer.calculate_distributed_ttl(base_ttl)
            ttl_values.append(ttl_ms)
        
        # All values should be exactly the same (no jitter)
        expected_ms = base_ttl * 1000
        for ttl_ms in ttl_values:
            assert ttl_ms == expected_ms
        
        # Should have no variation
        assert len(set(ttl_values)) == 1
    
    @pytest.mark.asyncio
    async def test_set_with_distributed_ttl(self, ttl_optimizer, mock_valkey_client):
        """Test setting cache value with distributed TTL."""
        key = "test:key"
        value = {"test": "data"}
        base_ttl = 5
        
        result = await ttl_optimizer.set_with_distributed_ttl(key, value, base_ttl)
        
        assert result is True
        mock_valkey_client.ensure_connection.assert_called_once()
        mock_valkey_client.client.psetex.assert_called_once()
        
        # Check that psetex was called with correct parameters
        call_args = mock_valkey_client.client.psetex.call_args
        assert call_args[0][0] == key  # key
        assert isinstance(call_args[0][1], int)  # ttl_ms
        assert '"test": "data"' in call_args[0][2]  # serialized value
    
    @pytest.mark.asyncio
    async def test_set_with_distributed_ttl_override_clustering(self, ttl_optimizer, mock_valkey_client):
        """Test overriding clustering prevention setting."""
        key = "test:key"
        value = "test_value"
        base_ttl = 5
        
        # Override to disable clustering prevention
        await ttl_optimizer.set_with_distributed_ttl(
            key, value, base_ttl, use_clustering_prevention=False
        )
        
        # Original setting should be restored
        assert ttl_optimizer.enable_clustering_prevention is True
    
    @pytest.mark.asyncio
    async def test_analyze_expiration_patterns_empty(self, ttl_optimizer):
        """Test analysis with no data."""
        analysis = await ttl_optimizer.analyze_expiration_patterns()
        
        assert "error" in analysis
        assert analysis["total_keys"] == 0
    
    @pytest.mark.asyncio
    async def test_analyze_expiration_patterns_with_data(self, ttl_optimizer):
        """Test analysis with expiration data."""
        # Generate some test data
        base_ttl = 5
        for _ in range(50):
            ttl_optimizer.calculate_distributed_ttl(base_ttl)
        
        analysis = await ttl_optimizer.analyze_expiration_patterns()
        
        assert "distribution_stats" in analysis
        assert "clustering_analysis" in analysis
        assert "jitter_statistics" in analysis
        assert analysis["distribution_stats"]["total_keys"] == 50
        
        # Should have clustering analysis
        clustering = analysis["clustering_analysis"]
        assert "clustering_score" in clustering
        assert "distribution_type" in clustering
        assert clustering["total_buckets"] > 0
    
    def test_generate_ttl_distribution_chart_empty(self, ttl_optimizer):
        """Test chart generation with no data."""
        chart = ttl_optimizer.generate_ttl_distribution_chart()
        assert "No data available" in chart
    
    def test_generate_ttl_distribution_chart_with_data(self, ttl_optimizer):
        """Test chart generation with data."""
        # Generate some test data
        base_ttl = 5
        for _ in range(20):
            ttl_optimizer.calculate_distributed_ttl(base_ttl)
        
        chart = ttl_optimizer.generate_ttl_distribution_chart()
        
        assert "TTL Distribution Pattern" in chart
        assert "Total Keys: 20" in chart
        assert "Clustering Score:" in chart
        assert "Legend:" in chart
    
    @pytest.mark.asyncio
    async def test_demonstrate_clustering_vs_distribution(self, ttl_optimizer, mock_valkey_client):
        """Test clustering vs distribution demonstration."""
        # Mock the delete operation for cleanup
        mock_valkey_client.client.delete = AsyncMock(return_value=1)
        
        comparison = await ttl_optimizer.demonstrate_clustering_vs_distribution(
            num_keys=10, base_ttl_seconds=5
        )
        
        assert "test_parameters" in comparison
        assert "clustered_results" in comparison
        assert "distributed_results" in comparison
        assert "performance_impact" in comparison
        assert "recommendation" in comparison
        
        # Check test parameters
        params = comparison["test_parameters"]
        assert params["num_keys"] == 10
        assert params["base_ttl_seconds"] == 5
        
        # Should have different clustering scores
        clustered_score = comparison["clustered_results"]["clustering_score"]
        distributed_score = comparison["distributed_results"]["clustering_score"]
        
        # Both should be valid scores (0-1 range)
        assert 0 <= clustered_score <= 1
        assert 0 <= distributed_score <= 1
        
        # The distributed version should have jitter applied
        distributed_jitter = comparison["distributed_results"]["jitter_stats"]
        if distributed_jitter:
            assert distributed_jitter.get("mean", 0) > 0  # Should have some jitter
    
    @pytest.mark.asyncio
    async def test_get_current_stats(self, ttl_optimizer):
        """Test getting current statistics."""
        # Generate some data first
        for _ in range(5):
            ttl_optimizer.calculate_distributed_ttl(5)
        
        stats = await ttl_optimizer.get_current_stats()
        
        assert "configuration" in stats
        assert "statistics" in stats
        assert "history_size" in stats
        assert "performance_metrics" in stats
        
        config = stats["configuration"]
        assert config["base_ttl_ms"] == 5000
        assert config["jitter_range_ms"] == 1000
        assert config["clustering_prevention_enabled"] is True
        
        assert stats["statistics"]["total_keys"] == 5
        assert stats["history_size"] == 5
    
    def test_reset_stats(self, ttl_optimizer):
        """Test resetting statistics."""
        # Generate some data first
        for _ in range(5):
            ttl_optimizer.calculate_distributed_ttl(5)
        
        assert ttl_optimizer.stats.total_keys == 5
        assert len(ttl_optimizer._expiration_history) == 5
        
        ttl_optimizer.reset_stats()
        
        assert ttl_optimizer.stats.total_keys == 0
        assert len(ttl_optimizer._expiration_history) == 0
    
    def test_configure_jitter(self, ttl_optimizer):
        """Test configuring jitter range."""
        original_jitter = ttl_optimizer.jitter_range_ms
        new_jitter = 2000
        
        ttl_optimizer.configure_jitter(new_jitter)
        assert ttl_optimizer.jitter_range_ms == new_jitter
        
        # Test negative value (should be clamped to 0)
        ttl_optimizer.configure_jitter(-500)
        assert ttl_optimizer.jitter_range_ms == 0
    
    def test_toggle_clustering_prevention(self, ttl_optimizer):
        """Test toggling clustering prevention."""
        original_state = ttl_optimizer.enable_clustering_prevention
        
        new_state = ttl_optimizer.toggle_clustering_prevention()
        assert new_state != original_state
        assert ttl_optimizer.enable_clustering_prevention == new_state
        
        # Toggle back
        final_state = ttl_optimizer.toggle_clustering_prevention()
        assert final_state == original_state
        assert ttl_optimizer.enable_clustering_prevention == original_state


class TestTTLDistributionStats:
    """Test TTL distribution statistics."""
    
    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = TTLDistributionStats()
        
        assert stats.total_keys == 0
        assert stats.clustered_expirations == 0
        assert stats.distributed_expirations == 0
        assert stats.avg_jitter_ms == 0.0
        assert stats.clustering_score == 0.0
        assert len(stats.expiration_timeline) == 0
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = TTLDistributionStats()
        stats.total_keys = 10
        stats.clustered_expirations = 2
        stats.distributed_expirations = 8
        stats.avg_jitter_ms = 500.0
        stats.clustering_score = 0.3
        
        stats_dict = stats.to_dict()
        
        assert stats_dict["total_keys"] == 10
        assert stats_dict["clustered_expirations"] == 2
        assert stats_dict["distributed_expirations"] == 8
        assert stats_dict["avg_jitter_ms"] == 500.0
        assert stats_dict["clustering_score"] == 0.3
        assert "expiration_count" in stats_dict


class TestTTLDistributionModel:
    """Test TTL distribution model."""
    
    def test_model_creation(self):
        """Test creating TTL distribution model."""
        expiration_time = datetime.now() + timedelta(seconds=5)
        
        model = TTLDistributionModel(
            base_ttl_seconds=5,
            jitter_range_ms=1000,
            calculated_ttl_ms=5500,
            expiration_timestamp=expiration_time,
            distribution_type="normal"
        )
        
        assert model.base_ttl_seconds == 5
        assert model.jitter_range_ms == 1000
        assert model.calculated_ttl_ms == 5500
        assert model.expiration_timestamp == expiration_time
        assert model.distribution_type == "normal"
    
    def test_model_validation(self):
        """Test model field validation."""
        expiration_time = datetime.now() + timedelta(seconds=5)
        
        # Test with valid data
        model = TTLDistributionModel(
            base_ttl_seconds=1,  # minimum 1 second
            jitter_range_ms=0,   # minimum 0 ms
            calculated_ttl_ms=1000,  # minimum 1 ms
            expiration_timestamp=expiration_time
        )
        
        assert model.base_ttl_seconds == 1
        assert model.jitter_range_ms == 0
        assert model.calculated_ttl_ms == 1000