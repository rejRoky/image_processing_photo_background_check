"""
Custom exception handling for the API.

This module provides production-grade error handling with proper
error codes, detailed messages, and consistent response formats.
"""

import logging
import traceback
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ErrorCode:
    """Standard error codes for API responses."""
    
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    NOT_FOUND = 'NOT_FOUND'
    RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
    SERVER_ERROR = 'SERVER_ERROR'
    BAD_REQUEST = 'BAD_REQUEST'
    
    # Domain-specific errors
    IMAGE_PROCESSING_ERROR = 'IMAGE_PROCESSING_ERROR'
    INVALID_IMAGE_FORMAT = 'INVALID_IMAGE_FORMAT'
    IMAGE_TOO_LARGE = 'IMAGE_TOO_LARGE'
    IMAGE_CORRUPTED = 'IMAGE_CORRUPTED'


class BaseAPIException(APIException):
    """Base exception class for custom API exceptions."""
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'A server error occurred.'
    default_code = ErrorCode.SERVER_ERROR

    def __init__(
        self,
        detail: Optional[str] = None,
        code: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        self.detail = detail or self.default_detail
        self.code = code or self.default_code
        self.extra = extra or {}
        super().__init__(detail=self.detail, code=self.code)


class ImageProcessingError(BaseAPIException):
    """Exception raised when image processing fails."""
    
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Failed to process the image.'
    default_code = ErrorCode.IMAGE_PROCESSING_ERROR


class InvalidImageFormatError(BaseAPIException):
    """Exception raised when image format is not supported."""
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'The image format is not supported.'
    default_code = ErrorCode.INVALID_IMAGE_FORMAT


class ImageTooLargeError(BaseAPIException):
    """Exception raised when image exceeds size limits."""
    
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = 'The image file is too large.'
    default_code = ErrorCode.IMAGE_TOO_LARGE


class ImageCorruptedError(BaseAPIException):
    """Exception raised when image file is corrupted."""
    
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'The image file appears to be corrupted.'
    default_code = ErrorCode.IMAGE_CORRUPTED


def custom_exception_handler(exc: Exception, context: dict) -> Optional[Response]:
    """
    Custom exception handler for DRF.
    
    This handler provides consistent error response format across the API:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...}  # Optional additional details
        }
    }
    """
    # Get the standard DRF response
    response = exception_handler(exc, context)
    
    if response is not None:
        error_response = _format_drf_exception(exc, response)
        response.data = error_response
        return response
    
    # Handle Django exceptions not handled by DRF
    if isinstance(exc, Http404):
        return Response(
            _format_error(
                code=ErrorCode.NOT_FOUND,
                message='The requested resource was not found.',
            ),
            status=status.HTTP_404_NOT_FOUND
        )
    
    if isinstance(exc, PermissionDenied):
        return Response(
            _format_error(
                code=ErrorCode.PERMISSION_DENIED,
                message='You do not have permission to perform this action.',
            ),
            status=status.HTTP_403_FORBIDDEN
        )
    
    if isinstance(exc, ValidationError):
        return Response(
            _format_error(
                code=ErrorCode.VALIDATION_ERROR,
                message='Validation error.',
                details={'errors': exc.messages if hasattr(exc, 'messages') else str(exc)},
            ),
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Log unhandled exceptions
    logger.error(
        'Unhandled exception: %s',
        str(exc),
        exc_info=True,
        extra={
            'view': context.get('view').__class__.__name__ if context.get('view') else None,
            'request_path': context.get('request').path if context.get('request') else None,
        }
    )
    
    # Return generic error in production, detailed error in debug
    if settings.DEBUG:
        return Response(
            _format_error(
                code=ErrorCode.SERVER_ERROR,
                message=str(exc),
                details={'traceback': traceback.format_exc()},
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response(
        _format_error(
            code=ErrorCode.SERVER_ERROR,
            message='An unexpected error occurred. Please try again later.',
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def _format_drf_exception(exc: Exception, response: Response) -> dict:
    """Format DRF exceptions into consistent error format."""
    code = ErrorCode.BAD_REQUEST
    message = 'An error occurred.'
    details = None
    
    if hasattr(exc, 'code'):
        code = exc.code
    
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, dict):
            message = 'Validation error.'
            details = {'fields': exc.detail}
        elif isinstance(exc.detail, list):
            message = '; '.join(str(d) for d in exc.detail)
        else:
            message = str(exc.detail)
    
    # Handle specific DRF exceptions
    if response.status_code == 401:
        code = ErrorCode.AUTHENTICATION_ERROR
        message = message or 'Authentication credentials were not provided.'
    elif response.status_code == 403:
        code = ErrorCode.PERMISSION_DENIED
    elif response.status_code == 404:
        code = ErrorCode.NOT_FOUND
    elif response.status_code == 429:
        code = ErrorCode.RATE_LIMIT_EXCEEDED
        message = 'Request rate limit exceeded. Please slow down.'
    
    return _format_error(code=code, message=message, details=details)


def _format_error(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> dict:
    """Create standardized error response format."""
    error = {
        'success': False,
        'error': {
            'code': code,
            'message': message,
        }
    }
    
    if details:
        error['error']['details'] = details
    
    return error
