"""
Pytest configuration for photo_checker tests.
"""

import os
import sys
from pathlib import Path

import django
import pytest
from django.conf import settings

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure():
    """Configure Django settings for tests."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photo_background_check.settings')
    os.environ['DJANGO_ENVIRONMENT'] = 'development'
    django.setup()


@pytest.fixture(scope='session')
def django_db_setup():
    """Setup test database."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


@pytest.fixture
def api_client():
    """Return DRF test client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def sample_white_image():
    """Create a sample white image for testing."""
    import io
    from PIL import Image
    
    # Create a white image
    img = Image.new('RGB', (100, 100), color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    buffer.name = 'test_white.jpg'
    return buffer


@pytest.fixture
def sample_colored_image():
    """Create a sample colored image for testing."""
    import io
    from PIL import Image
    
    # Create a colored image
    img = Image.new('RGB', (100, 100), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    buffer.name = 'test_colored.jpg'
    return buffer


@pytest.fixture
def sample_mixed_image():
    """Create a sample image with mixed colors for testing."""
    import io
    import numpy as np
    from PIL import Image
    
    # Create image with white border and colored center
    img_array = np.ones((100, 100, 3), dtype=np.uint8) * 255  # White
    img_array[20:80, 20:80] = [0, 0, 255]  # Blue center
    
    img = Image.fromarray(img_array, 'RGB')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    buffer.name = 'test_mixed.jpg'
    return buffer
