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
from django.db.models import Count, Min, Max, Avg, Q
from django.contrib.gis.geos import Polygon
from django.contrib.gis.measure import D

from apps.mobility.models import (
    TDriveRawPoint,
    TDriveTrajectory,
    TDriveImportLog,
    TDriveValidationError
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


class StandardResultsSetPagination(PageNumberPagination):
    """
    Pagination standard pour les résultats d'API.
    
    Configuration:
        - 100 résultats par page par défaut
        - Maximum 1000 résultats par page
        - Paramètre 'page_size' pour ajuster
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class TDriveRawPointViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les points GPS bruts T-Drive.
    
    Endpoints disponibles:
        GET /api/tdrive/points/ - Liste des points avec filtres
        GET /api/tdrive/points/{id}/ - Détail d'un point
        GET /api/tdrive/points/by_taxi/ - Points par taxi
        GET /api/tdrive/points/in_bbox/ - Points dans une bbox
        GET /api/tdrive/points/statistics/ - Statistiques globales
    
    Filtres disponibles:
        - taxi_id: Filtrer par ID de taxi
        - start_date: Date de début
        - end_date: Date de fin
        - only_valid: Ne retourner que les points valides (default: true)
    """
    
    queryset = TDriveRawPoint.objects.all()
    serializer_class = TDriveRawPointSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        """
        Utilise un serializer léger pour la liste, complet pour le détail.
        """
        if self.action == 'list':
            return TDriveRawPointListSerializer
        return TDriveRawPointSerializer
    
    def get_queryset(self):
        """
        Applique les filtres sur le queryset.
        
        Returns:
            QuerySet filtré selon les paramètres de requête
        """
        queryset = super().get_queryset()
        
        # Filtre par taxi_id
        taxi_id = self.request.query_params.get('taxi_id')
        if taxi_id:
            queryset = queryset.filter(taxi_id=taxi_id)
            print(f"[TDriveAPI] Filtering by taxi_id: {taxi_id}")
        
        # Filtre par période temporelle
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
            print(f"[TDriveAPI] Filtering by start_date: {start_date}")
        
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
            print(f"[TDriveAPI] Filtering by end_date: {end_date}")
        
        # Filtre par validité
        only_valid = self.request.query_params.get('only_valid', 'true').lower() == 'true'
        if only_valid:
            queryset = queryset.filter(is_valid=True)
            print(f"[TDriveAPI] Filtering only valid points")
        
        # Optimisation: sélection des champs nécessaires
        queryset = queryset.select_related().order_by('taxi_id', 'timestamp')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_taxi(self, request):
        """
        Récupère tous les points d'un taxi spécifique.
        
        Query params:
            - taxi_id (required): ID du taxi
            - start_date (optional): Date de début
            - end_date (optional): Date de fin
        
        Example:
            GET /api/tdrive/points/by_taxi/?taxi_id=1&start_date=2008-02-02T00:00:00
        
        Returns:
            GeoJSON FeatureCollection des points
        """
        print(f"[TDriveAPI] by_taxi endpoint called")
        
        taxi_id = request.query_params.get('taxi_id')
        
        if not taxi_id:
            return Response(
                {'error': 'taxi_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f"[TDriveAPI] Fetching points for taxi: {taxi_id}")
        
        queryset = self.get_queryset().filter(taxi_id=taxi_id)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def in_bbox(self, request):
        """
        Récupère les points GPS dans une bounding box géographique.
        
        Body params:
            - min_lon (required): Longitude minimale
            - max_lon (required): Longitude maximale
            - min_lat (required): Latitude minimale
            - max_lat (required): Latitude maximale
            - taxi_id (optional): Filtrer par taxi
            - limit (optional): Nombre max de résultats (default: 1000)
        
        Example:
            POST /api/tdrive/points/in_bbox/
            {
                "min_lon": 116.3,
                "max_lon": 116.5,
                "min_lat": 39.8,
                "max_lat": 40.0,
                "limit": 500
            }
        
        Returns:
            GeoJSON FeatureCollection des points dans la bbox
        """
        print(f"[TDriveAPI] in_bbox endpoint called")
        
        serializer = QueryParametersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Construction de la bbox PostGIS
        bbox_coords = (
            (data['min_lon'], data['min_lat']),
            (data['min_lon'], data['max_lat']),
            (data['max_lon'], data['max_lat']),
            (data['max_lon'], data['min_lat']),
            (data['min_lon'], data['min_lat'])
        )
        bbox = Polygon(bbox_coords, srid=4326)
        
        print(f"[TDriveAPI] Searching in bbox: {data['min_lon']},{data['min_lat']} to {data['max_lon']},{data['max_lat']}")
        
        # Requête spatiale
        queryset = self.get_queryset().filter(geom__within=bbox)
        
        # Filtre par taxi si fourni
        if data.get('taxi_id'):
            queryset = queryset.filter(taxi_id=data['taxi_id'])
        
        # Limitation des résultats
        limit = data.get('limit', 1000)
        queryset = queryset[:limit]
        
        print(f"[TDriveAPI] Found {queryset.count()} points in bbox")
        
        serializer = TDriveRawPointSerializer(queryset, many=True)
        return Response({
            'type': 'FeatureCollection',
            'count': len(serializer.data),
            'features': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Retourne des statistiques globales sur les points GPS.
        
        Returns:
            Dict avec statistiques:
            - total_points: Nombre total de points
            - total_taxis: Nombre de taxis uniques
            - date_range: Période couverte
            - valid_points: Nombre de points valides
            - invalid_points: Nombre de points invalides
        
        Example:
            GET /api/tdrive/points/statistics/
        """
        print(f"[TDriveAPI] statistics endpoint called")
        
        queryset = self.get_queryset()
        
        stats = queryset.aggregate(
            total_points=Count('id'),
            total_taxis=Count('taxi_id', distinct=True),
            first_timestamp=Min('timestamp'),
            last_timestamp=Max('timestamp'),
            valid_count=Count('id', filter=Q(is_valid=True)),
            invalid_count=Count('id', filter=Q(is_valid=False))
        )
        
        print(f"[TDriveAPI] Statistics computed: {stats['total_points']} points, {stats['total_taxis']} taxis")
        
        return Response({
            'total_points': stats['total_points'],
            'total_taxis': stats['total_taxis'],
            'date_range': {
                'start': stats['first_timestamp'],
                'end': stats['last_timestamp']
            },
            'valid_points': stats['valid_count'],
            'invalid_points': stats['invalid_count'],
            'validity_rate': round((stats['valid_count'] / stats['total_points'] * 100), 2) if stats['total_points'] > 0 else 0
        })


class TDriveTrajectoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les trajectoires agrégées T-Drive.
    
    Endpoints disponibles:
        GET /api/tdrive/trajectories/ - Liste des trajectoires
        GET /api/tdrive/trajectories/{id}/ - Détail d'une trajectoire
        GET /api/tdrive/trajectories/by_taxi/ - Trajectoires par taxi
        GET /api/tdrive/trajectories/by_date/ - Trajectoires par date
    """
    
    queryset = TDriveTrajectory.objects.all()
    serializer_class = TDriveTrajectorySerializer
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        """Utilise un serializer léger pour la liste."""
        if self.action == 'list':
            return TDriveTrajectoryListSerializer
        return TDriveTrajectorySerializer
    
    def get_queryset(self):
        """Applique les filtres sur le queryset."""
        queryset = super().get_queryset()
        
        # Filtre par taxi_id
        taxi_id = self.request.query_params.get('taxi_id')
        if taxi_id:
            queryset = queryset.filter(taxi_id=taxi_id)
        
        # Filtre par date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(trajectory_date=date)
        
        return queryset.order_by('taxi_id', 'trajectory_date')
    
    @action(detail=False, methods=['get'])
    def by_taxi(self, request):
        """
        Récupère toutes les trajectoires d'un taxi.
        
        Query params:
            - taxi_id (required): ID du taxi
        """
        taxi_id = request.query_params.get('taxi_id')
        
        if not taxi_id:
            return Response(
                {'error': 'taxi_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(taxi_id=taxi_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TDriveImportLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les logs d'import T-Drive.
    
    Endpoints disponibles:
        GET /api/tdrive/imports/ - Liste des imports
        GET /api/tdrive/imports/{id}/ - Détail d'un import
        POST /api/tdrive/imports/start/ - Lancer un nouvel import
        GET /api/tdrive/imports/batch/{batch_id}/ - Imports d'un batch
    """
    
    queryset = TDriveImportLog.objects.all()
    serializer_class = TDriveImportLogSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        """Utilise un serializer léger pour la liste."""
        if self.action == 'list':
            return TDriveImportLogListSerializer
        return TDriveImportLogSerializer
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Lance un nouvel import de données T-Drive.
        
        Body params:
            - file_path (optional): Chemin vers un fichier unique
            - directory_path (optional): Chemin vers un répertoire
            - max_files (optional): Nombre max de fichiers (pour directory)
            - strict_validation (optional): Validation stricte (default: false)
            - use_beijing_bbox (optional): Validation bbox Beijing (default: true)
        
        Example:
            POST /api/tdrive/imports/start/
            {
                "directory_path": "/app/data/tdrive/",
                "max_files": 10,
                "strict_validation": false
            }
        
        Returns:
            Statistiques de l'import
        """
        print(f"[TDriveAPI] Import start endpoint called")
        
        serializer = ImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Création de l'importeur
        importer = TDriveImporter(
            strict_validation=data.get('strict_validation', False),
            use_beijing_bbox=data.get('use_beijing_bbox', True)
        )
        
        print(f"[TDriveAPI] Starting import with params: {data}")
        
        # Lancement de l'import
        try:
            if data.get('file_path'):
                result = importer.import_file(data['file_path'])
            elif data.get('directory_path'):
                result = importer.import_directory(
                    data['directory_path'],
                    max_files=data.get('max_files')
                )
            
            print(f"[TDriveAPI] Import completed successfully")
            
            return Response(result, status=status.HTTP_200_OK)
        
        except FileNotFoundError as e:
            print(f"[TDriveAPI ERROR] File not found: {str(e)}")
            return Response(
                {'error': f'File not found: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            print(f"[TDriveAPI ERROR] Import failed: {str(e)}")
            return Response(
                {'error': f'Import failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='batch/(?P<batch_id>[^/.]+)')
    def batch(self, request, batch_id=None):
        """
        Récupère tous les imports d'un batch spécifique.
        
        Path params:
            - batch_id: UUID du batch
        
        Example:
            GET /api/tdrive/imports/batch/550e8400-e29b-41d4-a716-446655440000/
        """
        print(f"[TDriveAPI] Fetching batch: {batch_id}")
        
        queryset = self.get_queryset().filter(import_batch_id=batch_id)
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'batch_id': batch_id,
            'import_count': len(serializer.data),
            'imports': serializer.data
        })


class TDriveTaxiViewSet(viewsets.ViewSet):
    """
    ViewSet pour les statistiques par taxi.
    
    Endpoints disponibles:
        GET /api/tdrive/taxis/ - Liste des taxis avec stats
        GET /api/tdrive/taxis/{taxi_id}/ - Statistiques d'un taxi
    """
    
    def list(self, request):
        """
        Liste tous les taxis avec leurs statistiques.
        
        Returns:
            Liste des taxis avec:
            - taxi_id
            - total_points
            - first_record
            - last_record
            - active_days
        """
        print(f"[TDriveAPI] Listing all taxis")
        
        # Agrégation des statistiques par taxi
        stats = TDriveRawPoint.objects.filter(is_valid=True).values('taxi_id').annotate(
            total_points=Count('id'),
            first_record=Min('timestamp'),
            last_record=Max('timestamp'),
            active_days=Count('timestamp__date', distinct=True)
        ).order_by('-total_points')
        
        # Calcul de la moyenne de points par jour
        for stat in stats:
            if stat['active_days'] > 0:
                stat['avg_points_per_day'] = round(stat['total_points'] / stat['active_days'], 2)
            else:
                stat['avg_points_per_day'] = 0.0
        
        print(f"[TDriveAPI] Found {len(stats)} taxis")
        
        serializer = TaxiStatisticsSerializer(stats, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """
        Récupère les statistiques détaillées d'un taxi.
        
        Path params:
            - pk: taxi_id
        """
        print(f"[TDriveAPI] Fetching statistics for taxi: {pk}")
        
        stats = TDriveRawPoint.objects.filter(
            taxi_id=pk,
            is_valid=True
        ).aggregate(
            total_points=Count('id'),
            first_record=Min('timestamp'),
            last_record=Max('timestamp'),
            active_days=Count('timestamp__date', distinct=True)
        )
        
        if stats['total_points'] == 0:
            return Response(
                {'error': f'Taxi {pk} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        stats['taxi_id'] = pk
        if stats['active_days'] > 0:
            stats['avg_points_per_day'] = round(stats['total_points'] / stats['active_days'], 2)
        else:
            stats['avg_points_per_day'] = 0.0
        
        serializer = TaxiStatisticsSerializer(stats)
        return Response(serializer.data)izer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serial