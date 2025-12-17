"""
============================================================================
Django REST Framework Views pour T-Drive
============================================================================
Description: Endpoints API pour l'import, la requête et l'analyse
            des données T-Drive
============================================================================
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Min, Max, Q
from django.contrib.gis.geos import Polygon

from apps.mobility.models import (
    TDriveRawPoint,
    TDriveTrajectory,
    TDriveImportLog
)
from apps.mobility.serializers import (
    TDriveRawPointSerializer,
    TDriveRawPointListSerializer,
    TDriveTrajectorySerializer,
    TDriveTrajectoryListSerializer,
    TDriveImportLogSerializer,
    TDriveImportLogListSerializer,
    ImportRequestSerializer,
    QueryParametersSerializer,
    TaxiStatisticsSerializer
)
from apps.mobility.services.tdrive_importer import TDriveImporter
from apps.mobility.services.trajectory_analyzer import TrajectoryAnalyzer

from skmob.preprocessing import clustering



# ============================================================================
# Pagination
# ============================================================================

class StandardResultsSetPagination(PageNumberPagination):
    """Pagination standard pour les résultats d'API."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


# ============================================================================
# TDriveRawPoint ViewSet
# ============================================================================

class TDriveRawPointViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les points GPS bruts T-Drive.
    """
    queryset = TDriveRawPoint.objects.all()
    serializer_class = TDriveRawPointSerializer
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return TDriveRawPointListSerializer
        return TDriveRawPointSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        taxi_id = self.request.query_params.get('taxi_id')
        if taxi_id:
            queryset = queryset.filter(taxi_id=taxi_id)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        only_valid = self.request.query_params.get('only_valid', 'true').lower() == 'true'
        if only_valid:
            queryset = queryset.filter(is_valid=True)

        return queryset.select_related().order_by('taxi_id', 'timestamp')

    @action(detail=False, methods=['get'])
    def by_taxi(self, request):
        """Points d’un taxi spécifique."""
        taxi_id = request.query_params.get('taxi_id')
        if not taxi_id:
            return Response({'error': 'taxi_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(taxi_id=taxi_id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def in_bbox(self, request):
        """Points dans une bounding box."""
        serializer = QueryParametersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        bbox = Polygon((
            (data['min_lon'], data['min_lat']),
            (data['min_lon'], data['max_lat']),
            (data['max_lon'], data['max_lat']),
            (data['max_lon'], data['min_lat']),
            (data['min_lon'], data['min_lat'])
        ), srid=4326)

        # queryset = self.get_queryset().filter(geom__within=bbox)
        queryset = self.get_queryset().filter(
            longitude__gte=data['min_lon'],
            longitude__lte=data['max_lon'],
            latitude__gte=data['min_lat'],
            latitude__lte=data['max_lat'],
        )   
        if data.get('taxi_id'):
            queryset = queryset.filter(taxi_id=data['taxi_id'])

        limit = data.get('limit', 1000) #TODO modify limit in front
        queryset = queryset[:limit]

        serializer = TDriveRawPointSerializer(queryset, many=True)
        return Response({
            'type': 'FeatureCollection',
            'count': len(serializer.data),
            'features': serializer.data
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques globales sur les points GPS."""
        queryset = self.get_queryset()
        stats = queryset.aggregate(
            total_points=Count('id'),
            total_taxis=Count('taxi_id', distinct=True),
            first_timestamp=Min('timestamp'),
            last_timestamp=Max('timestamp'),
            valid_count=Count('id', filter=Q(is_valid=True)),
            invalid_count=Count('id', filter=Q(is_valid=False))
        )

        return Response({
            'total_points': stats['total_points'],
            'total_taxis': stats['total_taxis'],
            'date_range': {'start': stats['first_timestamp'], 'end': stats['last_timestamp']},
            'valid_points': stats['valid_count'],
            'invalid_points': stats['invalid_count'],
            'validity_rate': round((stats['valid_count'] / stats['total_points'] * 100), 2)
            if stats['total_points'] > 0 else 0
        })


# ============================================================================
# TDriveTrajectory ViewSet
# ============================================================================

class TDriveTrajectoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les trajectoires agrégées T-Drive."""
    queryset = TDriveTrajectory.objects.all()
    serializer_class = TDriveTrajectorySerializer
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return TDriveTrajectoryListSerializer
        return TDriveTrajectorySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        taxi_id = self.request.query_params.get('taxi_id')
        date = self.request.query_params.get('date')
        if taxi_id:
            queryset = queryset.filter(taxi_id=taxi_id)
        if date:
            queryset = queryset.filter(trajectory_date=date)
        return queryset.order_by('taxi_id', 'trajectory_date')

    @action(detail=False, methods=['get'])
    def by_taxi(self, request):
        taxi_id = request.query_params.get('taxi_id')
        if not taxi_id:
            return Response({'error': 'taxi_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset().filter(taxi_id=taxi_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def analyze_stops(self, request, pk=None):
        """Detect stops and activity patterns in a trajectory."""
        trajectory = self.get_object()
        
        analyzer = TrajectoryAnalyzer(
            stop_detection_threshold=300,  # 5 minutes
            min_points_per_trajectory=10
        )
        
        analysis = analyzer.analyze_taxi_trajectories(
            taxi_id=trajectory.taxi_id,
            date=trajectory.trajectory_date
        )
        
        return Response({
            'trajectory_id': pk,
            'mobility_metrics': analysis['metrics'],
            'detected_stops': analysis['stops'],
            'od_pairs': analysis['od_pairs']
        })


# ============================================================================
# TDriveImportLog ViewSet
# ============================================================================

class TDriveImportLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les logs d'import T-Drive."""
    queryset = TDriveImportLog.objects.all()
    serializer_class = TDriveImportLogSerializer
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return TDriveImportLogListSerializer
        return TDriveImportLogSerializer

    @action(detail=False, methods=['post'])
    def start(self, request):
        """Lancer un nouvel import."""
        serializer = ImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        importer = TDriveImporter(
            strict_validation=data.get('strict_validation', False),
            use_beijing_bbox=data.get('use_beijing_bbox', True)
        )

        try:
            if data.get('file_path'):
                result = importer.import_file(data['file_path'])
            elif data.get('directory_path'):
                result = importer.import_directory(
                    data['directory_path'],
                    max_files=data.get('max_files')
                )
            else:
                return Response({'error': 'file_path or directory_path is required'},
                                status=status.HTTP_400_BAD_REQUEST)

            return Response(result, status=status.HTTP_200_OK)

        except FileNotFoundError as e:
            return Response({'error': f'File not found: {str(e)}'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': f'Import failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='batch/(?P<batch_id>[^/.]+)')
    def batch(self, request, batch_id=None):
        """Récupère tous les imports d’un batch."""
        queryset = self.get_queryset().filter(import_batch_id=batch_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'batch_id': batch_id,
            'import_count': len(serializer.data),
            'imports': serializer.data
        })


# ============================================================================
# TDriveTaxi ViewSet
# ============================================================================

class TDriveTaxiViewSet(viewsets.ViewSet):
    """ViewSet pour les statistiques par taxi."""

    def list(self, request):
        stats = TDriveRawPoint.objects.filter(is_valid=True).values('taxi_id').annotate(
            total_points=Count('id'),
            first_record=Min('timestamp'),
            last_record=Max('timestamp'),
            active_days=Count('timestamp__date', distinct=True)
        ).order_by('-total_points')

        for s in stats:
            s['avg_points_per_day'] = round(s['total_points'] / s['active_days'], 2) if s['active_days'] > 0 else 0.0

        serializer = TaxiStatisticsSerializer(instance=stats, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        stats = TDriveRawPoint.objects.filter(taxi_id=pk, is_valid=True).aggregate(
            total_points=Count('id'),
            first_record=Min('timestamp'),
            last_record=Max('timestamp'),
            active_days=Count('timestamp__date', distinct=True)
        )

        if not stats['total_points']:
            return Response({'error': f'Taxi {pk} not found'}, status=status.HTTP_404_NOT_FOUND)

        stats['taxi_id'] = pk
        stats['avg_points_per_day'] = round(stats['total_points'] / stats['active_days'], 2) if stats['active_days'] > 0 else 0.0

        serializer = TaxiStatisticsSerializer(instance=stats)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def cluster_mobility_profiles(self, request):
        """Cluster taxis by mobility behavior patterns."""
        taxi_ids = request.data.get('taxi_ids', [])
        
        # Collect mobility metrics for each taxi
        profiles = []
        for taxi_id in taxi_ids:
            analyzer = TrajectoryAnalyzer()
            # Get trajectory data
            tdf = self._create_trajdataframe(taxi_id)
            
            # Calculate mobility metrics
            metrics = {
                'radius_of_gyration': radius_of_gyration(tdf),
                'number_of_locations': number_of_locations(tdf),
                'entropy': tdf.trajectory.entropy()
            }
            profiles.append(metrics)
        
        # Apply clustering (k-means, DBSCAN, etc.)
        clusters = self._cluster_profiles(profiles)
        
        return Response({
            'clusters': clusters,
            'interpretations': {
                'high_mobility': 'Wide coverage, many locations',
                'local_service': 'Limited area, repeated routes',
                'hub_focused': 'Concentrated around key points'
            }
        })