import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime
from tqdm import tqdm
import logging

class EEdb:

    def __init__(self, user, password, host, port, database, logger: logging.Logger):
        self.logger = logger
        self.db_user = user
        self.db_password = password
        self.db_host = host
        self.db_port = port
        self.db_name = database
        self.engine = self.create_db_engine(
            self.db_user, self.db_password, self.db_host, self.db_port, self.db_name
        )

    @staticmethod
    def create_db_engine(user, password, host, port, database):
        """Create SQLAlchemy engine for database operations"""
        connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        engine = create_engine(connection_string, pool_pre_ping=True, pool_recycle=3600)
        return engine


    def test_connection(self):
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                self.logger.info("Database connection successful!")
                return True
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            return False
        finally:
            self.engine.dispose()