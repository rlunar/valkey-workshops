"""Custom debug toolbar panels for cache monitoring."""

import time
from flask import current_app, request, g
from flask_debugtoolbar.panels import DebugPanel
from app.cache import cache_manager
from app import flask_cache as cache


class CachePanel(DebugPanel):
    """Debug panel for monitoring cache operations and statistics."""
    
    name = 'Cache'
    has_content = True
    
    def __init__(self, jinja_env, context={}):
        super().__init__(jinja_env, context)
        self.cache_operations = []
        self.request_start_time = None
        
    def nav_title(self):
        """Title shown in the debug toolbar navigation."""
        return 'Cache'
    
    def nav_subtitle(self):
        """Subtitle showing cache hit/miss ratio for this request."""
        if hasattr(g, 'cache_stats'):
            hits = g.cache_stats.get('hits', 0)
            misses = g.cache_stats.get('misses', 0)
            total = hits + misses
            if total > 0:
                hit_rate = (hits / total) * 100
                return f'{hits}H/{misses}M ({hit_rate:.1f}%)'
        return 'No operations'
    
    def title(self):
        """Panel title in the detailed view."""
        return 'Cache Operations'
    
    def url(self):
        """URL for the panel (not used in this implementation)."""
        return ''
    
    def content(self):
        """Generate the HTML content for the cache panel."""
        # Get current cache statistics
        cache_stats = cache_manager.get_stats()
        
        # Get request-specific cache operations if available
        request_operations = getattr(g, 'cache_operations', [])
        request_stats = getattr(g, 'cache_stats', {})
        
        # Get cache configuration
        cache_config = {
            'type': current_app.config.get('CACHE_TYPE', 'unknown'),
            'redis_url': current_app.config.get('CACHE_REDIS_URL', 'N/A'),
            'default_timeout': current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300),
            'key_prefix': current_app.config.get('CACHE_KEY_PREFIX', ''),
        }
        
        # Try to get cache keys if Redis/Valkey is available
        cache_keys = []
        try:
            if hasattr(cache.cache, '_write_client'):
                redis_client = cache.cache._write_client
                pattern = f"{cache_config['key_prefix']}*"
                keys = redis_client.keys(pattern)
                cache_keys = [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys[:50]]  # Limit to 50 keys
        except Exception:
            pass
        
        context = {
            'cache_stats': cache_stats,
            'request_stats': request_stats,
            'request_operations': request_operations,
            'cache_config': cache_config,
            'cache_keys': cache_keys,
            'total_keys': len(cache_keys)
        }
        
        return self.render('panels/cache.html', context)


class CacheKeyInspectorPanel(DebugPanel):
    """Debug panel for inspecting cache keys and their values."""
    
    name = 'CacheKeys'
    has_content = True
    
    def nav_title(self):
        """Title shown in the debug toolbar navigation."""
        return 'Cache Keys'
    
    def nav_subtitle(self):
        """Subtitle showing number of cache keys."""
        try:
            if hasattr(cache.cache, '_write_client'):
                redis_client = cache.cache._write_client
                key_prefix = current_app.config.get('CACHE_KEY_PREFIX', '')
                pattern = f"{key_prefix}*"
                key_count = len(redis_client.keys(pattern))
                return f'{key_count} keys'
        except Exception:
            pass
        return 'N/A'
    
    def title(self):
        """Panel title in the detailed view."""
        return 'Cache Key Inspector'
    
    def url(self):
        """URL for the panel (not used in this implementation)."""
        return ''
    
    def content(self):
        """Generate the HTML content for the cache key inspector panel."""
        cache_data = []
        
        try:
            if hasattr(cache.cache, '_write_client'):
                redis_client = cache.cache._write_client
                key_prefix = current_app.config.get('CACHE_KEY_PREFIX', '')
                pattern = f"{key_prefix}*"
                keys = redis_client.keys(pattern)
                
                for key in keys[:100]:  # Limit to 100 keys for performance
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    try:
                        # Get value and TTL
                        value = redis_client.get(key)
                        ttl = redis_client.ttl(key)
                        
                        # Try to decode value
                        if value:
                            try:
                                # Flask-Caching uses pickle by default
                                import pickle
                                decoded_value = pickle.loads(value)
                                value_preview = str(decoded_value)[:200] + ('...' if len(str(decoded_value)) > 200 else '')
                                value_type = type(decoded_value).__name__
                            except Exception:
                                # If pickle fails, show raw value
                                value_preview = str(value)[:200] + ('...' if len(str(value)) > 200 else '')
                                value_type = 'raw'
                        else:
                            value_preview = 'None'
                            value_type = 'None'
                        
                        cache_data.append({
                            'key': key_str,
                            'value_preview': value_preview,
                            'value_type': value_type,
                            'ttl': ttl if ttl > 0 else 'No expiration',
                            'size': len(value) if value else 0
                        })
                    except Exception as e:
                        cache_data.append({
                            'key': key_str,
                            'value_preview': f'Error: {str(e)}',
                            'value_type': 'error',
                            'ttl': 'N/A',
                            'size': 0
                        })
        except Exception as e:
            cache_data = [{'error': f'Unable to connect to cache: {str(e)}'}]
        
        context = {
            'cache_data': cache_data,
            'total_keys': len(cache_data)
        }
        
        return self.render('panels/cache_keys.html', context)


