"""Flask app factory for the caching demo application."""

import os
import time
from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy import event

# Initialize extensions
db = SQLAlchemy()
flask_cache = Cache()
toolbar = DebugToolbarExtension()


def create_app(config_name=None):
    """Create and configure Flask application.
    
    Args:
        config_name: Configuration name ('development', 'production', or None for auto-detect)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Auto-detect configuration if not specified
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Load configuration from config.py
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    flask_cache.init_app(app)
    
    # Set up database query tracking for debug toolbar
    setup_db_query_tracking(app)
    
    # Only initialize debug toolbar if enabled in config
    if app.config.get('DEBUG_TB_ENABLED', False):
        toolbar.init_app(app)
        
        # Initialize custom debug panels
        from app.debug_panels import init_debug_panels
        init_debug_panels(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    # Import models to ensure they are registered with SQLAlchemy
    from app import models
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


def register_blueprints(app):
    """Register application blueprints."""
    try:
        from app.routes.main import main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        # Blueprint not yet created, skip for now
        pass
    
    try:
        from app.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
    except ImportError:
        # Blueprint not yet created, skip for now
        pass


def register_cli_commands(app):
    """Register CLI commands for database management."""
    
    @app.cli.command()
    def init_db():
        """Initialize the database with tables."""
        db.create_all()
        print("Database tables created successfully!")
    
    @app.cli.command()
    def seed_db():
        """Seed the database with sample data."""
        from app.models import Category, Product
        
        # Clear existing data
        db.session.query(Product).delete()
        db.session.query(Category).delete()
        
        # Create sample categories
        categories = [
            Category(name='Electronics', description='Electronic devices and gadgets'),
            Category(name='Books', description='Physical and digital books'),
            Category(name='Clothing', description='Apparel and fashion items'),
            Category(name='Home & Garden', description='Home improvement and gardening supplies'),
            Category(name='Sports', description='Sports equipment and accessories')
        ]
        
        for category in categories:
            db.session.add(category)
        
        db.session.commit()
        
        # Create sample products
        products = [
            # Electronics
            Product(name='Laptop Pro 15"', description='High-performance laptop with 16GB RAM and 512GB SSD', 
                   price=1299.99, category_id=1),
            Product(name='Wireless Headphones', description='Noise-cancelling wireless headphones with 30-hour battery', 
                   price=199.99, category_id=1),
            Product(name='Smartphone X', description='Latest smartphone with advanced camera and 5G connectivity', 
                   price=899.99, category_id=1),
            Product(name='Tablet Air', description='Lightweight tablet perfect for reading and productivity', 
                   price=449.99, category_id=1),
            
            # Books
            Product(name='Python Programming Guide', description='Comprehensive guide to Python programming for beginners', 
                   price=39.99, category_id=2),
            Product(name='Web Development Handbook', description='Modern web development techniques and best practices', 
                   price=49.99, category_id=2),
            Product(name='Database Design Principles', description='Learn database design and optimization techniques', 
                   price=44.99, category_id=2),
            
            # Clothing
            Product(name='Cotton T-Shirt', description='Comfortable 100% cotton t-shirt in various colors', 
                   price=19.99, category_id=3),
            Product(name='Denim Jeans', description='Classic fit denim jeans with premium quality fabric', 
                   price=79.99, category_id=3),
            Product(name='Running Shoes', description='Lightweight running shoes with advanced cushioning', 
                   price=129.99, category_id=3),
            
            # Home & Garden
            Product(name='Coffee Maker Deluxe', description='Programmable coffee maker with built-in grinder', 
                   price=159.99, category_id=4),
            Product(name='Garden Tool Set', description='Complete set of essential gardening tools', 
                   price=89.99, category_id=4),
            Product(name='LED Desk Lamp', description='Adjustable LED desk lamp with USB charging port', 
                   price=34.99, category_id=4),
            
            # Sports
            Product(name='Yoga Mat Premium', description='Non-slip yoga mat with extra cushioning', 
                   price=29.99, category_id=5),
            Product(name='Fitness Tracker', description='Waterproof fitness tracker with heart rate monitor', 
                   price=149.99, category_id=5),
            Product(name='Basketball Official', description='Official size basketball for indoor and outdoor play', 
                   price=24.99, category_id=5)
        ]
        
        for product in products:
            db.session.add(product)
        
        db.session.commit()
        
        print(f"Database seeded successfully!")
        print(f"Created {len(categories)} categories and {len(products)} products.")
    
    @app.cli.command()
    def reset_db():
        """Reset the database by dropping and recreating all tables with sample data."""
        db.drop_all()
        db.create_all()
        
        # Import and run seed command
        from flask.cli import with_appcontext
        import click
        
        ctx = click.get_current_context()
        ctx.invoke(seed_db)
        
        print("Database reset and seeded successfully!")

def set
up_db_query_tracking(app):
    """Set up SQLAlchemy event listeners to track database queries for debug toolbar."""
    
    if not app.config.get('DEBUG_TB_ENABLED', False):
        return
    
    @event.listens_for(db.engine, "before_cursor_execute", named=True)
    def before_cursor_execute(**kw):
        """Track query start time."""
        if not hasattr(g, 'db_queries'):
            g.db_queries = []
        
        # Store query start information
        query_info = {
            'statement': kw.get('statement', ''),
            'parameters': kw.get('parameters', {}),
            'start_time': time.time(),
            'context': kw.get('context', None)
        }
        
        # Store in a temporary location for the after event
        g._current_query = query_info
    
    @event.listens_for(db.engine, "after_cursor_execute", named=True)
    def after_cursor_execute(**kw):
        """Track query completion and duration."""
        if hasattr(g, '_current_query'):
            query_info = g._current_query
            end_time = time.time()
            
            # Calculate duration in milliseconds
            duration = (end_time - query_info['start_time']) * 1000
            
            # Complete the query information
            query_info.update({
                'end_time': end_time,
                'duration': duration,
                'executemany': kw.get('executemany', False),
                'context': kw.get('context', None)
            })
            
            # Add to the request's query list
            if not hasattr(g, 'db_queries'):
                g.db_queries = []
            g.db_queries.append(query_info)
            
            # Clean up temporary storage
            delattr(g, '_current_query')