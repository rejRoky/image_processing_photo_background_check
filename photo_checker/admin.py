"""
Django Admin configuration for photo_checker app.

This module provides admin interfaces for managing photos
and viewing analysis results.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Photo, PhotoAnalysisResult, APIRequestLog


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    """Admin interface for Photo model."""
    
    list_display = [
        'uuid',
        'thumbnail_preview',
        'original_filename',
        'status',
        'dimensions_display',
        'file_size_display',
        'uploaded_at',
    ]
    list_filter = ['status', 'uploaded_at']
    search_fields = ['uuid', 'original_filename']
    readonly_fields = [
        'uuid',
        'image_preview',
        'original_filename',
        'file_size',
        'mime_type',
        'width',
        'height',
        'uploaded_at',
        'processed_at',
    ]
    ordering = ['-uploaded_at']
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        ('Image', {
            'fields': ('image', 'image_preview', 'original_filename'),
        }),
        ('Metadata', {
            'fields': ('uuid', 'file_size', 'mime_type', 'width', 'height'),
        }),
        ('Status', {
            'fields': ('status', 'uploaded_at', 'processed_at'),
        }),
        ('Additional Data', {
            'fields': ('metadata',),
            'classes': ('collapse',),
        }),
    )
    
    def thumbnail_preview(self, obj):
        """Display thumbnail in list view."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.image.url
            )
        return '-'
    thumbnail_preview.short_description = 'Preview'
    
    def image_preview(self, obj):
        """Display larger preview in detail view."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 500px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Image Preview'
    
    def dimensions_display(self, obj):
        """Display image dimensions."""
        if obj.width and obj.height:
            return f'{obj.width} × {obj.height}'
        return '-'
    dimensions_display.short_description = 'Dimensions'
    
    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        if obj.file_size:
            if obj.file_size < 1024:
                return f'{obj.file_size} B'
            elif obj.file_size < 1024 * 1024:
                return f'{obj.file_size / 1024:.1f} KB'
            else:
                return f'{obj.file_size / (1024 * 1024):.2f} MB'
        return '-'
    file_size_display.short_description = 'Size'


@admin.register(PhotoAnalysisResult)
class PhotoAnalysisResultAdmin(admin.ModelAdmin):
    """Admin interface for PhotoAnalysisResult model."""
    
    list_display = [
        'id',
        'photo_link',
        'is_white_background',
        'confidence_display',
        'dominant_color_preview',
        'processing_time_display',
        'created_at',
    ]
    list_filter = ['is_white_background', 'created_at']
    search_fields = ['photo__uuid']
    readonly_fields = [
        'photo',
        'is_white_background',
        'confidence',
        'white_pixel_percentage',
        'dominant_color',
        'dominant_color_preview_large',
        'threshold_used',
        'num_clusters_used',
        'processing_time_ms',
        'analysis_metadata',
        'created_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Photo', {
            'fields': ('photo',),
        }),
        ('Results', {
            'fields': (
                'is_white_background',
                'confidence',
                'white_pixel_percentage',
                'dominant_color',
                'dominant_color_preview_large',
            ),
        }),
        ('Parameters', {
            'fields': ('threshold_used', 'num_clusters_used'),
        }),
        ('Metrics', {
            'fields': ('processing_time_ms', 'created_at'),
        }),
        ('Metadata', {
            'fields': ('analysis_metadata',),
            'classes': ('collapse',),
        }),
    )
    
    def photo_link(self, obj):
        """Link to photo admin page."""
        from django.urls import reverse
        url = reverse('admin:photo_checker_photo_change', args=[obj.photo.id])
        return format_html('<a href="{}">{}</a>', url, obj.photo.uuid)
    photo_link.short_description = 'Photo'
    
    def confidence_display(self, obj):
        """Display confidence as percentage."""
        return f'{obj.confidence * 100:.1f}%'
    confidence_display.short_description = 'Confidence'
    
    def processing_time_display(self, obj):
        """Display processing time."""
        if obj.processing_time_ms:
            return f'{obj.processing_time_ms:.2f} ms'
        return '-'
    processing_time_display.short_description = 'Processing Time'
    
    def dominant_color_preview(self, obj):
        """Display color swatch in list view."""
        if obj.dominant_color and len(obj.dominant_color) == 3:
            r, g, b = obj.dominant_color
            return format_html(
                '<div style="background-color: rgb({},{},{}); '
                'width: 30px; height: 20px; border: 1px solid #ccc;"></div>',
                r, g, b
            )
        return '-'
    dominant_color_preview.short_description = 'Color'
    
    def dominant_color_preview_large(self, obj):
        """Display larger color swatch in detail view."""
        if obj.dominant_color and len(obj.dominant_color) == 3:
            r, g, b = obj.dominant_color
            return format_html(
                '<div style="background-color: rgb({},{},{}); '
                'width: 100px; height: 50px; border: 1px solid #ccc; '
                'display: inline-block; vertical-align: middle;"></div>'
                '<span style="margin-left: 10px;">RGB({}, {}, {})</span>',
                r, g, b, r, g, b
            )
        return '-'
    dominant_color_preview_large.short_description = 'Dominant Color'


@admin.register(APIRequestLog)
class APIRequestLogAdmin(admin.ModelAdmin):
    """Admin interface for API request logs."""
    
    list_display = [
        'request_id',
        'method',
        'path',
        'status_code',
        'response_time_display',
        'ip_address',
        'created_at',
    ]
    list_filter = ['method', 'status_code', 'created_at']
    search_fields = ['request_id', 'path', 'ip_address']
    readonly_fields = [
        'request_id',
        'method',
        'path',
        'ip_address',
        'user_agent',
        'status_code',
        'response_time_ms',
        'created_at',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def response_time_display(self, obj):
        """Display response time."""
        return f'{obj.response_time_ms:.2f} ms'
    response_time_display.short_description = 'Response Time'
    
    def has_add_permission(self, request):
        """Disable adding logs manually."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing logs."""
        return False
