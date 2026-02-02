# API Tests Configuration
# Configure pytest for async tests and fixtures

import pytest
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Use test database to avoid destroying production data
os.environ["TEST_MODE"] = "true"

@pytest.fixture
def app():
    """Create a test FastAPI application."""
    from src.api.server import app
    return app

@pytest.fixture
def client(app):
    """Create a test client."""
    from fastapi.testclient import TestClient
    return TestClient(app)

@pytest.fixture
def sample_product():
    """Sample product data for testing."""
    return {
        "slug": "test-product-001",
        "name": "Test Product",
        "brand": "Test Brand",
        "price": 100.0,
        "currency": "EUR",
        "description": "Test description",
        "main_image": "https://example.com/image.jpg",
        "dimensions": "100x50x30",
        "country": "Italy",
        "attributes": {
            "material": "Wood",
            "color": "Brown"
        }
    }

@pytest.fixture
def sample_project():
    """Sample project data for testing."""
    return {
        "id": "test-project-001",
        "name": "Test Project",
        "slug": "test-project",
        "items": []
    }
