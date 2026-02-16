"""
Celery tasks for the photo_checker app.

This module provides asynchronous tasks for image processing
using Celery for background job execution.
"""

import logging
from typing import List, Optional

from celery import shared_task
from django.utils import timezone

from .models import Photo, PhotoAnalysisResult, PhotoStatus
from .services import get_image_processing_service, ImageProcessingError

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 3},
    acks_late=True,
)
def analyze_photo_task(self, photo_id: int, threshold: float = 0.5, num_clusters: int = 2):
    """
    Async task to analyze a single photo.
    
    Args:
        photo_id: ID of the Photo model instance.
        threshold: White background detection threshold.
        num_clusters: Number of clusters for K-Means.
        
    Returns:
        Dict with analysis results.
    """
    logger.info(f'Starting analysis for photo {photo_id}')
    
    try:
        photo = Photo.objects.get(id=photo_id)
    except Photo.DoesNotExist:
        logger.error(f'Photo {photo_id} not found')
        return {'success': False, 'error': 'Photo not found'}
    
    # Update status
    photo.status = PhotoStatus.PROCESSING
    photo.save(update_fields=['status'])
    
    try:
        service = get_image_processing_service()
        result = service.analyze_from_file(
            photo.image.file,
            threshold=threshold,
            num_clusters=num_clusters,
        )
        
        # Save analysis result
        analysis_result = PhotoAnalysisResult.objects.create(
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
        
        # Update photo status
        photo.status = PhotoStatus.COMPLETED
        photo.processed_at = timezone.now()
        photo.save(update_fields=['status', 'processed_at'])
        
        logger.info(f'Analysis completed for photo {photo_id}')
        
        return {
            'success': True,
            'photo_id': photo_id,
            'photo_uuid': str(photo.uuid),
            'result_id': analysis_result.id,
            'is_white_background': result.is_white_background,
            'confidence': result.confidence,
        }
        
    except ImageProcessingError as e:
        logger.error(f'Image processing failed for photo {photo_id}: {e}')
        photo.status = PhotoStatus.FAILED
        photo.save(update_fields=['status'])
        raise
    except Exception as e:
        logger.exception(f'Unexpected error analyzing photo {photo_id}: {e}')
        photo.status = PhotoStatus.FAILED
        photo.save(update_fields=['status'])
        raise


@shared_task(bind=True)
def batch_analyze_photos_task(
    self,
    photo_ids: List[int],
    threshold: float = 0.5,
    num_clusters: int = 2
):
    """
    Async task to analyze multiple photos.
    
    Args:
        photo_ids: List of Photo model instance IDs.
        threshold: White background detection threshold.
        num_clusters: Number of clusters for K-Means.
        
    Returns:
        Dict with batch analysis results.
    """
    logger.info(f'Starting batch analysis for {len(photo_ids)} photos')
    
    results = []
    successful = 0
    failed = 0
    
    for i, photo_id in enumerate(photo_ids):
        # Update task progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i + 1,
                'total': len(photo_ids),
                'percent': int((i + 1) / len(photo_ids) * 100),
            }
        )
        
        try:
            # Process each photo synchronously within this task
            result = analyze_photo_task.apply(
                args=[photo_id, threshold, num_clusters]
            ).get()
            
            if result.get('success'):
                successful += 1
            else:
                failed += 1
            
            results.append(result)
            
        except Exception as e:
            failed += 1
            results.append({
                'success': False,
                'photo_id': photo_id,
                'error': str(e),
            })
    
    logger.info(f'Batch analysis completed: {successful} successful, {failed} failed')
    
    return {
        'success': True,
        'total': len(photo_ids),
        'successful': successful,
        'failed': failed,
        'results': results,
    }


@shared_task
def cleanup_old_photos_task(days: int = 30):
    """
    Cleanup task to remove old photos and their results.
    
    Args:
        days: Delete photos older than this many days.
        
    Returns:
        Number of deleted photos.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_photos = Photo.objects.filter(uploaded_at__lt=cutoff_date)
    count = old_photos.count()
    
    # Delete files and records
    for photo in old_photos:
        try:
            if photo.image:
                photo.image.delete(save=False)
        except Exception as e:
            logger.warning(f'Failed to delete image file for photo {photo.uuid}: {e}')
    
    old_photos.delete()
    
    logger.info(f'Cleaned up {count} old photos')
    return count


@shared_task
def generate_analytics_report_task():
    """
    Generate analytics report for photo analysis usage.
    
    Returns:
        Dict with analytics data.
    """
    from django.db.models import Count, Avg
    from datetime import timedelta
    from django.utils import timezone
    
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    # Count photos by status
    status_counts = dict(
        Photo.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')
    )
    
    # Recent activity
    recent_24h = Photo.objects.filter(uploaded_at__gte=last_24h).count()
    recent_7d = Photo.objects.filter(uploaded_at__gte=last_7d).count()
    recent_30d = Photo.objects.filter(uploaded_at__gte=last_30d).count()
    
    # Analysis statistics
    analysis_stats = PhotoAnalysisResult.objects.aggregate(
        avg_confidence=Avg('confidence'),
        avg_processing_time=Avg('processing_time_ms'),
        total_analyses=Count('id'),
    )
    
    # White background percentage
    white_bg_count = PhotoAnalysisResult.objects.filter(is_white_background=True).count()
    total_analyses = analysis_stats['total_analyses'] or 1
    white_bg_percentage = (white_bg_count / total_analyses) * 100
    
    report = {
        'generated_at': now.isoformat(),
        'photo_counts': {
            'by_status': status_counts,
            'last_24h': recent_24h,
            'last_7d': recent_7d,
            'last_30d': recent_30d,
        },
        'analysis_stats': {
            'total_analyses': analysis_stats['total_analyses'],
            'avg_confidence': round(analysis_stats['avg_confidence'] or 0, 4),
            'avg_processing_time_ms': round(analysis_stats['avg_processing_time'] or 0, 2),
            'white_background_percentage': round(white_bg_percentage, 2),
        },
    }
    
    logger.info('Analytics report generated')
    return report
