# Configuration settings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings and configuration"""
    
    # Database settings
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'database': os.getenv('DB_NAME', 'EEdb'),
        'user': os.getenv('DB_USER', 'your_username'),
        'password': os.getenv('DB_PASSWORD', 'your_password')
    }
    
    # Application settings
    APP_TITLE = "Symposium Energy Analytics"
    APP_DESCRIPTION = "Comprehensive energy market analysis platform"
    
    # Chart settings
    DEFAULT_CHART_HEIGHT = 500
    DEFAULT_CHART_WIDTH = "container"
    
    # Available modules
    AVAILABLE_MODULES = [
        {
            'name': 'PJM LMP Analysis',
            'module': 'pjm_module',
            'class': 'PJMModule',
            'description': 'Analyze PJM Locational Marginal Prices'
        },
        {
            'name': 'Future Analysis',
            'module': 'future_module', 
            'class': 'FutureModule',
            'description': 'Placeholder for future modules'
        }
    ]
