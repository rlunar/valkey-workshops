"""API routes for the Flask caching demo."""

import time
import random
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import func
from app import db
from app.models import Product, Category
from app.cache import cache_manager, CacheStrategies

# Create blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/products')
def api_products():
    """JSON API endpoint for products with response caching."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category_id = request.args.get('category', type=int)
    
    # Generate cache key for API response
    cache_key = f"api:products:page_{page}:per_page_{per_page}"
    if category_id:
        cache_key += f":category_{category_id}"
    
    def get_api_products_data():
        """Fetch products data for API response."""
        query = Product.query
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        # Order by created_at descending for consistent pagination
        query = query.order_by(Product.created_at.desc())
        
        # Get paginated results
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return {
            'success': True,
            'data': {
                'products': [product.to_dict() for product in pagination.items],
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_prev': pagination.has_prev,
                    'has_next': pagination.has_next,
                    'prev_num': pagination.prev_num,
                    'next_num': pagination.next_num
                }
            },
            'cache_info': {
                'cached_at': time.time(),
                'cache_key': cache_key
            }
        }
    
    # Cache API response for 5 minutes
    response_data = cache_manager.get_or_set(
        cache_key,
        get_api_products_data,
        timeout=300
    )
    
    # Add cache metadata to response
    response_data['cache_info']['served_from_cache'] = True
    response_data['cache_info']['served_at'] = time.time()
    
    return jsonify(response_data)


@api_bp.route('/products/<int:product_id>')
def api_product_detail(product_id):
    """JSON API endpoint for individual product with caching."""
    cache_key = f"api:product:detail:{product_id}"
    
    def get_api_product_data():
        """Fetch individual product data for API response."""
        product = Product.query.get(product_id)
        
        if not product:
            return {
                'success': False,
                'error': 'Product not found',
                'data': None
            }
        
        return {
            'success': True,
            'data': {
                'product': product.to_dict()
            },
            'cache_info': {
                'cached_at': time.time(),
                'cache_key': cache_key
            }
        }
    
    # Cache individual product API response for 10 minutes
    response_data = cache_manager.get_or_set(
        cache_key,
        get_api_product_data,
        timeout=600
    )
    
    # Add cache metadata
    response_data['cache_info']['served_from_cache'] = True
    response_data['cache_info']['served_at'] = time.time()
    
    # Return 404 if product not found
    if not response_data['success']:
        return jsonify(response_data), 404
    
    return jsonify(response_data)


@api_bp.route('/categories')
def api_categories():
    """JSON API endpoint for categories with caching."""
    cache_key = "api:categories:all"
    
    def get_api_categories_data():
        """Fetch categories data for API response."""
        categories = Category.query.order_by(Category.name).all()
        
        return {
            'success': True,
            'data': {
                'categories': [
                    {
                        'id': cat.id,
                        'name': cat.name,
                        'description': cat.description,
                        'product_count': len(cat.products)
                    }
                    for cat in categories
                ]
            },
            'cache_info': {
                'cached_at': time.time(),
                'cache_key': cache_key
            }
        }
    
    # Cache categories API response for 15 minutes
    response_data = cache_manager.get_or_set(
        cache_key,
        get_api_categories_data,
        timeout=900
    )
    
    # Add cache metadata
    response_data['cache_info']['served_from_cache'] = True
    response_data['cache_info']['served_at'] = time.time()
    
    return jsonify(response_data)


@api_bp.route('/expensive-operation')
def expensive_operation():
    """Simulated expensive operation with caching demonstration."""
    # Get operation type from query parameter
    operation_type = request.args.get('type', 'calculation')
    complexity = request.args.get('complexity', 'medium')
    
    cache_key = f"api:expensive_operation:{operation_type}:{complexity}"
    
    def perform_expensive_operation():
        """Simulate an expensive computational operation."""
        current_app.logger.info(f"Performing expensive {operation_type} operation with {complexity} complexity")
        
        # Simulate different types of expensive operations
        if operation_type == 'calculation':
            # Simulate complex mathematical calculation
            start_time = time.time()
            
            if complexity == 'low':
                time.sleep(0.5)  # 500ms delay
                result = sum(i ** 2 for i in range(1000))
            elif complexity == 'high':
                time.sleep(2.0)  # 2 second delay
                result = sum(i ** 3 for i in range(5000))
            else:  # medium
                time.sleep(1.0)  # 1 second delay
                result = sum(i ** 2 for i in range(2500))
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'data': {
                    'operation_type': 'mathematical_calculation',
                    'complexity': complexity,
                    'result': result,
                    'processing_time_seconds': round(processing_time, 3),
                    'computed_at': time.time()
                }
            }
        
        elif operation_type == 'database_aggregation':
            # Simulate expensive database aggregation
            start_time = time.time()
            
            # Perform actual database operations that could be expensive
            total_products = db.session.query(func.count(Product.id)).scalar()
            avg_price = db.session.query(func.avg(Product.price)).scalar()
            max_price = db.session.query(func.max(Product.price)).scalar()
            min_price = db.session.query(func.min(Product.price)).scalar()
            
            # Simulate additional processing time
            if complexity == 'low':
                time.sleep(0.3)
            elif complexity == 'high':
                time.sleep(1.5)
            else:  # medium
                time.sleep(0.8)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'data': {
                    'operation_type': 'database_aggregation',
                    'complexity': complexity,
                    'result': {
                        'total_products': total_products,
                        'average_price': float(avg_price) if avg_price else 0,
                        'max_price': float(max_price) if max_price else 0,
                        'min_price': float(min_price) if min_price else 0
                    },
                    'processing_time_seconds': round(processing_time, 3),
                    'computed_at': time.time()
                }
            }
        
        elif operation_type == 'external_api_simulation':
            # Simulate external API call
            start_time = time.time()
            
            # Simulate network latency and processing
            if complexity == 'low':
                time.sleep(0.4)
            elif complexity == 'high':
                time.sleep(1.8)
            else:  # medium
                time.sleep(1.2)
            
            # Generate some random data to simulate API response
            random_data = {
                'weather': {
                    'temperature': random.randint(15, 35),
                    'humidity': random.randint(30, 90),
                    'conditions': random.choice(['sunny', 'cloudy', 'rainy', 'partly_cloudy'])
                },
                'stock_prices': [
                    {'symbol': 'AAPL', 'price': round(random.uniform(150, 200), 2)},
                    {'symbol': 'GOOGL', 'price': round(random.uniform(2500, 3000), 2)},
                    {'symbol': 'MSFT', 'price': round(random.uniform(300, 400), 2)}
                ]
            }
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'data': {
                    'operation_type': 'external_api_simulation',
                    'complexity': complexity,
                    'result': random_data,
                    'processing_time_seconds': round(processing_time, 3),
                    'computed_at': time.time()
                }
            }
        
        else:
            return {
                'success': False,
                'error': f'Unknown operation type: {operation_type}',
                'data': None
            }
    
    # Cache expensive operation result for different durations based on complexity
    if complexity == 'low':
        timeout = 120  # 2 minutes for low complexity
    elif complexity == 'high':
        timeout = 600  # 10 minutes for high complexity
    else:  # medium
        timeout = 300  # 5 minutes for medium complexity
    
    response_data = cache_manager.get_or_set(
        cache_key,
        perform_expensive_operation,
        timeout=timeout
    )
    
    # Add cache metadata
    if 'data' in response_data and response_data['data']:
        response_data['cache_info'] = {
            'cache_key': cache_key,
            'served_from_cache': True,
            'served_at': time.time(),
            'cache_timeout_seconds': timeout
        }
    
    return jsonify(response_data)


@api_bp.route('/stats')
def api_cache_stats():
    """JSON API endpoint for cache statistics."""
    cache_key = "api:cache_stats"
    
    def get_cache_stats_data():
        """Get comprehensive cache statistics for API."""
        stats = cache_manager.get_stats()
        
        # Add API-specific statistics
        api_stats = {
            'cache_performance': stats,
            'api_endpoints': {
                'products': '/api/products',
                'product_detail': '/api/products/<id>',
                'categories': '/api/categories',
                'expensive_operation': '/api/expensive-operation',
                'cache_stats': '/api/stats'
            },
            'cache_strategies': {
                'products_list': 'Cache for 5 minutes with pagination support',
                'product_detail': 'Cache for 10 minutes per product',
                'categories': 'Cache for 15 minutes (relatively static)',
                'expensive_operations': 'Variable timeout based on complexity'
            }
        }
        
        return {
            'success': True,
            'data': api_stats,
            'cache_info': {
                'cached_at': time.time(),
                'cache_key': cache_key
            }
        }
    
    # Cache stats for 30 seconds (frequently changing data)
    response_data = cache_manager.get_or_set(
        cache_key,
        get_cache_stats_data,
        timeout=30
    )
    
    # Add cache metadata
    response_data['cache_info']['served_from_cache'] = True
    response_data['cache_info']['served_at'] = time.time()
    
    return jsonify(response_data)


@api_bp.route('/health')
def api_health():
    """Health check endpoint (not cached for real-time status)."""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    try:
        # Test cache connection
        test_key = 'health_check_test'
        cache_manager.set_with_expiry(test_key, 'test_value', timeout=10)
        cached_value = cache_manager.get_or_set(test_key, lambda: 'test_value', timeout=10)
        cache_status = 'healthy' if cached_value == 'test_value' else 'error'
    except Exception as e:
        cache_status = f'error: {str(e)}'
    
    health_data = {
        'success': True,
        'data': {
            'status': 'healthy' if db_status == 'healthy' and cache_status == 'healthy' else 'degraded',
            'timestamp': time.time(),
            'services': {
                'database': db_status,
                'cache': cache_status
            },
            'version': '1.0.0'
        }
    }
    
    # Return appropriate HTTP status code
    status_code = 200 if health_data['data']['status'] == 'healthy' else 503
    
    return jsonify(health_data), status_code


# Cache Management API Endpoints

@api_bp.route('/cache/invalidate', methods=['POST'])
def api_cache_invalidate():
    """API endpoint for cache invalidation with pattern support."""
    try:
        data = request.get_json() or {}
        pattern = data.get('pattern', '*')
        cache_type = data.get('type', 'pattern')  # 'pattern', 'key', or 'all'
        
        if cache_type == 'all':
            # Clear all cache
            from app import flask_cache as cache
            cache.clear()
            cache_manager.reset_stats()
            
            return jsonify({
                'success': True,
                'data': {
                    'message': 'All cache cleared successfully',
                    'invalidated_count': 'all',
                    'pattern': 'all'
                }
            })
        
        elif cache_type == 'key':
            # Invalidate specific key
            key = data.get('key')
            if not key:
                return jsonify({
                    'success': False,
                    'error': 'Key is required for key-based invalidation'
                }), 400
            
            result = cache_manager.invalidate_key(key)
            
            return jsonify({
                'success': True,
                'data': {
                    'message': f'Cache key {"invalidated" if result else "not found"}',
                    'key': key,
                    'invalidated': result
                }
            })
        
        else:  # pattern-based invalidation
            deleted_count = cache_manager.invalidate(pattern)
            
            return jsonify({
                'success': True,
                'data': {
                    'message': f'Invalidated {deleted_count} cache keys',
                    'pattern': pattern,
                    'invalidated_count': deleted_count
                }
            })
    
    except Exception as e:
        current_app.logger.error(f"Cache invalidation error: {e}")
        return jsonify({
            'success': False,
            'error': f'Cache invalidation failed: {str(e)}'
        }), 500


@api_bp.route('/cache/refresh', methods=['POST'])
def api_cache_refresh():
    """API endpoint for refreshing specific cache entries."""
    try:
        data = request.get_json() or {}
        endpoint = data.get('endpoint')
        params = data.get('params', {})
        
        if not endpoint:
            return jsonify({
                'success': False,
                'error': 'Endpoint is required for cache refresh'
            }), 400
        
        refreshed_keys = []
        
        if endpoint == 'products':
            # Refresh products cache
            page = params.get('page', 1)
            per_page = params.get('per_page', 10)
            category_id = params.get('category')
            
            cache_key = f"api:products:page_{page}:per_page_{per_page}"
            if category_id:
                cache_key += f":category_{category_id}"
            
            # Invalidate old cache
            cache_manager.invalidate_key(cache_key)
            
            # Refresh by making a new request (this will populate cache)
            query = Product.query
            if category_id:
                query = query.filter(Product.category_id == category_id)
            
            query = query.order_by(Product.created_at.desc())
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            fresh_data = {
                'success': True,
                'data': {
                    'products': [product.to_dict() for product in pagination.items],
                    'pagination': {
                        'page': pagination.page,
                        'pages': pagination.pages,
                        'per_page': pagination.per_page,
                        'total': pagination.total,
                        'has_prev': pagination.has_prev,
                        'has_next': pagination.has_next,
                        'prev_num': pagination.prev_num,
                        'next_num': pagination.next_num
                    }
                },
                'cache_info': {
                    'cached_at': time.time(),
                    'cache_key': cache_key
                }
            }
            
            # Store fresh data in cache
            cache_manager.set_with_expiry(cache_key, fresh_data, timeout=300)
            refreshed_keys.append(cache_key)
        
        elif endpoint == 'categories':
            # Refresh categories cache
            cache_key = "api:categories:all"
            
            # Invalidate old cache
            cache_manager.invalidate_key(cache_key)
            
            # Get fresh data
            categories = Category.query.order_by(Category.name).all()
            fresh_data = {
                'success': True,
                'data': {
                    'categories': [
                        {
                            'id': cat.id,
                            'name': cat.name,
                            'description': cat.description,
                            'product_count': len(cat.products)
                        }
                        for cat in categories
                    ]
                },
                'cache_info': {
                    'cached_at': time.time(),
                    'cache_key': cache_key
                }
            }
            
            # Store fresh data in cache
            cache_manager.set_with_expiry(cache_key, fresh_data, timeout=900)
            refreshed_keys.append(cache_key)
        
        elif endpoint == 'product_detail':
            # Refresh specific product cache
            product_id = params.get('product_id')
            if not product_id:
                return jsonify({
                    'success': False,
                    'error': 'product_id is required for product detail refresh'
                }), 400
            
            cache_key = f"api:product:detail:{product_id}"
            
            # Invalidate old cache
            cache_manager.invalidate_key(cache_key)
            
            # Get fresh data
            product = Product.query.get(product_id)
            if product:
                fresh_data = {
                    'success': True,
                    'data': {
                        'product': product.to_dict()
                    },
                    'cache_info': {
                        'cached_at': time.time(),
                        'cache_key': cache_key
                    }
                }
                
                # Store fresh data in cache
                cache_manager.set_with_expiry(cache_key, fresh_data, timeout=600)
                refreshed_keys.append(cache_key)
            else:
                return jsonify({
                    'success': False,
                    'error': f'Product with id {product_id} not found'
                }), 404
        
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown endpoint: {endpoint}'
            }), 400
        
        return jsonify({
            'success': True,
            'data': {
                'message': f'Cache refreshed for {endpoint}',
                'endpoint': endpoint,
                'refreshed_keys': refreshed_keys,
                'refresh_count': len(refreshed_keys)
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"Cache refresh error: {e}")
        return jsonify({
            'success': False,
            'error': f'Cache refresh failed: {str(e)}'
        }), 500


@api_bp.route('/cache/version', methods=['GET', 'POST'])
def api_cache_version():
    """API endpoint for cache versioning management."""
    if request.method == 'GET':
        # Get current cache version information
        try:
            version_key = "cache:version:api"
            current_version = cache_manager.get_or_set(
                version_key,
                lambda: {'version': 1, 'created_at': time.time()},
                timeout=3600  # Cache version info for 1 hour
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'current_version': current_version['version'],
                    'version_created_at': current_version['created_at'],
                    'version_key': version_key
                }
            })
        
        except Exception as e:
            current_app.logger.error(f"Cache version retrieval error: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to retrieve cache version: {str(e)}'
            }), 500
    
    else:  # POST - increment cache version
        try:
            data = request.get_json() or {}
            action = data.get('action', 'increment')
            
            version_key = "cache:version:api"
            
            if action == 'increment':
                # Get current version
                current_version = cache_manager.get_or_set(
                    version_key,
                    lambda: {'version': 1, 'created_at': time.time()},
                    timeout=3600
                )
                
                # Increment version
                new_version = {
                    'version': current_version['version'] + 1,
                    'created_at': time.time(),
                    'previous_version': current_version['version']
                }
                
                # Update version in cache
                cache_manager.set_with_expiry(version_key, new_version, timeout=3600)
                
                # Invalidate all versioned cache entries
                versioned_patterns = [
                    "api:products:*",
                    "api:product:*",
                    "api:categories:*",
                    "api:expensive_operation:*"
                ]
                
                total_invalidated = 0
                for pattern in versioned_patterns:
                    invalidated = cache_manager.invalidate(pattern)
                    total_invalidated += invalidated
                
                return jsonify({
                    'success': True,
                    'data': {
                        'message': 'Cache version incremented successfully',
                        'new_version': new_version['version'],
                        'previous_version': new_version['previous_version'],
                        'invalidated_entries': total_invalidated,
                        'version_created_at': new_version['created_at']
                    }
                })
            
            elif action == 'reset':
                # Reset version to 1
                new_version = {
                    'version': 1,
                    'created_at': time.time(),
                    'reset': True
                }
                
                # Clear all cache and reset version
                from app import flask_cache as cache
                cache.clear()
                cache_manager.reset_stats()
                cache_manager.set_with_expiry(version_key, new_version, timeout=3600)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'message': 'Cache version reset to 1 and all cache cleared',
                        'new_version': 1,
                        'version_created_at': new_version['created_at']
                    }
                })
            
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unknown action: {action}. Use "increment" or "reset"'
                }), 400
        
        except Exception as e:
            current_app.logger.error(f"Cache version update error: {e}")
            return jsonify({
                'success': False,
                'error': f'Cache version update failed: {str(e)}'
            }), 500


@api_bp.route('/cache/warm', methods=['POST'])
def api_cache_warm():
    """API endpoint for warming cache with fresh data."""
    try:
        data = request.get_json() or {}
        endpoints = data.get('endpoints', ['products', 'categories'])
        
        warming_results = {
            'total_warmed': 0,
            'endpoints_processed': [],
            'errors': []
        }
        
        for endpoint in endpoints:
            try:
                if endpoint == 'products':
                    # Warm product listings (first 3 pages)
                    for page in range(1, 4):
                        cache_key = f"api:products:page_{page}:per_page_10"
                        
                        query = Product.query.order_by(Product.created_at.desc())
                        pagination = query.paginate(page=page, per_page=10, error_out=False)
                        
                        warm_data = {
                            'success': True,
                            'data': {
                                'products': [product.to_dict() for product in pagination.items],
                                'pagination': {
                                    'page': pagination.page,
                                    'pages': pagination.pages,
                                    'per_page': pagination.per_page,
                                    'total': pagination.total,
                                    'has_prev': pagination.has_prev,
                                    'has_next': pagination.has_next,
                                    'prev_num': pagination.prev_num,
                                    'next_num': pagination.next_num
                                }
                            },
                            'cache_info': {
                                'cached_at': time.time(),
                                'cache_key': cache_key
                            }
                        }
                        
                        cache_manager.set_with_expiry(cache_key, warm_data, timeout=300)
                        warming_results['total_warmed'] += 1
                    
                    # Warm individual products
                    products = Product.query.limit(10).all()  # Warm first 10 products
                    for product in products:
                        cache_key = f"api:product:detail:{product.id}"
                        
                        warm_data = {
                            'success': True,
                            'data': {
                                'product': product.to_dict()
                            },
                            'cache_info': {
                                'cached_at': time.time(),
                                'cache_key': cache_key
                            }
                        }
                        
                        cache_manager.set_with_expiry(cache_key, warm_data, timeout=600)
                        warming_results['total_warmed'] += 1
                    
                    warming_results['endpoints_processed'].append('products')
                
                elif endpoint == 'categories':
                    # Warm categories
                    cache_key = "api:categories:all"
                    
                    categories = Category.query.order_by(Category.name).all()
                    warm_data = {
                        'success': True,
                        'data': {
                            'categories': [
                                {
                                    'id': cat.id,
                                    'name': cat.name,
                                    'description': cat.description,
                                    'product_count': len(cat.products)
                                }
                                for cat in categories
                            ]
                        },
                        'cache_info': {
                            'cached_at': time.time(),
                            'cache_key': cache_key
                        }
                    }
                    
                    cache_manager.set_with_expiry(cache_key, warm_data, timeout=900)
                    warming_results['total_warmed'] += 1
                    warming_results['endpoints_processed'].append('categories')
                
                else:
                    warming_results['errors'].append(f'Unknown endpoint: {endpoint}')
            
            except Exception as e:
                warming_results['errors'].append(f'Error warming {endpoint}: {str(e)}')
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Cache warming completed',
                'total_warmed': warming_results['total_warmed'],
                'endpoints_processed': warming_results['endpoints_processed'],
                'errors': warming_results['errors'],
                'error_count': len(warming_results['errors'])
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"Cache warming error: {e}")
        return jsonify({
            'success': False,
            'error': f'Cache warming failed: {str(e)}'
        }), 500


# Data Update API Endpoints with Cache Invalidation

@api_bp.route('/products', methods=['POST'])
def api_create_product():
    """Create new product with automatic cache invalidation."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data is required'
            }), 400
        
        # Validate required fields
        required_fields = ['name', 'price', 'category_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create new product
        product = Product(
            name=data['name'],
            description=data.get('description', ''),
            price=data['price'],
            category_id=data['category_id']
        )
        
        db.session.add(product)
        db.session.commit()
        
        # Invalidate related caches
        invalidated_patterns = [
            "api:products:*",  # All product listings
            "api:categories:*",  # Categories (product counts changed)
            "api:cache_stats",  # Cache stats
            "products:*",  # Web interface product caches
            "stats:*"  # Statistics caches
        ]
        
        total_invalidated = 0
        for pattern in invalidated_patterns:
            invalidated = cache_manager.invalidate(pattern)
            total_invalidated += invalidated
        
        return jsonify({
            'success': True,
            'data': {
                'product': product.to_dict(),
                'cache_invalidation': {
                    'invalidated_entries': total_invalidated,
                    'patterns': invalidated_patterns
                }
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Product creation error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to create product: {str(e)}'
        }), 500


@api_bp.route('/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    """Update product with automatic cache invalidation."""
    try:
        product = Product.query.get(product_id)
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'JSON data is required'
            }), 400
        
        # Update product fields
        if 'name' in data:
            product.name = data['name']
        if 'description' in data:
            product.description = data['description']
        if 'price' in data:
            product.price = data['price']
        if 'category_id' in data:
            product.category_id = data['category_id']
        
        product.updated_at = db.func.now()
        
        db.session.commit()
        
        # Invalidate related caches
        invalidated_patterns = [
            f"api:product:detail:{product_id}",  # Specific product
            "api:products:*",  # All product listings
            "api:categories:*",  # Categories (if category changed)
            f"product:detail:{product_id}",  # Web interface product cache
            "products:*",  # Web interface product listings
        ]
        
        total_invalidated = 0
        for pattern in invalidated_patterns:
            invalidated = cache_manager.invalidate(pattern)
            total_invalidated += invalidated
        
        return jsonify({
            'success': True,
            'data': {
                'product': product.to_dict(),
                'cache_invalidation': {
                    'invalidated_entries': total_invalidated,
                    'patterns': invalidated_patterns
                }
            }
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Product update error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to update product: {str(e)}'
        }), 500


@api_bp.route('/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    """Delete product with automatic cache invalidation."""
    try:
        product = Product.query.get(product_id)
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
        
        # Store product data for response
        product_data = product.to_dict()
        
        db.session.delete(product)
        db.session.commit()
        
        # Invalidate related caches
        invalidated_patterns = [
            f"api:product:detail:{product_id}",  # Specific product
            "api:products:*",  # All product listings
            "api:categories:*",  # Categories (product counts changed)
            f"product:detail:{product_id}",  # Web interface product cache
            "products:*",  # Web interface product listings
            "stats:*"  # Statistics caches
        ]
        
        total_invalidated = 0
        for pattern in invalidated_patterns:
            invalidated = cache_manager.invalidate(pattern)
            total_invalidated += invalidated
        
        return jsonify({
            'success': True,
            'data': {
                'message': 'Product deleted successfully',
                'deleted_product': product_data,
                'cache_invalidation': {
                    'invalidated_entries': total_invalidated,
                    'patterns': invalidated_patterns
                }
            }
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Product deletion error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete product: {str(e)}'
        }), 500