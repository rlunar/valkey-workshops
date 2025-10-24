"""Main routes for the Flask caching demo."""

import time
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func
from app import db
from app.models import Product, Category
from app.cache import cache_manager, CacheStrategies

# Create blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page with cache statistics display."""
    # Get cache statistics
    cache_stats = cache_manager.get_stats()
    
    # Get basic database statistics with caching
    def get_db_stats():
        product_count = db.session.query(func.count(Product.id)).scalar()
        category_count = db.session.query(func.count(Category.id)).scalar()
        return {
            'total_products': product_count,
            'total_categories': category_count
        }
    
    db_stats = cache_manager.get_or_set(
        'stats:database_counts',
        get_db_stats,
        timeout=300  # Cache for 5 minutes
    )
    
    return render_template('index.html', 
                         cache_stats=cache_stats, 
                         db_stats=db_stats)


@main_bp.route('/products')
def products():
    """Product listing with query result caching."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category_id = request.args.get('category', type=int)
    
    # Generate cache key based on pagination and filters
    cache_key = f"products:list:page_{page}:per_page_{per_page}"
    if category_id:
        cache_key += f":category_{category_id}"
    
    def get_products_data():
        """Fetch products from database with pagination."""
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
        }
    
    # Cache the query results for 5 minutes
    products_data = cache_manager.get_or_set(
        cache_key,
        get_products_data,
        timeout=300
    )
    
    # Get categories for filter dropdown (cached separately)
    def get_categories():
        return [{'id': cat.id, 'name': cat.name} 
                for cat in Category.query.order_by(Category.name).all()]
    
    categories = cache_manager.get_or_set(
        'categories:all',
        get_categories,
        timeout=600  # Cache categories for 10 minutes
    )
    
    return render_template('products.html', 
                         products_data=products_data,
                         categories=categories,
                         current_category=category_id)


@main_bp.route('/products/<int:product_id>')
def product_detail(product_id):
    """Individual product page with item caching."""
    cache_key = f"product:detail:{product_id}"
    
    def get_product_data():
        """Fetch individual product with category information."""
        product = Product.query.get_or_404(product_id)
        return product.to_dict()
    
    # Cache individual product for 10 minutes
    product_data = cache_manager.get_or_set(
        cache_key,
        get_product_data,
        timeout=600
    )
    
    # Get related products from same category (cached)
    def get_related_products():
        """Get related products from the same category."""
        if not product_data.get('category_id'):
            return []
        
        related = Product.query.filter(
            Product.category_id == product_data['category_id'],
            Product.id != product_id
        ).limit(4).all()
        
        return [p.to_dict() for p in related]
    
    related_cache_key = f"product:related:{product_id}"
    related_products = cache_manager.get_or_set(
        related_cache_key,
        get_related_products,
        timeout=600
    )
    
    return render_template('product_detail.html', 
                         product=product_data,
                         related_products=related_products)


@main_bp.route('/stats')
def cache_stats():
    """Detailed cache statistics page."""
    # Get comprehensive cache statistics
    cache_stats = cache_manager.get_stats()
    
    # Get cache key information if Redis/Valkey is available
    cache_keys = []
    try:
        from app import cache
        if hasattr(cache.cache, '_write_client'):
            redis_client = cache.cache._write_client
            # Get sample of cache keys
            all_keys = redis_client.keys('*')[:50]  # Limit to first 50 keys
            for key in all_keys:
                try:
                    ttl = redis_client.ttl(key)
                    key_type = redis_client.type(key).decode('utf-8')
                    cache_keys.append({
                        'key': key.decode('utf-8') if isinstance(key, bytes) else key,
                        'ttl': ttl,
                        'type': key_type
                    })
                except Exception:
                    pass
    except Exception:
        pass  # Redis not available or error occurred
    
    return render_template('stats.html', 
                         cache_stats=cache_stats,
                         cache_keys=cache_keys)


@main_bp.route('/clear-cache', methods=['GET', 'POST'])
def clear_cache():
    """Manual cache invalidation with pattern support."""
    if request.method == 'POST':
        pattern = request.form.get('pattern', '*')
        
        if pattern == 'all':
            # Clear all cache
            try:
                from app import cache
                cache.clear()
                cache_manager.reset_stats()
                deleted_count = 'all'
                flash(f'All cache cleared successfully!', 'success')
            except Exception as e:
                flash(f'Error clearing cache: {e}', 'error')
                deleted_count = 0
        else:
            # Clear specific pattern
            deleted_count = cache_manager.invalidate(pattern)
            if deleted_count > 0:
                flash(f'Cleared {deleted_count} cache keys matching pattern: {pattern}', 'success')
            else:
                flash(f'No cache keys found matching pattern: {pattern}', 'info')
        
        return redirect(url_for('main.clear_cache'))
    
    # GET request - show the form
    return render_template('cache_clear.html')


@main_bp.route('/warm-cache')
def warm_cache():
    """Cache warming trigger for frequently accessed data."""
    warming_stats = {
        'products_warmed': 0,
        'categories_warmed': 0,
        'errors': 0,
        'duration': 0
    }
    
    start_time = time.time()
    
    try:
        # Warm product cache
        def get_all_products():
            return [p.to_dict() for p in Product.query.all()]
        
        def product_key_generator(product):
            return f"product:detail:{product['id']}"
        
        product_warming = cache_manager.warm_cache(
            get_all_products,
            product_key_generator,
            timeout=600
        )
        warming_stats['products_warmed'] = product_warming['items_cached']
        warming_stats['errors'] += product_warming['errors']
        
        # Warm categories cache
        def get_all_categories():
            return [{'id': cat.id, 'name': cat.name} 
                   for cat in Category.query.all()]
        
        categories = get_all_categories()
        CacheStrategies.medium_term_cache('categories:all', categories)
        warming_stats['categories_warmed'] = len(categories)
        
        # Warm common product listings
        for page in range(1, 4):  # Warm first 3 pages
            cache_key = f"products:list:page_{page}:per_page_10"
            
            def get_page_data():
                query = Product.query.order_by(Product.created_at.desc())
                pagination = query.paginate(page=page, per_page=10, error_out=False)
                return {
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
                }
            
            cache_manager.get_or_set(cache_key, get_page_data, timeout=300)
        
        warming_stats['duration'] = time.time() - start_time
        flash(f'Cache warming completed! Products: {warming_stats["products_warmed"]}, '
              f'Categories: {warming_stats["categories_warmed"]}, '
              f'Duration: {warming_stats["duration"]:.2f}s', 'success')
        
    except Exception as e:
        warming_stats['errors'] += 1
        warming_stats['duration'] = time.time() - start_time
        flash(f'Cache warming failed: {e}', 'error')
    
    return redirect(url_for('main.cache_stats'))