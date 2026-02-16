"""
Request/Response middleware for the photo_checker app.

This module provides middleware for:
- Request logging with timing
- Request ID generation for tracing
- Security headers
"""

import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware for logging HTTP requests with timing information.
    
    This middleware:
    - Generates unique request IDs for tracing
    - Logs request/response details
    - Tracks request duration
    - Adds request ID to response headers
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR', '-')
        
        # Log request start (debug level)
        logger.debug(
            'Request started',
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'ip_address': client_ip,
                'user_agent': request.META.get('HTTP_USER_AGENT', '-')[:100],
            }
        )
        
        # Process request
        response = self.get_response(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Add headers to response
        response['X-Request-ID'] = request_id
        response['X-Response-Time'] = f'{duration_ms:.2f}ms'
        
        # Log request completion
        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        
        logger.log(
            log_level,
            'Request completed',
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2),
                'ip_address': client_ip,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            }
        )
        
        return response


class SecurityHeadersMiddleware:
    """
    Middleware for adding additional security headers to responses.
    
    Supplements Django's built-in security middleware with additional
    headers for enhanced security.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        
        # Content Security Policy (adjust based on your needs)
        response['Content-Security-Policy'] = "default-src 'self'"
        
        # Permissions Policy
        response['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), microphone=(), payment=(), usb=()'
        )
        
        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-DNS-Prefetch-Control'] = 'off'
        response['X-Download-Options'] = 'noopen'
        response['X-Permitted-Cross-Domain-Policies'] = 'none'
        
        return response


class CacheControlMiddleware:
    """
    Middleware for setting appropriate cache control headers.
    
    Sets cache headers based on response type and content.
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        
        # Don't cache API responses by default
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
