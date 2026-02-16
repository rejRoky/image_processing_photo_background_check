"""
Image processing service for the photo_checker app.

This module provides production-grade image processing with:
- Optimized K-Means clustering for background detection
- Caching for repeated analysis
- Detailed metrics and logging
- Error handling and recovery
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from django.conf import settings
from django.core.cache import cache
from PIL import Image
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


class BackgroundType(Enum):
    """Enumeration of detected background types."""
    WHITE = 'white'
    LIGHT = 'light'
    DARK = 'dark'
    COLORED = 'colored'
    TRANSPARENT = 'transparent'
    UNKNOWN = 'unknown'


@dataclass
class AnalysisResult:
    """
    Data class for image analysis results.
    """
    is_white_background: bool
    confidence: float
    white_pixel_percentage: float
    dominant_color: List[int]
    background_type: BackgroundType
    cluster_centers: Optional[List[List[int]]] = None
    cluster_percentages: Optional[List[float]] = None
    processing_time_ms: float = 0.0
    image_dimensions: Tuple[int, int] = (0, 0)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'is_white_background': self.is_white_background,
            'confidence': round(self.confidence, 4),
            'white_pixel_percentage': round(self.white_pixel_percentage, 4),
            'dominant_color': self.dominant_color,
            'background_type': self.background_type.value,
            'cluster_centers': self.cluster_centers,
            'cluster_percentages': self.cluster_percentages,
            'processing_time_ms': round(self.processing_time_ms, 2),
            'image_dimensions': {
                'width': self.image_dimensions[0],
                'height': self.image_dimensions[1],
            },
            'metadata': self.extra_metadata,
        }


class ImageProcessingService:
    """
    Production-grade image processing service.
    
    Features:
    - K-Means clustering for background detection
    - Edge detection for background isolation
    - Caching of analysis results
    - Configurable parameters
    - Detailed metrics and logging
    """
    
    def __init__(
        self,
        white_threshold: Optional[float] = None,
        num_clusters: Optional[int] = None,
        white_color_threshold: Optional[int] = None,
        max_dimension: Optional[int] = None,
        enable_caching: bool = True,
        cache_timeout: int = 3600,
    ):
        """
        Initialize the image processing service.
        
        Args:
            white_threshold: Percentage threshold for white background detection.
            num_clusters: Number of clusters for K-Means.
            white_color_threshold: RGB value considered as white (0-255).
            max_dimension: Maximum image dimension for processing.
            enable_caching: Whether to cache analysis results.
            cache_timeout: Cache timeout in seconds.
        """
        img_settings = getattr(settings, 'IMAGE_PROCESSING', {})
        
        self.white_threshold = white_threshold or img_settings.get('DEFAULT_WHITE_THRESHOLD', 0.5)
        self.num_clusters = num_clusters or img_settings.get('DEFAULT_NUM_CLUSTERS', 2)
        self.white_color_threshold = white_color_threshold or img_settings.get('WHITE_COLOR_THRESHOLD', 240)
        self.max_dimension = max_dimension or img_settings.get('MAX_IMAGE_DIMENSION', 4096)
        self.enable_caching = enable_caching
        self.cache_timeout = cache_timeout
    
    def analyze_image(
        self,
        image_data: bytes,
        threshold: Optional[float] = None,
        num_clusters: Optional[int] = None,
    ) -> AnalysisResult:
        """
        Analyze an image for white background detection.
        
        Args:
            image_data: Raw image bytes.
            threshold: Override default white threshold.
            num_clusters: Override default number of clusters.
            
        Returns:
            AnalysisResult with detailed analysis data.
        """
        start_time = time.time()
        
        threshold = threshold or self.white_threshold
        num_clusters = num_clusters or self.num_clusters
        
        # Check cache
        if self.enable_caching:
            cache_key = self._get_cache_key(image_data, threshold, num_clusters)
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug('Returning cached analysis result')
                return cached_result
        
        try:
            # Decode image
            image = self._decode_image(image_data)
            original_dimensions = (image.shape[1], image.shape[0])
            
            # Resize if necessary for performance
            image = self._resize_for_processing(image)
            
            # Perform analysis
            result = self._analyze_background(image, threshold, num_clusters)
            result.image_dimensions = original_dimensions
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # Cache result
            if self.enable_caching:
                cache.set(cache_key, result, self.cache_timeout)
            
            logger.info(
                'Image analysis completed',
                extra={
                    'is_white_background': result.is_white_background,
                    'confidence': result.confidence,
                    'processing_time_ms': result.processing_time_ms,
                    'dimensions': original_dimensions,
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f'Image analysis failed: {e}', exc_info=True)
            raise ImageProcessingError(f'Failed to analyze image: {str(e)}')
    
    def analyze_from_file(
        self,
        file,
        threshold: Optional[float] = None,
        num_clusters: Optional[int] = None,
    ) -> AnalysisResult:
        """
        Analyze an image from a file-like object.
        
        Args:
            file: File-like object containing image data.
            threshold: Override default white threshold.
            num_clusters: Override default number of clusters.
            
        Returns:
            AnalysisResult with detailed analysis data.
        """
        file.seek(0)
        image_data = file.read()
        file.seek(0)
        
        return self.analyze_image(image_data, threshold, num_clusters)
    
    def _decode_image(self, image_data: bytes) -> np.ndarray:
        """Decode image data to numpy array."""
        # Try OpenCV first
        image = cv2.imdecode(
            np.frombuffer(image_data, np.uint8),
            cv2.IMREAD_COLOR
        )
        
        if image is None:
            # Fallback to PIL
            try:
                pil_image = Image.open(BytesIO(image_data))
                pil_image = pil_image.convert('RGB')
                image = np.array(pil_image)
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            except Exception as e:
                raise ImageProcessingError(f'Failed to decode image: {e}')
        
        return image
    
    def _resize_for_processing(
        self,
        image: np.ndarray,
        max_pixels: int = 1000000  # 1 megapixel
    ) -> np.ndarray:
        """Resize image if it's too large for efficient processing."""
        height, width = image.shape[:2]
        pixels = height * width
        
        if pixels > max_pixels:
            scale = np.sqrt(max_pixels / pixels)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.debug(f'Resized image from {width}x{height} to {new_width}x{new_height}')
        
        return image
    
    def _analyze_background(
        self,
        image: np.ndarray,
        threshold: float,
        num_clusters: int,
    ) -> AnalysisResult:
        """Perform background analysis using K-Means clustering."""
        # Reshape image for clustering
        pixels = image.reshape(-1, 3).astype(np.float32)
        
        # Perform K-Means clustering
        kmeans = KMeans(
            n_clusters=num_clusters,
            random_state=42,
            n_init=10,
            max_iter=300,
        )
        labels = kmeans.fit_predict(pixels)
        cluster_centers = kmeans.cluster_centers_.astype(int)
        
        # Calculate cluster percentages
        unique, counts = np.unique(labels, return_counts=True)
        cluster_percentages = counts / len(labels)
        
        # Sort by percentage (most common first)
        sorted_indices = np.argsort(cluster_percentages)[::-1]
        cluster_centers = cluster_centers[sorted_indices]
        cluster_percentages = cluster_percentages[sorted_indices]
        
        # Determine dominant color (BGR to RGB)
        dominant_color_bgr = cluster_centers[0]
        dominant_color = [int(dominant_color_bgr[2]), int(dominant_color_bgr[1]), int(dominant_color_bgr[0])]  # BGR to RGB
        
        # Calculate white pixel percentage
        white_mask = self._is_color_white(cluster_centers)
        white_percentage = sum(
            percentage for i, percentage in enumerate(cluster_percentages)
            if white_mask[i]
        )
        
        # Determine if background is white
        is_white = white_percentage >= threshold
        
        # Calculate confidence based on how clearly the background is detected
        # Higher confidence when percentage is far from threshold
        confidence = self._calculate_confidence(white_percentage, threshold)
        
        # Determine background type
        background_type = self._determine_background_type(dominant_color, white_percentage)
        
        # Edge-based background analysis for additional confidence
        edge_analysis = self._analyze_edges(image)
        
        return AnalysisResult(
            is_white_background=is_white,
            confidence=confidence,
            white_pixel_percentage=white_percentage,
            dominant_color=dominant_color,
            background_type=background_type,
            cluster_centers=[
                [int(c[2]), int(c[1]), int(c[0])] for c in cluster_centers  # BGR to RGB
            ],
            cluster_percentages=[float(p) for p in cluster_percentages],
            extra_metadata={
                'edge_analysis': edge_analysis,
                'threshold_used': threshold,
                'num_clusters': num_clusters,
            }
        )
    
    def _is_color_white(self, colors: np.ndarray) -> List[bool]:
        """Check if colors are close to white."""
        results = []
        for color in colors:
            # Check if all BGR channels are above threshold
            is_white = all(c >= self.white_color_threshold for c in color)
            results.append(is_white)
        return results
    
    def _calculate_confidence(self, percentage: float, threshold: float) -> float:
        """Calculate confidence score based on detection certainty."""
        # Distance from threshold normalized to 0-1 scale
        distance = abs(percentage - threshold)
        max_distance = max(threshold, 1 - threshold)
        
        # Sigmoid-like scaling for smoother confidence values
        confidence = min(distance / max_distance, 1.0)
        
        # Boost confidence when percentage is very high or very low
        if percentage > 0.8 or percentage < 0.2:
            confidence = min(confidence * 1.2, 1.0)
        
        return confidence
    
    def _determine_background_type(
        self,
        dominant_color: List[int],
        white_percentage: float
    ) -> BackgroundType:
        """Determine the type of background based on color analysis."""
        r, g, b = dominant_color
        
        # Check for white
        if all(c >= self.white_color_threshold for c in [r, g, b]):
            return BackgroundType.WHITE
        
        # Check for light background
        brightness = (r + g + b) / 3
        if brightness > 200:
            return BackgroundType.LIGHT
        
        # Check for dark background
        if brightness < 50:
            return BackgroundType.DARK
        
        # Check for neutral (gray) vs colored
        color_variance = np.std([r, g, b])
        if color_variance < 20:
            return BackgroundType.LIGHT if brightness > 127 else BackgroundType.DARK
        
        return BackgroundType.COLORED
    
    def _analyze_edges(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze image edges for background detection enhancement."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        
        # Calculate edge density
        edge_density = np.sum(edges > 0) / edges.size
        
        # Analyze border regions (potential background)
        h, w = image.shape[:2]
        border_width = max(10, min(h, w) // 20)
        
        borders = {
            'top': image[:border_width, :],
            'bottom': image[-border_width:, :],
            'left': image[:, :border_width],
            'right': image[:, -border_width:],
        }
        
        border_colors = {}
        for name, region in borders.items():
            mean_color = np.mean(region, axis=(0, 1))
            border_colors[name] = [int(mean_color[2]), int(mean_color[1]), int(mean_color[0])]  # BGR to RGB
        
        return {
            'edge_density': float(edge_density),
            'border_colors': border_colors,
        }
    
    def _get_cache_key(
        self,
        image_data: bytes,
        threshold: float,
        num_clusters: int
    ) -> str:
        """Generate cache key for analysis results."""
        image_hash = hashlib.md5(image_data).hexdigest()
        return f'img_analysis:{image_hash}:{threshold}:{num_clusters}'


class ImageProcessingError(Exception):
    """Exception raised when image processing fails."""
    pass


# Singleton instance for convenience
_service_instance: Optional[ImageProcessingService] = None


def get_image_processing_service() -> ImageProcessingService:
    """Get the singleton image processing service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageProcessingService()
    return _service_instance
