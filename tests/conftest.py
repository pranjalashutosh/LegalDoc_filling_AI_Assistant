"""
Pytest configuration and shared fixtures
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app as flask_app
from config import TestingConfig


@pytest.fixture
def app():
    """
    Create and configure a test Flask application.
    """
    flask_app.config.from_object(TestingConfig)
    
    # Create test upload folder
    os.makedirs(TestingConfig.UPLOAD_FOLDER, exist_ok=True)
    
    yield flask_app
    
    # Cleanup test upload folder
    import shutil
    if os.path.exists(TestingConfig.UPLOAD_FOLDER):
        shutil.rmtree(TestingConfig.UPLOAD_FOLDER)


@pytest.fixture
def client(app):
    """
    Create a test client for the Flask application.
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Create a test CLI runner for the Flask application.
    """
    return app.test_cli_runner()


@pytest.fixture
def session(client):
    """
    Create a test session context.
    """
    with client.session_transaction() as sess:
        yield sess


@pytest.fixture
def sample_docx_path():
    """
    Path to a sample .docx file for testing.
    """
    fixtures_dir = Path(__file__).parent / 'fixtures'
    return fixtures_dir / 'sample_document.docx'


@pytest.fixture
def sample_placeholders():
    """
    Sample placeholder data for testing.
    """
    return [
        'COMPANY_NAME',
        'CLIENT_NAME',
        'CONTRACT_DATE',
        'CONTRACT_AMOUNT',
        'PAYMENT_TERMS'
    ]


@pytest.fixture
def sample_answers():
    """
    Sample answers for placeholders.
    """
    return {
        'COMPANY_NAME': 'Acme Corporation',
        'CLIENT_NAME': 'John Doe',
        'CONTRACT_DATE': 'January 1, 2025',
        'CONTRACT_AMOUNT': '$10,000',
        'PAYMENT_TERMS': 'Net 30'
    }

