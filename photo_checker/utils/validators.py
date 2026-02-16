"""
Image validation utilities for the photo_checker app.

This module provides comprehensive validation for uploaded images
including format, size, dimensions, and content validation.
"""

import logging
import magic
from io import BytesIO
from typing import List, Optional, Tuple

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image

logger = logging.getLogger(__name__)


class ImageValidator:
    """
    Comprehensive image validator for uploaded files.
    
    Validates:
    - File size limits
    - MIME type / magic bytes
    - Image dimensions
    - File extension
    - Image integrity (can be opened by PIL)
    """
    
    def __init__(
        self,
        max_size_mb: Optional[int] = None,
        allowed_types: Optional[List[str]] = None,
        allowed_extensions: Optional[List[str]] = None,
        max_dimension: Optional[int] = None,
        min_dimension: Optional[int] = None,
    ):
        """
        Initialize validator with constraints.
        
        Args:
            max_size_mb: Maximum file size in megabytes.
            allowed_types: List of allowed MIME types.
            allowed_extensions: List of allowed file extensions.
            max_dimension: Maximum width/height in pixels.
            min_dimension: Minimum width/height in pixels.
        """
        self.max_size_bytes = (max_size_mb or getattr(settings, 'MAX_UPLOAD_SIZE_MB', 10)) * 1024 * 1024
        self.allowed_types = allowed_types or getattr(settings, 'ALLOWED_IMAGE_TYPES', [
            'image/jpeg', 'image/png', 'image/webp', 'image/bmp'
        ])
        self.allowed_extensions = allowed_extensions or getattr(settings, 'ALLOWED_IMAGE_EXTENSIONS', [
            '.jpg', '.jpeg', '.png', '.webp', '.bmp'
        ])
        self.max_dimension = max_dimension or getattr(settings, 'IMAGE_PROCESSING', {}).get('MAX_IMAGE_DIMENSION', 4096)
        self.min_dimension = min_dimension or 10
    
    def validate(self, file) -> Tuple[bool, Optional[str]]:
        """
        Validate an uploaded file.
        
        Args:
            file: Uploaded file object (InMemoryUploadedFile or similar).
            
        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            # Validate file size
            if hasattr(file, 'size') and file.size > self.max_size_bytes:
                return False, f'File size exceeds maximum allowed size of {self.max_size_bytes // (1024 * 1024)} MB.'
            
            # Read file content
            file.seek(0)
            content = file.read()
            file.seek(0)
            
            # Validate by content length
            if len(content) > self.max_size_bytes:
                return False, f'File size exceeds maximum allowed size of {self.max_size_bytes // (1024 * 1024)} MB.'
            
            # Validate MIME type using magic bytes
            mime_type = self._get_mime_type(content)
            if mime_type not in self.allowed_types:
                return False, f'File type "{mime_type}" is not allowed. Allowed types: {", ".join(self.allowed_types)}.'
            
            # Validate file extension
            if hasattr(file, 'name') and file.name:
                ext = '.' + file.name.lower().rsplit('.', 1)[-1] if '.' in file.name else ''
                if ext and ext not in self.allowed_extensions:
                    return False, f'File extension "{ext}" is not allowed. Allowed extensions: {", ".join(self.allowed_extensions)}.'
            
            # Validate image can be opened
            try:
                img = Image.open(BytesIO(content))
                img.verify()  # Verify image integrity
                
                # Re-open for dimension check (verify() closes the file)
                img = Image.open(BytesIO(content))
                width, height = img.size
                
                # Validate dimensions
                if width > self.max_dimension or height > self.max_dimension:
                    return False, f'Image dimensions ({width}x{height}) exceed maximum allowed ({self.max_dimension}x{self.max_dimension}).'
                
                if width < self.min_dimension or height < self.min_dimension:
                    return False, f'Image dimensions ({width}x{height}) are below minimum required ({self.min_dimension}x{self.min_dimension}).'
                
            except Exception as e:
                logger.warning(f'Image validation failed - could not open image: {e}')
                return False, 'The file appears to be corrupted or is not a valid image.'
            
            return True, None
            
        except Exception as e:
            logger.error(f'Image validation error: {e}', exc_info=True)
            return False, f'An error occurred while validating the image: {str(e)}'
    
    def _get_mime_type(self, content: bytes) -> str:
        """Get MIME type from file content using magic bytes."""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_buffer(content)
        except Exception:
            # Fallback to basic magic byte detection
            if content.startswith(b'\xff\xd8\xff'):
                return 'image/jpeg'
            elif content.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'image/png'
            elif content.startswith(b'RIFF') and b'WEBP' in content[:12]:
                return 'image/webp'
            elif content.startswith(b'BM'):
                return 'image/bmp'
            elif content.startswith(b'GIF'):
                return 'image/gif'
            return 'application/octet-stream'


def validate_image_file(file) -> None:
    """
    Validate an image file, raising ValidationError if invalid.
    
    This is a convenience function for use in Django form/serializer validation.
    
    Args:
        file: Uploaded file to validate.
        
    Raises:
        ValidationError: If the image is invalid.
    """
    validator = ImageValidator()
    is_valid, error_message = validator.validate(file)
    
    if not is_valid:
        raise ValidationError(error_message)


def get_image_info(file) -> dict:
    """
    Get detailed information about an image file.
    
    Args:
        file: Image file to analyze.
        
    Returns:
        Dictionary with image information.
    """
    file.seek(0)
    content = file.read()
    file.seek(0)
    
    info = {
        'size_bytes': len(content),
        'size_mb': round(len(content) / (1024 * 1024), 2),
    }
    
    try:
        img = Image.open(BytesIO(content))
        info.update({
            'width': img.size[0],
            'height': img.size[1],
            'format': img.format,
            'mode': img.mode,
            'has_alpha': img.mode in ('RGBA', 'LA', 'PA'),
        })
    except Exception as e:
        logger.warning(f'Could not get image info: {e}')
    
    return info
