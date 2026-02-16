"""
Custom logging utilities for the photo_checker app.

This module provides JSON-formatted logging for production environments
and structured logging helpers.
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging in production.
    
    Outputs logs in JSON format for easy parsing by log aggregation
    tools like ELK Stack, Datadog, or CloudWatch.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields from record
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        
        # Add any custom extra data
        extra_keys = set(record.__dict__.keys()) - set(logging.LogRecord('', 0, '', 0, '', (), None).__dict__.keys())
        for key in extra_keys:
            if key not in log_data and not key.startswith('_'):
                log_data[key] = getattr(record, key)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info) if record.exc_info[0] else None,
            }
        
        return json.dumps(log_data, default=str)


class RequestContextFilter(logging.Filter):
    """
    Logging filter that adds request context to log records.
    
    This filter extracts useful information from the current request
    and adds it to log records for better debugging.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record."""
        # These will be set by middleware if available
        record.request_id = getattr(record, 'request_id', '-')
        record.user_id = getattr(record, 'user_id', '-')
        record.ip_address = getattr(record, 'ip_address', '-')
        return True


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for the given name.
    
    Args:
        name: Logger name, typically __name__ of the calling module.
        
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    return logger


def log_api_request(
    logger: logging.Logger,
    request: Any,
    response_status: int,
    duration_ms: float,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log API request with structured data.
    
    Args:
        logger: Logger instance to use.
        request: Django/DRF request object.
        response_status: HTTP response status code.
        duration_ms: Request duration in milliseconds.
        extra: Additional data to include in log.
    """
    log_data = {
        'method': request.method,
        'path': request.path,
        'status_code': response_status,
        'duration_ms': round(duration_ms, 2),
        'user_agent': request.META.get('HTTP_USER_AGENT', '-'),
        'content_length': request.META.get('CONTENT_LENGTH', 0),
    }
    
    if extra:
        log_data.update(extra)
    
    if response_status >= 500:
        logger.error('API request failed', extra=log_data)
    elif response_status >= 400:
        logger.warning('API request client error', extra=log_data)
    else:
        logger.info('API request completed', extra=log_data)


def log_image_processing(
    logger: logging.Logger,
    image_size: tuple,
    processing_time_ms: float,
    result: Dict[str, Any],
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log image processing operation with metrics.
    
    Args:
        logger: Logger instance to use.
        image_size: Tuple of (width, height) of processed image.
        processing_time_ms: Processing duration in milliseconds.
        result: Processing result data.
        extra: Additional data to include in log.
    """
    log_data = {
        'image_width': image_size[0] if image_size else None,
        'image_height': image_size[1] if image_size else None,
        'processing_time_ms': round(processing_time_ms, 2),
        'result': result,
    }
    
    if extra:
        log_data.update(extra)
    
    logger.info('Image processing completed', extra=log_data)
