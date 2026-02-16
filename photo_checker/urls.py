"""
URL configuration for the photo_checker app.

This module defines all API endpoints for photo analysis.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PhotoCheckAPIView,
    BatchPhotoCheckAPIView,
    PhotoViewSet,
)

app_name = 'photo_checker'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'photos', PhotoViewSet, basename='photo')

urlpatterns = [
    # Main analysis endpoint (legacy compatible)
    path('check-photo/', PhotoCheckAPIView.as_view(), name='check_photo'),
    
    # New analysis endpoints
    path('analyze/', PhotoCheckAPIView.as_view(), name='analyze_photo'),
    path('analyze/batch/', BatchPhotoCheckAPIView.as_view(), name='batch_analyze'),
    
    # ViewSet routes
    path('', include(router.urls)),
]
