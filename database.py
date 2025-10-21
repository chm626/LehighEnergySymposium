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

def get_mysql_connection():
    """
    Creates and returns a MySQL database connection using SQLAlchemy engine.
    
    Returns:
        sqlalchemy.engine.Engine: Database engine for executing queries
        
    Raises:
        Exception: If database connection fails
    """
    # Database configuration from environment variables
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'database': os.getenv('DB_NAME', 'EEdb'),
        'user': os.getenv('DB_USER', 'your_username'),
        'password': os.getenv('DB_PASSWORD', 'your_password')
    }
    
    # Create connection string
    connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    
    try:
        # Create SQLAlchemy engine
        engine = create_engine(
            connection_string, 
            pool_pre_ping=True, 
            pool_recycle=3600
        )
        
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connection successful!")
            
        return engine
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise Exception(f"Failed to connect to database: {e}")

def execute_query(engine, query, params=None):
    """
    Execute a SQL query and return results as a pandas DataFrame.
    
    Args:
        engine: SQLAlchemy engine from get_mysql_connection()
        query (str): SQL query to execute
        params (dict, optional): Query parameters
        
    Returns:
        pandas.DataFrame: Query results
    """
    try:
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

def get_pjm_data():
    """
    Connect to EEdb database, PJM_daily table, and retrieve all LMP data.
    
    Returns:
        pandas.DataFrame: PJM data with columns: id, date, zone, average_lmp, import_id
        
    Raises:
        Exception: If database connection or query fails
    """
    try:
        # Get database connection
        engine = get_mysql_connection()
        
        # Query to get monthly averaged PJM data
        query = """
        SELECT 
            YEAR(date) as year,
            MONTH(date) as month,
            zone,
            AVG(average_lmp) as average_lmp
        FROM PJM_daily 
        GROUP BY YEAR(date), MONTH(date), zone
        ORDER BY year, month, zone
        """
        
        # Execute query
        df = execute_query(engine, query)
        
        # Create date column from year and month, convert average_lmp to float
        df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))
        df['average_lmp'] = df['average_lmp'].astype(float)
        
        # Convert from $/MWh to cents/kWh
        # 1 MWh = 1000 kWh, so $/MWh * 1000 = $/kWh, then * 100 = cents/kWh
        df['lmp_cents_per_kwh'] = df['average_lmp'] * 0.1  # $/MWh to cents/kWh
        
        logger.info(f"Successfully retrieved {len(df)} monthly PJM data records")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get PJM data: {e}")
        raise Exception(f"Failed to get PJM data: {e}")

def get_pjm_average_lmp():
    """
    Connect to EEdb database, PJM_daily table, and calculate average of average_lmp column.
    
    Returns:
        float: Average LMP value from PJM_daily table
        
    Raises:
        Exception: If database connection or query fails
    """
    try:
        # Get database connection
        engine = get_mysql_connection()
        
        # Query to calculate average of average_lmp column
        query = "SELECT AVG(average_lmp) as avg_lmp FROM PJM_daily"
        
        # Execute query
        df = execute_query(engine, query)
        
        # Extract the average value and convert to float
        avg_lmp = float(df.iloc[0]['avg_lmp'])
        
        logger.info(f"Successfully calculated average \n LMP: {avg_lmp}")
        return avg_lmp
        
    except Exception as e:
        logger.error(f"Failed to get PJM average LMP: {e}")
        raise Exception(f"Failed to get PJM average LMP: {e}")

# Example usage function
def test_connection():
    """Test function to verify database connectivity"""
    try:
        engine = get_mysql_connection()
        print("SUCCESS: Database connection established!")
        
        
        return True
    except Exception as e:
        print(f"ERROR: Database connection failed - {e}")
        return False

if __name__ == "__main__":
    get_pjm_average_lmp()
