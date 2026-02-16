"""
Models for the photo_checker app.

This module provides database models for storing photos and their
analysis results with proper indexing and optimization.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


def photo_upload_path(instance, filename):
    """Generate upload path for photos with date-based organization."""
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
    now = timezone.now()
    return f'photos/{now.year}/{now.month:02d}/{now.day:02d}/{instance.uuid}.{ext}'


class PhotoStatus(models.TextChoices):
    """Status choices for photo processing."""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Photo(models.Model):
    """
    Model representing an uploaded photo.
    
    Stores photo metadata, file reference, and processing status.
    Optimized with indexes for common query patterns.
    """
    
    # Unique identifier for external references (never expose auto-increment IDs)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name='UUID'
    )
    
    # Image file
    image = models.ImageField(
        upload_to=photo_upload_path,
        max_length=500,
        verbose_name='Image File'
    )
    
    # Original file metadata
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Original Filename'
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='File Size (bytes)'
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='MIME Type'
    )
    
    # Image dimensions
    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Width (px)'
    )
    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Height (px)'
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=PhotoStatus.choices,
        default=PhotoStatus.PENDING,
        db_index=True,
        verbose_name='Processing Status'
    )
    
    # Timestamps
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Uploaded At'
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Processed At'
    )
    
    # Optional user association (for authenticated requests)
    # user = models.ForeignKey(
    #     'auth.User',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='photos'
    # )
    
    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadata'
    )
    
    class Meta:
        verbose_name = 'Photo'
        verbose_name_plural = 'Photos'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['status', 'uploaded_at']),
            models.Index(fields=['-uploaded_at']),
        ]
    
    def __str__(self):
        return f'Photo {self.uuid} ({self.status})'
    
    def save(self, *args, **kwargs):
        """Override save to extract image metadata."""
        if self.image and not self.file_size:
            self.file_size = self.image.size
            
            if hasattr(self.image.file, 'name'):
                self.original_filename = self.image.file.name.rsplit('/', 1)[-1]
            
            # Try to get image dimensions
            try:
                from PIL import Image
                from io import BytesIO
                
                self.image.seek(0)
                img = Image.open(BytesIO(self.image.read()))
                self.width, self.height = img.size
                self.image.seek(0)
            except Exception:
                pass
        
        super().save(*args, **kwargs)
    
    @property
    def aspect_ratio(self):
        """Calculate aspect ratio of the image."""
        if self.width and self.height:
            return round(self.width / self.height, 3)
        return None
    
    @property
    def is_processed(self):
        """Check if photo has been processed."""
        return self.status == PhotoStatus.COMPLETED


class PhotoAnalysisResult(models.Model):
    """
    Model for storing photo analysis results.
    
    Each photo can have multiple analysis results with different
    parameters (threshold, clusters, etc.).
    """
    
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name='analysis_results',
        verbose_name='Photo'
    )
    
    # Analysis results
    is_white_background = models.BooleanField(
        verbose_name='Has White Background'
    )
    confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name='Confidence Score'
    )
    white_pixel_percentage = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name='White Pixel Percentage'
    )
    
    # Dominant color (stored as JSON array [R, G, B])
    dominant_color = models.JSONField(
        default=list,
        verbose_name='Dominant Color (RGB)'
    )
    
    # Analysis parameters used
    threshold_used = models.FloatField(
        default=0.5,
        verbose_name='Threshold Used'
    )
    num_clusters_used = models.PositiveIntegerField(
        default=2,
        verbose_name='Number of Clusters'
    )
    
    # Processing metrics
    processing_time_ms = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Processing Time (ms)'
    )
    
    # Full analysis metadata
    analysis_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Analysis Metadata'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At'
    )
    
    class Meta:
        verbose_name = 'Photo Analysis Result'
        verbose_name_plural = 'Photo Analysis Results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['photo', '-created_at']),
            models.Index(fields=['is_white_background']),
        ]
    
    def __str__(self):
        return f'Analysis for {self.photo.uuid}: white_bg={self.is_white_background}, conf={self.confidence:.2f}'


class APIRequestLog(models.Model):
    """
    Model for logging API requests for analytics and debugging.
    
    Stores request metadata for monitoring and rate limiting analysis.
    """
    
    # Request identification
    request_id = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='Request ID'
    )
    
    # Request details
    method = models.CharField(
        max_length=10,
        verbose_name='HTTP Method'
    )
    path = models.CharField(
        max_length=500,
        verbose_name='Request Path'
    )
    
    # Client information
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP Address'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    
    # Response details
    status_code = models.PositiveIntegerField(
        verbose_name='Status Code'
    )
    response_time_ms = models.FloatField(
        verbose_name='Response Time (ms)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At'
    )
    
    class Meta:
        verbose_name = 'API Request Log'
        verbose_name_plural = 'API Request Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.method} {self.path} - {self.status_code}'