class DatabaseQueryPanel(DebugPanel):
    """Enhanced database query panel with cache correlation."""
    
    name = 'DatabaseQueries'
    has_content = True
    
    def __init__(self, jinja_env, context={}):
        super().__init__(jinja_env, context)
        self.queries = []
        
    def nav_title(self):
        """Title shown in the debug toolbar navigation."""
        return 'DB Queries'
    
    def nav_subtitle(self):
        """Subtitle showing query count and total time."""
        if hasattr(g, 'db_queries'):
            query_count = len(g.db_queries)
            total_time = sum(q.get('duration', 0) for q in g.db_queries)
            return f'{query_count} queries ({total_time:.2f}ms)'
        return 'No queries'
    
    def title(self):
        """Panel title in the detailed view."""
        return 'Database Queries with Cache Correlation'
    
    def url(self):
        """URL for the panel (not used in this implementation)."""
        return ''
    
    def content(self):
        """Generate the HTML content for the database query panel."""
        queries = getattr(g, 'db_queries', [])
        cache_operations = getattr(g, 'cache_operations', [])
        
        # Correlate queries with cache operations by timestamp
        for query in queries:
            query['related_cache_ops'] = []
            query_time = query.get('start_time', 0)
            
            for cache_op in cache_operations:
                cache_time = cache_op.get('timestamp', 0)
                # If cache operation happened within 100ms of query
                if abs(cache_time - query_time) < 0.1:
                    query['related_cache_ops'].append(cache_op)
        
        context = {
            'queries': queries,
            'total_queries': len(queries),
            'total_time': sum(q.get('duration', 0) for q in queries),
            'cache_operations': cache_operations
        }
        
        return self.render('panels/database_queries.html', context)


def init_debug_panels(app):
    """Initialize custom debug panels with the Flask app."""
    
    if app.config.get('DEBUG_TB_ENABLED', False):
        # Add custom panels to debug toolbar
        app.config.setdefault('DEBUG_TB_PANELS', [])
        
        # Remove default panels we're replacing and add our custom ones
        default_panels = app.config['DEBUG_TB_PANELS']
        
        # Add our custom panels
        custom_panels = [
            'app.debug_panels.CachePanel',
            'app.debug_panels.CacheKeyInspectorPanel',
            'app.debug_panels.DatabaseQueryPanel',
        ]
        
        # Combine with existing panels, avoiding duplicates
        all_panels = list(default_panels) + [panel for panel in custom_panels if panel not in default_panels]
        app.config['DEBUG_TB_PANELS'] = all_panels
        
        # Set up request hooks for collecting debug information
        setup_debug_hooks(app)


def setup_debug_hooks(app):
    """Set up Flask hooks to collect debug information for panels."""
    
    @app.before_request
    def before_request():
        """Initialize debug tracking for the request."""
        g.cache_operations = []
        g.cache_stats = {'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0}
        g.db_queries = []
        g.request_start_time = time.time()
    
    @app.after_request
    def after_request(response):
        """Finalize debug information after request."""
        if hasattr(g, 'request_start_time'):
            g.request_duration = time.time() - g.request_start_time
        return response


# Monkey patch cache manager to track operations for debug panel
original_get_or_set = cache_manager.get_or_set
original_invalidate = cache_manager.invalidate
original_set_with_expiry = cache_manager.set_with_expiry

def track_cache_operation(operation_type, key, result=None, duration=None):
    """Track cache operations for debug panel."""
    if hasattr(g, 'cache_operations'):
        g.cache_operations.append({
            'operation': operation_type,
            'key': key,
            'result': result,
            'timestamp': time.time(),
            'duration': duration
        })
    
    if hasattr(g, 'cache_stats'):
        if operation_type == 'hit':
            g.cache_stats['hits'] += 1
        elif operation_type == 'miss':
            g.cache_stats['misses'] += 1
        elif operation_type == 'set':
            g.cache_stats['sets'] += 1
        elif operation_type == 'delete':
            g.cache_stats['deletes'] += 1

def patched_get_or_set(key, callable_func, timeout=300):
    """Patched version of get_or_set that tracks operations."""
    start_time = time.time()
    
    try:
        # Try to get from cache first
        cached_value = cache.get(key)
        if cached_value is not None:
            duration = (time.time() - start_time) * 1000  # Convert to ms
            track_cache_operation('hit', key, 'cached', duration)
            return cached_value
        
        # Cache miss
        track_cache_operation('miss', key, 'computed')
        result = original_get_or_set(key, callable_func, timeout)
        
        duration = (time.time() - start_time) * 1000  # Convert to ms
        track_cache_operation('set', key, 'stored', duration)
        
        return result
    except Exception as e:
        duration = (time.time() - start_time) * 1000  # Convert to ms
        track_cache_operation('error', key, str(e), duration)
        raise

def patched_invalidate(pattern):
    """Patched version of invalidate that tracks operations."""
    start_time = time.time()
    result = original_invalidate(pattern)
    duration = (time.time() - start_time) * 1000  # Convert to ms
    track_cache_operation('delete', pattern, f'{result} keys deleted', duration)
    return result

def patched_set_with_expiry(key, value, timeout=None):
    """Patched version of set_with_expiry that tracks operations."""
    start_time = time.time()
    result = original_set_with_expiry(key, value, timeout)
    duration = (time.time() - start_time) * 1000  # Convert to ms
    track_cache_operation('set', key, 'stored' if result else 'failed', duration)
    return result

# Apply patches
cache_manager.get_or_set = patched_get_or_set
cache_manager.invalidate = patched_invalidate
cache_manager.set_with_expiry = patched_set_with_expiry