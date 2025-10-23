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
    APP_TITLE = "ERES Energy Analytics"
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
            'name': 'EGS Pricing Analysis',
            'module': 'future_module', 
            'class': 'FutureModule',
            'description': 'Compare EGS retail prices to PJM wholesale prices by EDC'
        },
        {
            'name': 'PTC Analysis',
            'module': 'ptc_module',
            'class': 'PTCModule',
            'description': 'Compare PTC rates to EGS retail prices and PJM wholesale prices by EDC'
        },
        {
            'name': 'EGS Fee Analysis',
            'module': 'fees_module', 
            'class': 'FeesModule',
            'description': 'Analyze EGS signup fees by EDC and supplier'
        }
    ]
