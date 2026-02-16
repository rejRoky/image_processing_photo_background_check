"""
Tests for photo_checker models.
"""

import io
import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from photo_checker.models import Photo, PhotoAnalysisResult, PhotoStatus


@pytest.mark.django_db
class TestPhotoModel:
    """Tests for Photo model."""
    
    def create_test_image(self, name='test.jpg', size=(100, 100), color='white'):
        """Create a test image file."""
        img = Image.new('RGB', size, color=color)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')
    
    def test_create_photo(self):
        """Test creating a Photo instance."""
        image_file = self.create_test_image()
        photo = Photo.objects.create(image=image_file)
        
        assert photo.id is not None
        assert photo.uuid is not None
        assert photo.status == PhotoStatus.PENDING
        assert photo.uploaded_at is not None
    
    def test_photo_uuid_is_unique(self):
        """Test that each photo has a unique UUID."""
        image1 = self.create_test_image('test1.jpg')
        image2 = self.create_test_image('test2.jpg')
        
        photo1 = Photo.objects.create(image=image1)
        photo2 = Photo.objects.create(image=image2)
        
        assert photo1.uuid != photo2.uuid
    
    def test_photo_status_choices(self):
        """Test photo status transitions."""
        image_file = self.create_test_image()
        photo = Photo.objects.create(image=image_file)
        
        assert photo.status == PhotoStatus.PENDING
        
        photo.status = PhotoStatus.PROCESSING
        photo.save()
        assert photo.status == PhotoStatus.PROCESSING
        
        photo.status = PhotoStatus.COMPLETED
        photo.save()
        assert photo.status == PhotoStatus.COMPLETED
    
    def test_photo_aspect_ratio(self):
        """Test aspect ratio calculation."""
        image_file = self.create_test_image(size=(200, 100))
        photo = Photo.objects.create(
            image=image_file,
            width=200,
            height=100
        )
        
        assert photo.aspect_ratio == 2.0
    
    def test_photo_is_processed(self):
        """Test is_processed property."""
        image_file = self.create_test_image()
        photo = Photo.objects.create(image=image_file)
        
        assert photo.is_processed is False
        
        photo.status = PhotoStatus.COMPLETED
        photo.save()
        
        assert photo.is_processed is True
    
    def test_photo_str_representation(self):
        """Test string representation."""
        image_file = self.create_test_image()
        photo = Photo.objects.create(image=image_file)
        
        str_repr = str(photo)
        assert str(photo.uuid) in str_repr
        assert photo.status in str_repr


@pytest.mark.django_db
class TestPhotoAnalysisResultModel:
    """Tests for PhotoAnalysisResult model."""
    
    def create_test_photo(self):
        """Create a test photo."""
        img = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        image_file = SimpleUploadedFile('test.jpg', buffer.read(), content_type='image/jpeg')
        return Photo.objects.create(image=image_file)
    
    def test_create_analysis_result(self):
        """Test creating an analysis result."""
        photo = self.create_test_photo()
        
        result = PhotoAnalysisResult.objects.create(
            photo=photo,
            is_white_background=True,
            confidence=0.95,
            white_pixel_percentage=0.85,
            dominant_color=[255, 255, 255],
        )
        
        assert result.id is not None
        assert result.photo == photo
        assert result.is_white_background is True
        assert result.confidence == 0.95
    
    def test_analysis_result_photo_relationship(self):
        """Test relationship between Photo and AnalysisResult."""
        photo = self.create_test_photo()
        
        result1 = PhotoAnalysisResult.objects.create(
            photo=photo,
            is_white_background=True,
            confidence=0.9,
            white_pixel_percentage=0.8,
            dominant_color=[255, 255, 255],
        )
        
        result2 = PhotoAnalysisResult.objects.create(
            photo=photo,
            is_white_background=True,
            confidence=0.95,
            white_pixel_percentage=0.85,
            dominant_color=[255, 255, 255],
            threshold_used=0.6,
        )
        
        assert photo.analysis_results.count() == 2
        assert result1 in photo.analysis_results.all()
        assert result2 in photo.analysis_results.all()
    
    def test_analysis_result_ordering(self):
        """Test that results are ordered by created_at desc."""
        photo = self.create_test_photo()
        
        result1 = PhotoAnalysisResult.objects.create(
            photo=photo,
            is_white_background=True,
            confidence=0.9,
            white_pixel_percentage=0.8,
            dominant_color=[255, 255, 255],
        )
        
        result2 = PhotoAnalysisResult.objects.create(
            photo=photo,
            is_white_background=True,
            confidence=0.95,
            white_pixel_percentage=0.85,
            dominant_color=[255, 255, 255],
        )
        
        results = list(photo.analysis_results.all())
        # Most recent first
        assert results[0] == result2
        assert results[1] == result1
