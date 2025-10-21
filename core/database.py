# Core database connection and query functions
import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Core database management class for all modules"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'database': os.getenv('DB_NAME', 'EEdb'),
            'user': os.getenv('DB_USER', 'your_username'),
            'password': os.getenv('DB_PASSWORD', 'your_password')
        }
        self._engine = None
    
    def get_engine(self):
        """Get or create database engine"""
        if self._engine is None:
            connection_string = f"mysql+pymysql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            
            try:
                self._engine = create_engine(
                    connection_string, 
                    pool_pre_ping=True, 
                    pool_recycle=3600
                )
                
                # Test the connection
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                    logger.info("Database connection successful!")
                    
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise Exception(f"Failed to connect to database: {e}")
        
        return self._engine
    
    def execute_query(self, query, params=None):
        """Execute a SQL query and return results as a pandas DataFrame"""
        try:
            engine = self.get_engine()
            with engine.connect() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                
                # Convert to DataFrame
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                return df
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise Exception(f"Failed to execute query: {e}")
    
    def test_connection(self):
        """Test database connectivity"""
        try:
            engine = self.get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
def get_mysql_connection():
    """Get database engine (backward compatibility)"""
    return db_manager.get_engine()

def execute_query(engine, query, params=None):
    """Execute query (backward compatibility)"""
    return db_manager.execute_query(query, params)
