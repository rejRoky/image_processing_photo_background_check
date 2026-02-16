"""
URL configuration for photo_background_check project.

This module defines the root URL routing for the entire project,
including API versioning and documentation endpoints.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# API versioning prefix
API_V1_PREFIX = 'api/v1/'

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1 endpoints
    path(API_V1_PREFIX, include('photo_checker.urls', namespace='photo_checker')),
    
    # Legacy API endpoints (backward compatibility)
    path('api/', include('photo_checker.urls')),
    
    # Health checks
    path('health/', include('health_check.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
