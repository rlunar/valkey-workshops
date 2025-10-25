"""
TTL Distribution Optimizer for preventing cache expiration clustering.

This module implements millisecond-level TTL distribution to prevent cache
expiration clustering at second boundaries, which can cause performance spikes
and cache stampedes when many keys expire simultaneously.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from ..cache.client import ValkeyClient
from ..cache.config import ValkeyConfig
from ..models.cache import TTLDistributionModel, CacheMetricsModel

logger = logging.getLogger(__name__)


@dataclass
class TTLDistributionStats:
    """Statistics for TTL distribution analysis."""
    
    total_keys: int = 0
    clustered_expirations: int = 0
    distributed_expirations: int = 0
    avg_jitter_ms: float = 0.0
    min_jitter_ms: int = 0
    max_jitter_ms: int = 0
    expiration_timeline: List[Tuple[datetime, int]] = field(default_factory=list)
    clustering_score: float = 0.0  # 0.0 = perfectly distributed, 1.0 = completely clustered
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_keys": self.total_keys,
            "clustered_expirations": self.clustered_expirations,
            "distributed_expirations": self.distributed_expirations,
            "avg_jitter_ms": self.avg_jitter_ms,
            "min_jitter_ms": self.min_jitter_ms,
            "max_jitter_ms": self.max_jitter_ms,
            "clustering_score": self.clustering_score,
            "expiration_count": len(self.expiration_timeline),
        }


class TTLOptimizer:
    """
    TTL Distribution Optimizer with millisecond-level jittered expiration.
    
    Prevents cache expiration clustering by distributing TTL values across
    time using millisecond-precision jitter. This prevents performance spikes
    caused by many keys expiring simultaneously.
    
    Features:
    - Millisecond-precision TTL calculation
    - Configurable jitter ranges
    - Distribution pattern analysis
    - Performance impact demonstration
    - Clustering prevention visualization
    """
    
    def __init__(
        self, 
        valkey_client: ValkeyClient,
        base_ttl_ms: int = 5000,
        jitter_range_ms: int = 1000,
        enable_clustering_prevention: bool = True
    ):
        """
        Initialize TTL optimizer.
        
        Args:
            valkey_client: Valkey client instance
            base_ttl_ms: Base TTL in milliseconds (default: 5 seconds)
            jitter_range_ms: Jitter range in milliseconds (default: ±1 second)
            enable_clustering_prevention: Enable jitter by default
        """
        self.cache = valkey_client
        self.base_ttl_ms = base_ttl_ms
        self.jitter_range_ms = jitter_range_ms
        self.enable_clustering_prevention = enable_clustering_prevention
        
        # Statistics tracking
        self.stats = TTLDistributionStats()
        self._expiration_history: List[TTLDistributionModel] = []
        self._performance_metrics: Dict[str, List[float]] = defaultdict(list)
        
        logger.info(
            f"TTLOptimizer initialized with base_ttl={base_ttl_ms}ms, "
            f"jitter_range=±{jitter_range_ms}ms, clustering_prevention={enable_clustering_prevention}"
        )
    
    def calculate_distributed_ttl(self, base_ttl_seconds: int) -> int:
        """
        Calculate TTL with millisecond-level jitter to prevent clustering.
        
        Args:
            base_ttl_seconds: Base TTL in seconds
            
        Returns:
            int: TTL in milliseconds with jitter applied
        """
        base_ms = base_ttl_seconds * 1000
        
        if not self.enable_clustering_prevention:
            # Return exact second boundary (clustered)
            return base_ms
        
        # Apply random jitter within range
        jitter = random.randint(-self.jitter_range_ms, self.jitter_range_ms)
        final_ttl_ms = base_ms + jitter
        
        # Ensure minimum TTL of 1 second
        final_ttl_ms = max(final_ttl_ms, 1000)
        
        # Track statistics
        self.stats.total_keys += 1
        if jitter == 0:
            self.stats.clustered_expirations += 1
        else:
            self.stats.distributed_expirations += 1
        
        # Update jitter statistics
        abs_jitter = abs(jitter)
        if self.stats.total_keys == 1:
            self.stats.min_jitter_ms = abs_jitter
            self.stats.max_jitter_ms = abs_jitter
            self.stats.avg_jitter_ms = abs_jitter
        else:
            self.stats.min_jitter_ms = min(self.stats.min_jitter_ms, abs_jitter)
            self.stats.max_jitter_ms = max(self.stats.max_jitter_ms, abs_jitter)
            # Running average
            self.stats.avg_jitter_ms = (
                (self.stats.avg_jitter_ms * (self.stats.total_keys - 1) + abs_jitter) 
                / self.stats.total_keys
            )
        
        # Create distribution model
        expiration_time = datetime.now() + timedelta(milliseconds=final_ttl_ms)
        distribution_model = TTLDistributionModel(
            base_ttl_seconds=base_ttl_seconds,
            jitter_range_ms=self.jitter_range_ms,
            calculated_ttl_ms=final_ttl_ms,
            expiration_timestamp=expiration_time,
            distribution_type="normal" if self.enable_clustering_prevention else "clustered"
        )
        
        # Store for analysis
        self._expiration_history.append(distribution_model)
        self.stats.expiration_timeline.append((expiration_time, final_ttl_ms))
        
        return final_ttl_ms
    
    async def set_with_distributed_ttl(
        self, 
        key: str, 
        value: Any, 
        base_ttl_seconds: int,
        use_clustering_prevention: Optional[bool] = None
    ) -> bool:
        """
        Set cache value with distributed TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            base_ttl_seconds: Base TTL in seconds
            use_clustering_prevention: Override clustering prevention setting
            
        Returns:
            bool: True if successful
        """
        start_time = time.time()
        
        # Override clustering prevention if specified
        original_setting = self.enable_clustering_prevention
        if use_clustering_prevention is not None:
            self.enable_clustering_prevention = use_clustering_prevention
        
        try:
            # Calculate distributed TTL
            ttl_ms = self.calculate_distributed_ttl(base_ttl_seconds)
            ttl_seconds = ttl_ms / 1000.0
            
            # Serialize value
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)
            
            # Set with calculated TTL
            await self.cache.ensure_connection()
            
            # Use PSETEX for millisecond precision
            result = self.cache.client.psetex(key, ttl_ms, serialized_value)
            
            # Record performance metrics
            operation_time = (time.time() - start_time) * 1000
            self._performance_metrics["set_operations"].append(operation_time)
            
            logger.debug(
                f"Set key '{key}' with distributed TTL: {ttl_ms}ms "
                f"(base: {base_ttl_seconds}s, jitter: {ttl_ms - base_ttl_seconds * 1000}ms)"
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to set key '{key}' with distributed TTL: {e}")
            return False
        
        finally:
            # Restore original setting
            self.enable_clustering_prevention = original_setting
    
    async def analyze_expiration_patterns(self) -> Dict[str, Any]:
        """
        Analyze TTL distribution patterns and clustering.
        
        Returns:
            Dict[str, Any]: Analysis results including clustering metrics
        """
        if not self._expiration_history:
            return {
                "error": "No expiration data available for analysis",
                "total_keys": 0,
            }
        
        # Group expirations by second boundaries
        expiration_buckets = defaultdict(int)
        jitter_values = []
        
        for dist_model in self._expiration_history:
            # Round to nearest second for clustering analysis
            second_boundary = dist_model.expiration_timestamp.replace(microsecond=0)
            expiration_buckets[second_boundary] += 1
            
            # Calculate jitter from base TTL
            base_ms = dist_model.base_ttl_seconds * 1000
            jitter = dist_model.calculated_ttl_ms - base_ms
            jitter_values.append(abs(jitter))
        
        # Calculate clustering score
        bucket_counts = list(expiration_buckets.values())
        if len(bucket_counts) > 1:
            # Higher standard deviation = more clustering
            clustering_score = statistics.stdev(bucket_counts) / statistics.mean(bucket_counts)
            # Normalize to 0-1 scale (approximate)
            clustering_score = min(clustering_score / 2.0, 1.0)
        else:
            clustering_score = 1.0 if bucket_counts else 0.0
        
        self.stats.clustering_score = clustering_score
        
        # Jitter statistics
        jitter_stats = {}
        if jitter_values:
            jitter_stats = {
                "mean": statistics.mean(jitter_values),
                "median": statistics.median(jitter_values),
                "stdev": statistics.stdev(jitter_values) if len(jitter_values) > 1 else 0.0,
                "min": min(jitter_values),
                "max": max(jitter_values),
            }
        
        # Performance metrics
        perf_stats = {}
        for operation, times in self._performance_metrics.items():
            if times:
                perf_stats[operation] = {
                    "count": len(times),
                    "avg_ms": statistics.mean(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                }
        
        return {
            "distribution_stats": self.stats.to_dict(),
            "clustering_analysis": {
                "total_buckets": len(expiration_buckets),
                "max_bucket_size": max(bucket_counts) if bucket_counts else 0,
                "min_bucket_size": min(bucket_counts) if bucket_counts else 0,
                "avg_bucket_size": statistics.mean(bucket_counts) if bucket_counts else 0,
                "clustering_score": clustering_score,
                "distribution_type": "distributed" if clustering_score < 0.5 else "clustered",
            },
            "jitter_statistics": jitter_stats,
            "performance_metrics": perf_stats,
            "analysis_timestamp": datetime.now().isoformat(),
        }
    
    def generate_ttl_distribution_chart(self, chart_width: int = 60) -> str:
        """
        Generate ASCII chart showing TTL distribution patterns.
        
        Args:
            chart_width: Width of the chart in characters
            
        Returns:
            str: ASCII chart representation
        """
        if not self._expiration_history:
            return "No data available for chart generation"
        
        # Group expirations by time buckets (1-second intervals)
        time_buckets = defaultdict(int)
        min_time = None
        max_time = None
        
        for dist_model in self._expiration_history:
            # Round to nearest second
            bucket_time = dist_model.expiration_timestamp.replace(microsecond=0)
            time_buckets[bucket_time] += 1
            
            if min_time is None or bucket_time < min_time:
                min_time = bucket_time
            if max_time is None or bucket_time > max_time:
                max_time = bucket_time
        
        if not time_buckets or min_time == max_time:
            return "Insufficient data for chart generation"
        
        # Create time range
        current_time = min_time
        chart_data = []
        max_count = max(time_buckets.values())
        
        while current_time <= max_time:
            count = time_buckets.get(current_time, 0)
            chart_data.append((current_time, count))
            current_time += timedelta(seconds=1)
        
        # Generate ASCII chart
        chart_lines = []
        chart_lines.append("TTL Distribution Pattern")
        chart_lines.append("=" * chart_width)
        
        # Chart header
        chart_lines.append(f"Time Range: {min_time.strftime('%H:%M:%S')} - {max_time.strftime('%H:%M:%S')}")
        chart_lines.append(f"Total Keys: {len(self._expiration_history)}")
        chart_lines.append(f"Clustering Score: {self.stats.clustering_score:.3f}")
        chart_lines.append("")
        
        # Chart body
        for time_point, count in chart_data:
            # Calculate bar length
            if max_count > 0:
                bar_length = int((count / max_count) * (chart_width - 20))
            else:
                bar_length = 0
            
            # Create bar
            bar = "█" * bar_length
            time_str = time_point.strftime("%H:%M:%S")
            
            chart_lines.append(f"{time_str} |{bar:<{chart_width-20}} {count:>3}")
        
        # Chart footer
        chart_lines.append("")
        chart_lines.append("Legend:")
        if self.enable_clustering_prevention:
            chart_lines.append("  Normal distribution (jitter applied)")
            chart_lines.append("  Lower clustering score = better distribution")
        else:
            chart_lines.append("  Clustered distribution (no jitter)")
            chart_lines.append("  Higher clustering score = more clustering")
        
        return "\n".join(chart_lines)
    
    async def demonstrate_clustering_vs_distribution(
        self, 
        num_keys: int = 100,
        base_ttl_seconds: int = 5
    ) -> Dict[str, Any]:
        """
        Demonstrate performance difference between clustered and distributed expiration.
        
        Args:
            num_keys: Number of test keys to create
            base_ttl_seconds: Base TTL for test keys
            
        Returns:
            Dict[str, Any]: Comparison results
        """
        logger.info(f"Starting clustering vs distribution demonstration with {num_keys} keys")
        
        # Test clustered expiration (no jitter)
        clustered_start = time.time()
        clustered_keys = []
        
        original_setting = self.enable_clustering_prevention
        self.enable_clustering_prevention = False
        
        try:
            for i in range(num_keys):
                key = f"test:clustered:{i}"
                value = {"test_data": f"clustered_value_{i}", "timestamp": datetime.now().isoformat()}
                await self.set_with_distributed_ttl(key, value, base_ttl_seconds)
                clustered_keys.append(key)
            
            clustered_time = (time.time() - clustered_start) * 1000
            
            # Analyze clustered pattern
            clustered_analysis = await self.analyze_expiration_patterns()
            
            # Reset for distributed test
            self._expiration_history.clear()
            self.stats = TTLDistributionStats()
            self._performance_metrics.clear()
            
            # Test distributed expiration (with jitter)
            self.enable_clustering_prevention = True
            distributed_start = time.time()
            distributed_keys = []
            
            for i in range(num_keys):
                key = f"test:distributed:{i}"
                value = {"test_data": f"distributed_value_{i}", "timestamp": datetime.now().isoformat()}
                await self.set_with_distributed_ttl(key, value, base_ttl_seconds)
                distributed_keys.append(key)
            
            distributed_time = (time.time() - distributed_start) * 1000
            
            # Analyze distributed pattern
            distributed_analysis = await self.analyze_expiration_patterns()
            
            # Cleanup test keys
            await asyncio.gather(
                *[self.cache.client.delete(key) for key in clustered_keys + distributed_keys],
                return_exceptions=True
            )
            
            # Compare results
            comparison = {
                "test_parameters": {
                    "num_keys": num_keys,
                    "base_ttl_seconds": base_ttl_seconds,
                    "jitter_range_ms": self.jitter_range_ms,
                },
                "clustered_results": {
                    "setup_time_ms": clustered_time,
                    "clustering_score": clustered_analysis.get("clustering_analysis", {}).get("clustering_score", 0),
                    "distribution_type": "clustered",
                    "jitter_stats": clustered_analysis.get("jitter_statistics", {}),
                },
                "distributed_results": {
                    "setup_time_ms": distributed_time,
                    "clustering_score": distributed_analysis.get("clustering_analysis", {}).get("clustering_score", 0),
                    "distribution_type": "distributed",
                    "jitter_stats": distributed_analysis.get("jitter_statistics", {}),
                },
                "performance_impact": {
                    "setup_time_difference_ms": distributed_time - clustered_time,
                    "clustering_improvement": (
                        clustered_analysis.get("clustering_analysis", {}).get("clustering_score", 0) -
                        distributed_analysis.get("clustering_analysis", {}).get("clustering_score", 0)
                    ),
                },
                "recommendation": self._generate_recommendation(clustered_analysis, distributed_analysis),
                "demonstration_timestamp": datetime.now().isoformat(),
            }
            
            logger.info(
                f"Demonstration completed. Clustering improvement: "
                f"{comparison['performance_impact']['clustering_improvement']:.3f}"
            )
            
            return comparison
            
        finally:
            # Restore original setting
            self.enable_clustering_prevention = original_setting
    
    def _generate_recommendation(
        self, 
        clustered_analysis: Dict[str, Any], 
        distributed_analysis: Dict[str, Any]
    ) -> str:
        """Generate recommendation based on analysis results."""
        clustered_score = clustered_analysis.get("clustering_analysis", {}).get("clustering_score", 0)
        distributed_score = distributed_analysis.get("clustering_analysis", {}).get("clustering_score", 0)
        
        improvement = clustered_score - distributed_score
        
        if improvement > 0.3:
            return (
                "Significant clustering reduction achieved with TTL distribution. "
                "Recommended for production use to prevent cache stampedes."
            )
        elif improvement > 0.1:
            return (
                "Moderate clustering reduction achieved. "
                "Consider using TTL distribution for high-traffic applications."
            )
        else:
            return (
                "Minimal clustering detected. "
                "TTL distribution may not be necessary for this use case."
            )
    
    async def get_current_stats(self) -> Dict[str, Any]:
        """
        Get current TTL optimizer statistics.
        
        Returns:
            Dict[str, Any]: Current statistics and metrics
        """
        return {
            "configuration": {
                "base_ttl_ms": self.base_ttl_ms,
                "jitter_range_ms": self.jitter_range_ms,
                "clustering_prevention_enabled": self.enable_clustering_prevention,
            },
            "statistics": self.stats.to_dict(),
            "history_size": len(self._expiration_history),
            "performance_metrics": {
                operation: {
                    "count": len(times),
                    "avg_ms": statistics.mean(times) if times else 0,
                }
                for operation, times in self._performance_metrics.items()
            },
        }
    
    def reset_stats(self) -> None:
        """Reset all statistics and history."""
        self.stats = TTLDistributionStats()
        self._expiration_history.clear()
        self._performance_metrics.clear()
        logger.info("TTL optimizer statistics reset")
    
    def configure_jitter(self, jitter_range_ms: int) -> None:
        """
        Configure jitter range.
        
        Args:
            jitter_range_ms: New jitter range in milliseconds
        """
        old_range = self.jitter_range_ms
        self.jitter_range_ms = max(0, jitter_range_ms)
        logger.info(f"Jitter range updated from ±{old_range}ms to ±{self.jitter_range_ms}ms")
    
    def toggle_clustering_prevention(self) -> bool:
        """
        Toggle clustering prevention on/off.
        
        Returns:
            bool: New clustering prevention state
        """
        self.enable_clustering_prevention = not self.enable_clustering_prevention
        logger.info(f"Clustering prevention {'enabled' if self.enable_clustering_prevention else 'disabled'}")
        return self.enable_clustering_prevention


# Factory function for creating TTL optimizer instances
async def create_ttl_optimizer(
    valkey_client: Optional[ValkeyClient] = None,
    config: Optional[ValkeyConfig] = None,
    **kwargs
) -> TTLOptimizer:
    """
    Create and initialize TTL optimizer instance.
    
    Args:
        valkey_client: Optional ValkeyClient instance
        config: Optional ValkeyConfig
        **kwargs: Additional TTLOptimizer arguments
        
    Returns:
        TTLOptimizer: Initialized optimizer instance
    """
    if not valkey_client:
        from ..cache.client import get_client
        valkey_client = await get_client(config or ValkeyConfig.from_env())
    
    optimizer = TTLOptimizer(valkey_client, **kwargs)
    logger.info("TTL optimizer created and ready for use")
    return optimizer