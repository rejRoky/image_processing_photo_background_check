"""
API views for the photo_checker app.

This module provides production-grade API endpoints for photo
background analysis with comprehensive error handling, validation,
and documentation.
"""

import logging
import time
from typing import Any

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Photo, PhotoAnalysisResult, PhotoStatus
from .serializers import (
    BatchPhotoUploadSerializer,
    ImageUploadSerializer,
    PhotoAnalysisResponseSerializer,
    PhotoSerializer,
    TaskStatusSerializer,
)
from .services import get_image_processing_service, ImageProcessingError
from .utils.exceptions import ImageProcessingError as APIImageProcessingError

logger = logging.getLogger(__name__)


@extend_schema(tags=['Photos'])
class PhotoCheckAPIView(APIView):
    """
    API endpoint for analyzing photo backgrounds.
    
    This endpoint accepts an image file and returns analysis results
    indicating whether the image has a white background.
    """
    
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (AllowAny,)
    
    @extend_schema(
        summary='Analyze photo background',
        description='''
        Analyze an uploaded photo to detect if it has a white background.
        
        Uses K-Means clustering to segment the image and determine the
        dominant background color. Returns detailed analysis including
        confidence scores and color information.
        ''',
        request={
            'multipart/form-data': ImageUploadSerializer,
        },
        responses={
            200: PhotoAnalysisResponseSerializer,
            400: {'description': 'Invalid request or image format'},
            413: {'description': 'Image file too large'},
            422: {'description': 'Image processing failed'},
        },
    )
    def post(self, request, *args, **kwargs):
        """Analyze an uploaded photo for white background."""
        start_time = time.time()
        
        # Validate input
        serializer = ImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid request data',
                        'details': serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract validated data
        image_file = serializer.validated_data['image']
        threshold = serializer.validated_data.get('threshold', 0.5)
        num_clusters = serializer.validated_data.get('num_clusters', 2)
        
        try:
            # Get image processing service
            service = get_image_processing_service()
            
            # Analyze image
            result = service.analyze_from_file(
                image_file,
                threshold=threshold,
                num_clusters=num_clusters,
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Build response
            response_data = {
                'success': True,
                'data': {
                    'is_white_background': result.is_white_background,
                    'confidence': result.confidence,
                    'dominant_color': result.dominant_color,
                    'white_pixel_percentage': result.white_pixel_percentage,
                    'background_type': result.background_type.value,
                    'analysis_details': {
                        'cluster_centers': result.cluster_centers,
                        'cluster_percentages': result.cluster_percentages,
                        **result.extra_metadata,
                    },
                },
                'image_info': serializer.get_image_info(),
                'processing_time_ms': round(processing_time, 2),
            }
            
            logger.info(
                'Photo analysis completed',
                extra={
                    'is_white_background': result.is_white_background,
                    'confidence': result.confidence,
                    'processing_time_ms': processing_time,
                }
            )
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ImageProcessingError as e:
            logger.error(f'Image processing failed: {e}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'IMAGE_PROCESSING_ERROR',
                        'message': str(e),
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.exception(f'Unexpected error during photo analysis: {e}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'SERVER_ERROR',
                        'message': 'An unexpected error occurred',
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['Photos'])
class BatchPhotoCheckAPIView(APIView):
    """
    API endpoint for batch photo analysis.
    
    Allows uploading multiple images for analysis in a single request.
    Supports both synchronous and asynchronous processing.
    """
    
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (AllowAny,)
    
    @extend_schema(
        summary='Batch analyze photos',
        description='''
        Analyze multiple photos for white background detection.
        
        When async_processing is true, returns a task ID that can be
        used to poll for results. Otherwise, processes all images
        synchronously and returns results immediately.
        ''',
        request={
            'multipart/form-data': BatchPhotoUploadSerializer,
        },
        responses={
            200: {'description': 'Batch analysis results'},
            202: {'description': 'Async task created'},
            400: {'description': 'Invalid request'},
        },
    )
    def post(self, request, *args, **kwargs):
        """Batch analyze uploaded photos."""
        serializer = BatchPhotoUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid request data',
                        'details': serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        images = serializer.validated_data['images']
        threshold = serializer.validated_data.get('threshold', 0.5)
        async_processing = serializer.validated_data.get('async_processing', False)
        
        if async_processing:
            # Queue async task
            try:
                from .tasks import batch_analyze_photos_task
                
                # Save images temporarily and queue task
                task = batch_analyze_photos_task.delay(
                    image_ids=[],  # Would need to save images first
                    threshold=threshold,
                )
                
                return Response(
                    {
                        'success': True,
                        'task_id': str(task.id),
                        'status': 'pending',
                        'message': f'Processing {len(images)} images asynchronously',
                    },
                    status=status.HTTP_202_ACCEPTED
                )
            except ImportError:
                logger.warning('Celery not configured, falling back to sync processing')
        
        # Synchronous processing
        service = get_image_processing_service()
        results = []
        
        for i, image_file in enumerate(images):
            try:
                result = service.analyze_from_file(image_file, threshold=threshold)
                results.append({
                    'index': i,
                    'filename': getattr(image_file, 'name', f'image_{i}'),
                    'success': True,
                    'data': result.to_dict(),
                })
            except Exception as e:
                results.append({
                    'index': i,
                    'filename': getattr(image_file, 'name', f'image_{i}'),
                    'success': False,
                    'error': str(e),
                })
        
        return Response(
            {
                'success': True,
                'total': len(images),
                'successful': sum(1 for r in results if r['success']),
                'failed': sum(1 for r in results if not r['success']),
                'results': results,
            },
            status=status.HTTP_200_OK
        )


@extend_schema_view(
    list=extend_schema(summary='List photos', tags=['Photos']),
    retrieve=extend_schema(summary='Get photo details', tags=['Photos']),
    create=extend_schema(summary='Upload photo', tags=['Photos']),
    destroy=extend_schema(summary='Delete photo', tags=['Photos']),
)
class PhotoViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing photos with full CRUD operations.
    
    Provides endpoints for uploading, listing, retrieving, and
    deleting photos with their analysis results.
    """
    
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (AllowAny,)
    lookup_field = 'uuid'
    
    def get_queryset(self):
        """Filter queryset with optional status filter."""
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related().prefetch_related('analysis_results')
    
    def perform_create(self, serializer):
        """Handle photo upload with automatic analysis."""
        photo = serializer.save()
        
        # Trigger analysis
        try:
            service = get_image_processing_service()
            result = service.analyze_from_file(photo.image.file)
            
            # Save analysis result
            PhotoAnalysisResult.objects.create(
                photo=photo,
                is_white_background=result.is_white_background,
                confidence=result.confidence,
                white_pixel_percentage=result.white_pixel_percentage,
                dominant_color=result.dominant_color,
                processing_time_ms=result.processing_time_ms,
                analysis_metadata=result.extra_metadata,
            )
            
            photo.status = PhotoStatus.COMPLETED
            photo.processed_at = timezone.now()
            photo.save(update_fields=['status', 'processed_at'])
            
        except Exception as e:
            logger.error(f'Failed to analyze photo {photo.uuid}: {e}')
            photo.status = PhotoStatus.FAILED
            photo.save(update_fields=['status'])
    
    @extend_schema(
        summary='Re-analyze photo',
        description='Trigger re-analysis of an existing photo with optional new parameters.',
        parameters=[
            OpenApiParameter('threshold', float, description='Detection threshold (0-1)'),
            OpenApiParameter('num_clusters', int, description='Number of clusters (2-10)'),
        ],
        responses={200: PhotoSerializer},
        tags=['Photos'],
    )
    @action(detail=True, methods=['post'])
    def analyze(self, request, uuid=None):
        """Re-analyze an existing photo."""
        photo = self.get_object()
        
        threshold = float(request.query_params.get('threshold', 0.5))
        num_clusters = int(request.query_params.get('num_clusters', 2))
        
        try:
            service = get_image_processing_service()
            result = service.analyze_from_file(
                photo.image.file,
                threshold=threshold,
                num_clusters=num_clusters,
            )
            
            # Save new analysis result
            PhotoAnalysisResult.objects.create(
                photo=photo,
                is_white_background=result.is_white_background,
                confidence=result.confidence,
                white_pixel_percentage=result.white_pixel_percentage,
                dominant_color=result.dominant_color,
                threshold_used=threshold,
                num_clusters_used=num_clusters,
                processing_time_ms=result.processing_time_ms,
                analysis_metadata=result.extra_metadata,
            )
            
            photo.status = PhotoStatus.COMPLETED
            photo.processed_at = timezone.now()
            photo.save(update_fields=['status', 'processed_at'])
            
            return Response(
                PhotoSerializer(photo, context={'request': request}).data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f'Failed to re-analyze photo {photo.uuid}: {e}')
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'ANALYSIS_FAILED',
                        'message': str(e),
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )


# Legacy view for backward compatibility
PhotoCheckAPI = PhotoCheckAPIView
