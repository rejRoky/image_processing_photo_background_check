"""
Serializers for the photo_checker app.

This module provides DRF serializers with comprehensive validation
and documentation for API input/output.
"""

import logging
from typing import Any, Dict

from django.conf import settings
from rest_framework import serializers

from .models import Photo, PhotoAnalysisResult
from .utils.validators import ImageValidator, get_image_info

logger = logging.getLogger(__name__)


class ImageUploadSerializer(serializers.Serializer):
    """
    Serializer for image upload validation.
    
    Validates uploaded images against size, format, and dimension constraints.
    """
    
    image = serializers.ImageField(
        required=True,
        help_text='Image file to analyze. Supported formats: JPEG, PNG, WebP, BMP.',
    )
    threshold = serializers.FloatField(
        required=False,
        default=0.5,
        min_value=0.0,
        max_value=1.0,
        help_text='White background detection threshold (0.0 to 1.0). Default: 0.5',
    )
    num_clusters = serializers.IntegerField(
        required=False,
        default=2,
        min_value=2,
        max_value=10,
        help_text='Number of color clusters for K-means analysis (2-10). Default: 2',
    )
    
    def validate_image(self, value):
        """Validate the uploaded image file."""
        validator = ImageValidator()
        is_valid, error_message = validator.validate(value)
        
        if not is_valid:
            raise serializers.ValidationError(error_message)
        
        # Add image info to validated data for later use
        self._image_info = get_image_info(value)
        
        return value
    
    def get_image_info(self) -> Dict[str, Any]:
        """Get image information extracted during validation."""
        return getattr(self, '_image_info', {})


class BackgroundAnalysisResultSerializer(serializers.Serializer):
    """
    Serializer for background analysis results.
    
    Provides detailed analysis output with confidence scores.
    """
    
    is_white_background = serializers.BooleanField(
        help_text='Whether the image has a predominantly white background.'
    )
    confidence = serializers.FloatField(
        help_text='Confidence score of the detection (0.0 to 1.0).'
    )
    dominant_color = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=255),
        help_text='Dominant background color in RGB format [R, G, B].'
    )
    white_pixel_percentage = serializers.FloatField(
        help_text='Percentage of pixels classified as white (0.0 to 1.0).'
    )
    analysis_details = serializers.DictField(
        required=False,
        help_text='Additional analysis details.'
    )


class PhotoAnalysisResponseSerializer(serializers.Serializer):
    """
    Serializer for the complete photo analysis API response.
    """
    
    success = serializers.BooleanField(default=True)
    data = BackgroundAnalysisResultSerializer()
    image_info = serializers.DictField(
        required=False,
        help_text='Information about the analyzed image.'
    )
    processing_time_ms = serializers.FloatField(
        help_text='Time taken to process the image in milliseconds.'
    )


class PhotoSerializer(serializers.ModelSerializer):
    """
    Serializer for Photo model.
    
    Handles photo upload with full validation and provides
    read-only fields for analysis results.
    """
    
    analysis_results = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = Photo
        fields = [
            'id',
            'uuid',
            'image',
            'image_url',
            'original_filename',
            'file_size',
            'file_size_mb',
            'mime_type',
            'width',
            'height',
            'status',
            'analysis_results',
            'uploaded_at',
            'processed_at',
        ]
        read_only_fields = [
            'id',
            'uuid',
            'original_filename',
            'file_size',
            'mime_type',
            'width',
            'height',
            'status',
            'uploaded_at',
            'processed_at',
        ]
    
    def get_analysis_results(self, obj) -> Dict[str, Any]:
        """Get the latest analysis results for this photo."""
        try:
            result = obj.analysis_results.latest('created_at')
            return PhotoAnalysisResultSerializer(result).data
        except PhotoAnalysisResult.DoesNotExist:
            return None
    
    def get_image_url(self, obj) -> str:
        """Get the full URL for the image."""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None
    
    def get_file_size_mb(self, obj) -> float:
        """Get file size in megabytes."""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None
    
    def validate_image(self, value):
        """Validate the uploaded image."""
        validator = ImageValidator()
        is_valid, error_message = validator.validate(value)
        
        if not is_valid:
            raise serializers.ValidationError(error_message)
        
        return value


class PhotoAnalysisResultSerializer(serializers.ModelSerializer):
    """
    Serializer for PhotoAnalysisResult model.
    """
    
    class Meta:
        model = PhotoAnalysisResult
        fields = [
            'id',
            'is_white_background',
            'confidence',
            'white_pixel_percentage',
            'dominant_color',
            'threshold_used',
            'num_clusters_used',
            'processing_time_ms',
            'analysis_metadata',
            'created_at',
        ]
        read_only_fields = fields


class BatchPhotoUploadSerializer(serializers.Serializer):
    """
    Serializer for batch photo upload.
    
    Allows uploading multiple images at once for batch processing.
    """
    
    images = serializers.ListField(
        child=serializers.ImageField(),
        min_length=1,
        max_length=10,
        help_text='List of images to analyze (1-10 images).',
    )
    threshold = serializers.FloatField(
        required=False,
        default=0.5,
        min_value=0.0,
        max_value=1.0,
    )
    async_processing = serializers.BooleanField(
        required=False,
        default=False,
        help_text='Process images asynchronously using background tasks.',
    )
    
    def validate_images(self, value):
        """Validate all uploaded images."""
        validator = ImageValidator()
        errors = []
        
        for i, image in enumerate(value):
            is_valid, error_message = validator.validate(image)
            if not is_valid:
                errors.append(f'Image {i + 1}: {error_message}')
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return value


class TaskStatusSerializer(serializers.Serializer):
    """
    Serializer for async task status response.
    """
    
    task_id = serializers.CharField()
    status = serializers.ChoiceField(
        choices=['pending', 'processing', 'completed', 'failed']
    )
    progress = serializers.IntegerField(
        min_value=0,
        max_value=100,
        help_text='Progress percentage (0-100).',
    )
    result = serializers.DictField(
        required=False,
        allow_null=True,
    )
    error = serializers.CharField(
        required=False,
        allow_null=True,
    )
