"""
Tests for photo_checker API endpoints.
"""

import io
import pytest
from PIL import Image
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestPhotoCheckAPI:
    """Tests for the photo check API endpoint."""
    
    def test_analyze_white_background_image(self, api_client, sample_white_image):
        """Test that white background images are correctly detected."""
        url = '/api/check-photo/'
        
        response = api_client.post(
            url,
            {'image': sample_white_image},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['is_white_background'] is True
        assert 'confidence' in response.data['data']
        assert 'processing_time_ms' in response.data
    
    def test_analyze_colored_background_image(self, api_client, sample_colored_image):
        """Test that colored background images are correctly detected."""
        url = '/api/check-photo/'
        
        response = api_client.post(
            url,
            {'image': sample_colored_image},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['is_white_background'] is False
    
    def test_analyze_with_custom_threshold(self, api_client, sample_white_image):
        """Test analysis with custom threshold parameter."""
        url = '/api/check-photo/'
        
        response = api_client.post(
            url,
            {
                'image': sample_white_image,
                'threshold': 0.8,
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
    
    def test_analyze_with_custom_clusters(self, api_client, sample_mixed_image):
        """Test analysis with custom number of clusters."""
        url = '/api/check-photo/'
        
        response = api_client.post(
            url,
            {
                'image': sample_mixed_image,
                'num_clusters': 3,
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
    
    def test_analyze_no_image_provided(self, api_client):
        """Test error when no image is provided."""
        url = '/api/check-photo/'
        
        response = api_client.post(url, {}, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
        assert 'error' in response.data
    
    def test_analyze_invalid_file_type(self, api_client):
        """Test error when invalid file type is provided."""
        url = '/api/check-photo/'
        
        # Create a text file
        text_file = io.BytesIO(b'This is not an image')
        text_file.name = 'test.txt'
        
        response = api_client.post(
            url,
            {'image': text_file},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_analyze_response_format(self, api_client, sample_white_image):
        """Test that response has expected format."""
        url = '/api/check-photo/'
        
        response = api_client.post(
            url,
            {'image': sample_white_image},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        assert 'success' in response.data
        assert 'data' in response.data
        assert 'processing_time_ms' in response.data
        
        # Check data structure
        data = response.data['data']
        assert 'is_white_background' in data
        assert 'confidence' in data
        assert 'dominant_color' in data
        assert 'white_pixel_percentage' in data
        
        # Check dominant color format
        assert isinstance(data['dominant_color'], list)
        assert len(data['dominant_color']) == 3


@pytest.mark.django_db
class TestPhotoViewSet:
    """Tests for the Photo ViewSet."""
    
    def test_list_photos_empty(self, api_client):
        """Test listing photos when none exist."""
        url = '/api/photos/'
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_upload_photo(self, api_client, sample_white_image):
        """Test uploading a photo."""
        url = '/api/photos/'
        
        response = api_client.post(
            url,
            {'image': sample_white_image},
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'uuid' in response.data
        assert 'status' in response.data


@pytest.mark.django_db 
class TestBatchAnalysis:
    """Tests for batch photo analysis."""
    
    def test_batch_analyze_multiple_images(self, api_client, sample_white_image, sample_colored_image):
        """Test batch analysis of multiple images."""
        url = '/api/analyze/batch/'
        
        # Reset file pointers
        sample_white_image.seek(0)
        sample_colored_image.seek(0)
        
        response = api_client.post(
            url,
            {
                'images': [sample_white_image, sample_colored_image],
            },
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['total'] == 2
        assert len(response.data['results']) == 2


@pytest.mark.django_db
class TestAPIDocumentation:
    """Tests for API documentation endpoints."""
    
    def test_schema_endpoint(self, api_client):
        """Test that OpenAPI schema is accessible."""
        url = '/api/schema/'
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_swagger_ui(self, api_client):
        """Test that Swagger UI is accessible."""
        url = '/api/docs/'
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestHealthCheck:
    """Tests for health check endpoints."""
    
    def test_health_endpoint(self, api_client):
        """Test health check endpoint."""
        url = '/health/'
        
        response = api_client.get(url)
        
        # Health check should return 200 or 503
        assert response.status_code in [200, 503]
