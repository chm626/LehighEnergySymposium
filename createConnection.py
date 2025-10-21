# This file will read from the .env file and create a connection to the database
import os
import logging
from dotenv import load_dotenv
from etl import EEdb

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME', 'EEdb'),
    'user': os.getenv('DB_USER', 'your_username'),
    'password': os.getenv('DB_PASSWORD', 'your_password')
}
# Create database handler
db_handler = EEdb(
    DB_CONFIG['user'], 
    DB_CONFIG['password'], 
    DB_CONFIG['host'], 
    DB_CONFIG['port'], 
    DB_CONFIG['database'], 
    logger
)

if __name__ == "__main__":
    if db_handler.test_connection():
        print("SUCCESS: Database connection established, and then disconnected")
    else:
        print("ERROR: Database connection failed - check your .env file")
    