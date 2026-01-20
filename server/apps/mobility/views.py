"""
============================================================================
Django REST Framework Views - FIXED GPS Points Query
============================================================================
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Min, Max, Avg, Sum, Q
from django.contrib.gis.geos import Polygon
from django.shortcuts import get_object_or_404
import logging

from apps.mobility.models import (
    Dataset,
    GPSPoint,
    Trajectory,
    ImportJob,
    ValidationError
)
from apps.mobility.serializers import (
    DatasetSerializer,
    DatasetListSerializer,
    GPSPointGeoJSONSerializer,
    GPSPointListSerializer,
    GPSPointCreateSerializer,
    TrajectoryGeoJSONSerializer,
    TrajectoryListSerializer,
    ImportJobSerializer,
    ImportJobListSerializer,
    ImportJobCreateSerializer,
    GPSPointQuerySerializer,
    TrajectoryQuerySerializer,
    EntityStatisticsSerializer,
    DatasetStatisticsSerializer
)
from apps.mobility.services.generic_importer import (
    MobilityDataImporter,
    TDriveImporter
)

logger = logging.getLogger(__name__)


# ============================================================================
# Pagination
# ============================================================================

class StandardPagination(PageNumberPagination):
    """Standard pagination for API results."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


# ============================================================================
# Dataset Management ViewSet
# ============================================================================

class DatasetViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing mobility datasets.
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DatasetListSerializer
        return DatasetSerializer
    
    def get_queryset(self):
        """Filter datasets by query parameters."""
        queryset = super().get_queryset()
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        dataset_type = self.request.query_params.get('type')
        if dataset_type:
            queryset = queryset.filter(dataset_type=dataset_type)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get detailed statistics for a specific dataset."""
        dataset = self.get_object()
        
        point_stats = GPSPoint.objects.filter(dataset=dataset).aggregate(
            total_points=Count('id'),
            total_entities=Count('entity_id', distinct=True),
            first_timestamp=Min('timestamp'),
            last_timestamp=Max('timestamp'),
            valid_count=Count('id', filter=Q(is_valid=True)),
            invalid_count=Count('id', filter=Q(is_valid=False))
        )
        
        trajectory_count = Trajectory.objects.filter(dataset=dataset).count()
        
        geo_bounds = GPSPoint.objects.filter(
            dataset=dataset,
            is_valid=True
        ).aggregate(
            min_lon=Min('longitude'),
            max_lon=Max('longitude'),
            min_lat=Min('latitude'),
            max_lat=Max('latitude')
        )
        
        total = point_stats['total_points']
        valid = point_stats['valid_count']
        validity_rate = round((valid / total * 100), 2) if total > 0 else 0.0
        
        return Response({
            'dataset_id': dataset.id,
            'dataset_name': dataset.name,
            'total_points': total,
            'total_entities': point_stats['total_entities'],
            'total_trajectories': trajectory_count,
            'date_range': {
                'start': point_stats['first_timestamp'],
                'end': point_stats['last_timestamp']
            },
            'validity_rate': validity_rate,
            'valid_points': valid,
            'invalid_points': point_stats['invalid_count'],
            'geographic_bounds': geo_bounds if all(geo_bounds.values()) else None
        })
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a dataset (soft delete)."""
        dataset = self.get_object()
        dataset.is_active = False
        dataset.save()
        return Response({'status': 'Dataset deactivated'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Reactivate a dataset."""
        dataset = self.get_object()
        dataset.is_active = True
        dataset.save()
        return Response({'status': 'Dataset activated'})


# ============================================================================
# GPS Points ViewSet - FIXED
# ============================================================================

class GPSPointViewSet(viewsets.ModelViewSet):
    """
    API endpoints for GPS point data.
    """
    queryset = GPSPoint.objects.all()
    serializer_class = GPSPointGeoJSONSerializer
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return GPSPointListSerializer
        elif self.action == 'create':
            return GPSPointCreateSerializer
        return GPSPointGeoJSONSerializer
    
    def get_queryset(self):
        """Apply filters from query parameters."""
        queryset = super().get_queryset()
        
        dataset_id = self.request.query_params.get('dataset')
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        
        entity_id = self.request.query_params.get('entity_id')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')
        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
        if end_time:
            queryset = queryset.filter(timestamp__lte=end_time)
        
        only_valid = self.request.query_params.get('only_valid', 'true').lower() == 'true'
        if only_valid:
            queryset = queryset.filter(is_valid=True)
        
        return queryset.select_related('dataset').order_by('timestamp')
    
    @action(detail=False, methods=['post'])
    def query(self, request):
        """
        FIXED: Advanced query endpoint with spatial filtering.
        Returns proper GeoJSON FeatureCollection.
        """
        serializer = GPSPointQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        
        # Build query
        queryset = GPSPoint.objects.all()
        
        if 'dataset' in params:
            queryset = queryset.filter(dataset_id=params['dataset'])
        
        if 'entity_id' in params:
            queryset = queryset.filter(entity_id=params['entity_id'])
        
        if 'start_time' in params:
            queryset = queryset.filter(timestamp__gte=params['start_time'])
        
        if 'end_time' in params:
            queryset = queryset.filter(timestamp__lte=params['end_time'])
        
        # Spatial filter (bounding box)
        if all(k in params for k in ['min_lon', 'max_lon', 'min_lat', 'max_lat']):
            queryset = queryset.filter(
                longitude__gte=params['min_lon'],
                longitude__lte=params['max_lon'],
                latitude__gte=params['min_lat'],
                latitude__lte=params['max_lat']
            )
        
        if params.get('only_valid', True):
            queryset = queryset.filter(is_valid=True)
        
        # Apply limit
        limit = params.get('limit', 1000)
        queryset = queryset[:limit]
        
        # FIXED: Serialize points to GeoJSON features
        point_serializer = GPSPointGeoJSONSerializer(queryset, many=True)
        
        # Debug logging
        logger.info(f"Query returned {len(point_serializer.data)} points")
        
        # Return proper GeoJSON FeatureCollection
        return Response({
            'type': 'FeatureCollection',
            'count': len(point_serializer.data),
            'features': point_serializer.data  # This is the array of features
        })
    
    @action(detail=False, methods=['get'])
    def by_entity(self, request):
        """Get all points for a specific entity."""
        entity_id = request.query_params.get('entity_id')
        dataset_id = request.query_params.get('dataset')
        
        if not entity_id:
            return Response(
                {'error': 'entity_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(entity_id=entity_id)
        
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create GPS points."""
        dataset_id = request.data.get('dataset')
        points_data = request.data.get('points', [])
        
        if not dataset_id:
            return Response(
                {'error': 'dataset parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not points_data:
            return Response(
                {'error': 'points array required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            dataset = Dataset.objects.get(id=dataset_id)
        except Dataset.DoesNotExist:
            return Response(
                {'error': 'Dataset not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(
            {'error': 'Bulk creation not yet implemented'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


# ============================================================================
# Trajectories ViewSet
# ============================================================================

class TrajectoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for trajectory data."""
    queryset = Trajectory.objects.all()
    serializer_class = TrajectoryGeoJSONSerializer
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TrajectoryListSerializer
        return TrajectoryGeoJSONSerializer
    
    def get_queryset(self):
        """Filter trajectories by query parameters."""
        queryset = super().get_queryset()
        
        dataset_id = self.request.query_params.get('dataset')
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        
        entity_id = self.request.query_params.get('entity_id')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(trajectory_date=date)
        
        return queryset.select_related('dataset').order_by('trajectory_date')
    
    @action(detail=False, methods=['post'])
    def query(self, request):
        """Advanced trajectory query endpoint."""
        serializer = TrajectoryQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        
        queryset = Trajectory.objects.all()
        
        if 'dataset' in params:
            queryset = queryset.filter(dataset_id=params['dataset'])
        
        if 'entity_id' in params:
            queryset = queryset.filter(entity_id=params['entity_id'])
        
        if 'date' in params:
            queryset = queryset.filter(trajectory_date=params['date'])
        
        if 'start_date' in params:
            queryset = queryset.filter(trajectory_date__gte=params['start_date'])
        
        if 'end_date' in params:
            queryset = queryset.filter(trajectory_date__lte=params['end_date'])
        
        if 'min_distance' in params:
            queryset = queryset.filter(total_distance_meters__gte=params['min_distance'])
        
        if 'max_distance' in params:
            queryset = queryset.filter(total_distance_meters__lte=params['max_distance'])
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TrajectoryGeoJSONSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TrajectoryGeoJSONSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def analyze(self, request, pk=None):
        """Analyze a specific trajectory."""
        trajectory = self.get_object()
        
        return Response({
            'trajectory_id': trajectory.id,
            'entity_id': trajectory.entity_id,
            'date': trajectory.trajectory_date,
            'metrics': trajectory.metrics,
            'message': 'Advanced analysis not yet implemented'
        })


# ============================================================================
# Import Jobs ViewSet
# ============================================================================

class ImportJobViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for managing data imports."""
    queryset = ImportJob.objects.all()
    serializer_class = ImportJobSerializer
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ImportJobListSerializer
        return ImportJobSerializer
    
    def get_queryset(self):
        """Filter by dataset and status."""
        queryset = super().get_queryset()
        
        dataset_id = self.request.query_params.get('dataset')
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('dataset').order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def start_import(self, request):
        """Start a new data import job."""
        serializer = ImportJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        
        dataset = get_object_or_404(Dataset, id=params['dataset_id'])
        
        importer = MobilityDataImporter(dataset)
        
        import_config = {
            'field_mapping': params.get('field_mapping', {}),
            'validation': params.get('validation_config', {}),
            'delimiter': params.get('delimiter', ','),
            'skip_header': params.get('skip_header', True),
            'file_format': params.get('file_format', 'csv')
        }
        
        try:
            if params['source_type'] == 'file':
                if params.get('file_format') == 'csv':
                    job = importer.import_from_csv(
                        params['source_path'],
                        import_config
                    )
                elif params.get('file_format') == 'txt':
                    job = importer.import_text_file(
                        params['source_path'],
                        import_config
                    )
                else:
                    return Response(
                        {'error': f"Unsupported file format: {params.get('file_format')}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    {'error': f"Source type '{params['source_type']}' not yet supported"},
                    status=status.HTTP_501_NOT_IMPLEMENTED
                )
            
            serializer = ImportJobSerializer(job)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            return Response(
                {'error': f"Import failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get current progress of an import job."""
        job = self.get_object()
        
        progress_pct = 0
        if job.total_records and job.total_records > 0:
            progress_pct = round(
                (job.processed_records / job.total_records) * 100,
                2
            )
        
        return Response({
            'id': job.id,
            'status': job.status,
            'progress_percentage': progress_pct,
            'processed_records': job.processed_records,
            'successful_records': job.successful_records,
            'failed_records': job.failed_records,
            'total_records': job.total_records,
            'started_at': job.started_at,
            'duration_seconds': job.duration_seconds
        })


# ============================================================================
# Entity Statistics ViewSet
# ============================================================================

class EntityViewSet(viewsets.ViewSet):
    """API endpoints for entity-level statistics and analysis."""
    
    def list(self, request):
        """List all entities with summary statistics."""
        dataset_id = request.query_params.get('dataset')
        min_points = request.query_params.get('min_points', 0)
        
        queryset = GPSPoint.objects.filter(is_valid=True)
        
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        
        # Aggregate by entity
        stats = queryset.values('entity_id').annotate(
            total_points=Count('id'),
            first_timestamp=Min('timestamp'),
            last_timestamp=Max('timestamp'),
            active_days=Count('timestamp__date', distinct=True),
            avg_speed=Avg('speed')
        ).filter(
            total_points__gte=min_points
        ).order_by('-total_points')
        
        # Calculate derived metrics
        for s in stats:
            if s['active_days'] > 0:
                s['avg_points_per_day'] = round(
                    s['total_points'] / s['active_days'],
                    2
                )
            else:
                s['avg_points_per_day'] = 0.0
        
        serializer = EntityStatisticsSerializer(stats, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get detailed statistics for a specific entity."""
        dataset_id = request.query_params.get('dataset')
        
        queryset = GPSPoint.objects.filter(entity_id=pk, is_valid=True)
        
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        
        if not queryset.exists():
            return Response(
                {'error': f'Entity {pk} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stats = queryset.aggregate(
            total_points=Count('id'),
            first_timestamp=Min('timestamp'),
            last_timestamp=Max('timestamp'),
            active_days=Count('timestamp__date', distinct=True),
            avg_speed=Avg('speed')
        )
        
        stats['entity_id'] = pk
        if stats['active_days'] > 0:
            stats['avg_points_per_day'] = round(
                stats['total_points'] / stats['active_days'],
                2
            )
        else:
            stats['avg_points_per_day'] = 0.0
        
        trajectory_stats = Trajectory.objects.filter(
            entity_id=pk
        ).aggregate(
            total_trajectories=Count('id'),
            total_distance=Sum('total_distance_meters'),
            avg_distance=Avg('total_distance_meters')
        )
        
        stats['total_trajectories'] = trajectory_stats['total_trajectories']
        stats['total_distance_meters'] = trajectory_stats['total_distance']
        stats['avg_trajectory_distance'] = trajectory_stats['avg_distance']
        
        serializer = EntityStatisticsSerializer(stats)
        return Response(serializer.data)