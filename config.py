"""
Configuration management for Legal Document Filler application.
Loads environment variables and defines application constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Google Gemini API Configuration
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    
    # Session Configuration
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 3600))  # 1 hour in seconds
    SESSION_TYPE = 'filesystem'  # or 'redis' for production
    PERMANENT_SESSION_LIFETIME = SESSION_TIMEOUT
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 5))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
    ALLOWED_EXTENSIONS = {'docx'}
    UPLOAD_FOLDER = 'uploads'
    
    # LLM Configuration
    ENABLE_LLM = os.getenv('ENABLE_LLM', 'true').lower() == 'true'
    LLM_TIMEOUT = 3  # seconds
    LLM_CACHE_SIZE = 100  # max cached responses
    LLM_RATE_LIMIT = 15  # requests per minute (Gemini free tier)
    
    # Document Processing Configuration
    MAX_PAGES = 50
    MAX_PLACEHOLDERS = 200
    
    # Placeholder Pattern Configuration
    PATTERNS = {
        'double_curly': r'\{\{([a-zA-Z0-9_]+)\}\}',          # {{name}}
        'single_curly': r'\{([a-zA-Z0-9_]+)\}',              # {name}
        'square_bracket': r'\[([A-Z][a-zA-Z0-9_\s]+)\]',     # [Date of Safe], [NAME]
        'underscore': r'_{5,}',                              # _____
        'dollar_underscore': r'\$\[_{5,}\]',                 # $[_____]
    }
    
    # Validation Configuration
    MIN_PLACEHOLDER_LENGTH = 2
    MAX_PLACEHOLDER_LENGTH = 100


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    
    # Override with stricter settings for production
    SESSION_TYPE = 'redis'  # Use Redis for production sessions


class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = True
    TESTING = True
    MAX_FILE_SIZE_MB = 1  # Smaller for tests


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """
    Get configuration based on environment.
    
    Args:
        env (str): Environment name ('development', 'production', 'testing')
    
    Returns:
        Config: Configuration class for the specified environment
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    return config.get(env, config['default'])

