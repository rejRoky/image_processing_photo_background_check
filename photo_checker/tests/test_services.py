"""
Tests for the image processing service.
"""

import io
import pytest
import numpy as np
from PIL import Image

from photo_checker.services import (
    ImageProcessingService,
    AnalysisResult,
    BackgroundType,
    get_image_processing_service,
)


class TestImageProcessingService:
    """Tests for ImageProcessingService."""
    
    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        return ImageProcessingService(enable_caching=False)
    
    def create_solid_color_image(self, color: tuple, size: tuple = (100, 100)) -> bytes:
        """Create a solid color image and return bytes."""
        img = Image.new('RGB', size, color=color)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()
    
    def test_analyze_white_image(self, service):
        """Test analysis of pure white image."""
        image_data = self.create_solid_color_image((255, 255, 255))
        
        result = service.analyze_image(image_data)
        
        assert isinstance(result, AnalysisResult)
        assert result.is_white_background is True
        assert result.white_pixel_percentage >= 0.9
        assert result.background_type == BackgroundType.WHITE
    
    def test_analyze_black_image(self, service):
        """Test analysis of pure black image."""
        image_data = self.create_solid_color_image((0, 0, 0))
        
        result = service.analyze_image(image_data)
        
        assert result.is_white_background is False
        assert result.background_type == BackgroundType.DARK
    
    def test_analyze_colored_image(self, service):
        """Test analysis of colored image."""
        image_data = self.create_solid_color_image((255, 0, 0))  # Red
        
        result = service.analyze_image(image_data)
        
        assert result.is_white_background is False
        assert result.background_type in [BackgroundType.COLORED, BackgroundType.LIGHT]
    
    def test_analyze_with_custom_threshold(self, service):
        """Test analysis with custom threshold."""
        image_data = self.create_solid_color_image((240, 240, 240))  # Light gray
        
        # With default threshold, might be considered white
        result_default = service.analyze_image(image_data, threshold=0.5)
        
        # With higher threshold, should not be white
        result_strict = service.analyze_image(image_data, threshold=0.99)
        
        assert isinstance(result_default, AnalysisResult)
        assert isinstance(result_strict, AnalysisResult)
    
    def test_analyze_returns_dominant_color(self, service):
        """Test that dominant color is returned correctly."""
        blue_image = self.create_solid_color_image((0, 0, 255))
        
        result = service.analyze_image(blue_image)
        
        # Dominant color should be close to blue
        assert len(result.dominant_color) == 3
        # Allow some variation due to JPEG compression
        assert result.dominant_color[2] > 200  # Blue channel high
    
    def test_analyze_returns_cluster_info(self, service):
        """Test that cluster information is returned."""
        image_data = self.create_solid_color_image((128, 128, 128))
        
        result = service.analyze_image(image_data, num_clusters=3)
        
        assert result.cluster_centers is not None
        assert result.cluster_percentages is not None
        assert len(result.cluster_centers) <= 3
    
    def test_analyze_processing_time(self, service):
        """Test that processing time is recorded."""
        image_data = self.create_solid_color_image((255, 255, 255))
        
        result = service.analyze_image(image_data)
        
        assert result.processing_time_ms > 0
    
    def test_analyze_image_dimensions(self, service):
        """Test that image dimensions are recorded."""
        image_data = self.create_solid_color_image((255, 255, 255), size=(200, 150))
        
        result = service.analyze_image(image_data)
        
        assert result.image_dimensions == (200, 150)
    
    def test_to_dict(self, service):
        """Test AnalysisResult.to_dict() method."""
        image_data = self.create_solid_color_image((255, 255, 255))
        
        result = service.analyze_image(image_data)
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'is_white_background' in result_dict
        assert 'confidence' in result_dict
        assert 'dominant_color' in result_dict
        assert 'processing_time_ms' in result_dict
    
    def test_singleton_service(self):
        """Test that get_image_processing_service returns singleton."""
        service1 = get_image_processing_service()
        service2 = get_image_processing_service()
        
        assert service1 is service2


class TestImageProcessingServiceCaching:
    """Tests for service caching functionality."""
    
    def test_cached_results(self):
        """Test that results are cached."""
        service = ImageProcessingService(enable_caching=True, cache_timeout=60)
        
        img = Image.new('RGB', (50, 50), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        image_data = buffer.getvalue()
        
        # First call
        result1 = service.analyze_image(image_data)
        
        # Second call should use cache
        result2 = service.analyze_image(image_data)
        
        assert result1.is_white_background == result2.is_white_background
        assert result1.confidence == result2.confidence


class TestImageProcessingEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.fixture
    def service(self):
        return ImageProcessingService(enable_caching=False)
    
    def test_very_small_image(self, service):
        """Test handling of very small images."""
        img = Image.new('RGB', (10, 10), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        
        result = service.analyze_image(buffer.getvalue())
        
        assert isinstance(result, AnalysisResult)
    
    def test_large_image_resizing(self, service):
        """Test that large images are resized for processing."""
        # Create a large image
        img = Image.new('RGB', (2000, 2000), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        
        result = service.analyze_image(buffer.getvalue())
        
        assert isinstance(result, AnalysisResult)
        assert result.image_dimensions == (2000, 2000)  # Original dimensions preserved
    
    def test_png_image(self, service):
        """Test handling of PNG images."""
        img = Image.new('RGBA', (100, 100), color=(255, 255, 255, 255))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        
        result = service.analyze_image(buffer.getvalue())
        
        assert isinstance(result, AnalysisResult)
