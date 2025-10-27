import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseManager:
    """Database connection and session management for Flughafen DB"""
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = self._build_database_url()
        
        # Configure engine with better settings for large operations
        engine_kwargs = {
            "echo": False,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 3600,  # Recycle connections every hour
            "pool_pre_ping": True,  # Validate connections before use
        }
        
        # Add database-specific settings
        if "mysql" in database_url:
            engine_kwargs["connect_args"] = {
                "connect_timeout": 60,
                "read_timeout": 300,
                "write_timeout": 300,
            }
        elif "postgresql" in database_url:
            engine_kwargs["connect_args"] = {
                "connect_timeout": 60,
            }
        
        self.engine = create_engine(database_url, **engine_kwargs)
    
    @staticmethod
    def _build_database_url() -> str:
        """Build database URL from environment variables"""
        # Check if full DATABASE_URL is provided
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        
        # Build URL from individual components
        db_type = os.getenv("DB_TYPE", "mysql").lower()
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT")
        name = os.getenv("DB_NAME", "flughafendb")
        user = os.getenv("DB_USER", "username")
        password = os.getenv("DB_PASSWORD", "password")
        
        # Set default ports if not specified
        if not port:
            port = "3306" if db_type in ["mysql", "mariadb"] else "5432"
        
        # Build connection string based on database type
        if db_type in ["mysql", "mariadb"]:
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
        elif db_type == "postgresql":
            return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}. Use 'mysql', 'mariadb', or 'postgresql'")
    
    def create_tables(self):
        """Create all tables in the database"""
        SQLModel.metadata.create_all(self.engine)
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session"""
        with Session(self.engine) as session:
            yield session


# Example usage:
# 
# Method 1: Using environment variables (recommended)
# Create a .env file with your database configuration
# db_manager = DatabaseManager()
# 
# Method 2: Using explicit URL
# db_manager = DatabaseManager("mysql+pymysql://user:password@localhost/flughafendb")
# 
# # Create tables
# db_manager.create_tables()
# 
# # Use session
# with db_manager.get_session() as session:
#     airports = session.exec(select(Airport)).all()