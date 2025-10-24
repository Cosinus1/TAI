"""
============================================================================
Django REST Framework Serializers pour T-Drive
============================================================================
Description: Serializers pour convertir les modèles Django en JSON
            et valider les données entrantes de l'API
============================================================================
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.mobility.models import (
    TDriveRawPoint,
    TDriveTrajectory,
    TDriveImportLog,
    TDriveValidationError
)


class TDriveRawPointSerializer(GeoFeatureModelSerializer):
    """
    Serializer pour les points GPS bruts avec support GeoJSON.
    
    Permet de retourner les points au format GeoJSON pour visualisation
    sur des cartes (Leaflet, Mapbox, etc.)
    
    Example output:
    {
        "type": "Feature",
        "id": 1,
        "geometry": {
            "type": "Point",
            "coordinates": [116.51172, 39.92123]
        },
        "properties": {
            "taxi_id": "1",
            "timestamp": "2008-02-02T13:30:39Z",
            "is_valid": true
        }
    }
    """
    
    class Meta:
        model = TDriveRawPoint
        geo_field = 'geom'
        fields = [
            'id',
            'taxi_id',
            'timestamp',
            'longitude',
            'latitude',
            'is_valid',
            'validation_notes',
            'imported_at'
        ]
        read_only_fields = ['id', 'imported_at']


class TDriveRawPointListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour les listes de points (sans géométrie).
    
    Utilisé pour les endpoints de listing où la géométrie complète
    n'est pas nécessaire pour optimiser les performances.
    """
    
    class Meta:
        model = TDriveRawPoint
        fields = [
            'id',
            'taxi_id',
            'timestamp',
            'longitude',
            'latitude',
            'is_valid'
        ]
        read_only_fields = ['id']


class TDriveTrajectorySerializer(GeoFeatureModelSerializer):
    """
    Serializer pour les trajectoires avec géométrie LineString.
    
    Retourne les trajectoires complètes au format GeoJSON pour
    visualisation de parcours complets.
    
    Example output:
    {
        "type": "Feature",
        "id": 1,
        "geometry": {
            "type": "LineString",
            "coordinates": [[116.51, 39.92], [116.52, 39.93], ...]
        },
        "properties": {
            "taxi_id": "1",
            "trajectory_date": "2008-02-02",
            "point_count": 150,
            "total_distance_meters": 15000.5,
            "avg_speed_kmh": 35.2
        }
    }
    """
    
    class Meta:
        model = TDriveTrajectory
        geo_field = 'geom'
        fields = [
            'id',
            'taxi_id',
            'trajectory_date',
            'start_time',
            'end_time',
            'point_count',
            'total_distance_meters',
            'duration_seconds',
            'avg_speed_kmh',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TDriveTrajectoryListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour les listes de trajectoires.
    """
    
    class Meta:
        model = TDriveTrajectory
        fields = [
            'id',
            'taxi_id',
            'trajectory_date',
            'point_count',
            'total_distance_meters',
            'avg_speed_kmh'
        ]


class TDriveValidationErrorSerializer(serializers.ModelSerializer):
    """
    Serializer pour les erreurs de validation.
    """
    
    class Meta:
        model = TDriveValidationError
        fields = [
            'id',
            'line_number',
            'raw_line',
            'error_type',
            'error_message',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TDriveImportLogSerializer(serializers.ModelSerializer):
    """
    Serializer pour les logs d'import avec erreurs associées.
    
    Inclut les erreurs de validation via une relation nested.
    """
    
    validation_errors = TDriveValidationErrorSerializer(many=True, read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = TDriveImportLog
        fields = [
            'id',
            'import_batch_id',
            'file_name',
            'file_path',
            'total_lines',
            'successful_imports',
            'failed_imports',
            'start_time',
            'end_time',
            'duration_seconds',
            'status',
            'error_message',
            'created_at',
            'success_rate',
            'validation_errors'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_success_rate(self, obj):
        """
        Calcule le taux de succès de l'import.
        
        Returns:
            float: Pourcentage de lignes importées avec succès
        """
        if obj.total_lines and obj.total_lines > 0:
            return round((obj.successful_imports / obj.total_lines) * 100, 2)
        return 0.0


class TDriveImportLogListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour les listes de logs.
    """
    
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = TDriveImportLog
        fields = [
            'id',
            'import_batch_id',
            'file_name',
            'successful_imports',
            'failed_imports',
            'status',
            'duration_seconds',
            'created_at',
            'success_rate'
        ]
    
    def get_success_rate(self, obj):
        """Calcule le taux de succès."""
        if obj.total_lines and obj.total_lines > 0:
            return round((obj.successful_imports / obj.total_lines) * 100, 2)
        return 0.0


class TaxiStatisticsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques par taxi.
    
    Utilisé pour les endpoints d'analyse et de monitoring.
    """
    
    taxi_id = serializers.CharField()
    total_points = serializers.IntegerField()
    first_record = serializers.DateTimeField()
    last_record = serializers.DateTimeField()
    active_days = serializers.IntegerField()
    avg_points_per_day = serializers.FloatField()
    

class ImportRequestSerializer(serializers.Serializer):
    """
    Serializer pour les requêtes d'import.
    
    Valide les paramètres envoyés par le client pour lancer un import.
    """
    
    file_path = serializers.CharField(
        required=False,
        help_text="Chemin vers un fichier unique à importer"
    )
    directory_path = serializers.CharField(
        required=False,
        help_text="Chemin vers un répertoire contenant plusieurs fichiers"
    )
    max_files = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Nombre maximum de fichiers à importer (pour directory_path)"
    )
    strict_validation = serializers.BooleanField(
        default=False,
        help_text="Active la validation stricte (rejette les points invalides)"
    )
    use_beijing_bbox = serializers.BooleanField(
        default=True,
        help_text="Vérifie que les points sont dans la bbox de Beijing"
    )
    
    def validate(self, data):
        """
        Valide que soit file_path soit directory_path est fourni.
        """
        if not data.get('file_path') and not data.get('directory_path'):
            raise serializers.ValidationError(
                "Either 'file_path' or 'directory_path' must be provided"
            )
        
        if data.get('file_path') and data.get('directory_path'):
            raise serializers.ValidationError(
                "Cannot provide both 'file_path' and 'directory_path'"
            )
        
        return data


class QueryParametersSerializer(serializers.Serializer):
    """
    Serializer pour les paramètres de requête des points GPS.
    
    Permet de filtrer les points par taxi, période temporelle et bbox spatiale.
    """
    
    taxi_id = serializers.CharField(
        required=False,
        help_text="Filtrer par ID de taxi"
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text="Date de début (format ISO 8601)"
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text="Date de fin (format ISO 8601)"
    )
    min_lon = serializers.FloatField(
        required=False,
        help_text="Longitude minimale de la bounding box"
    )
    max_lon = serializers.FloatField(
        required=False,
        help_text="Longitude maximale de la bounding box"
    )
    min_lat = serializers.FloatField(
        required=False,
        help_text="Latitude minimale de la bounding box"
    )
    max_lat = serializers.FloatField(
        required=False,
        help_text="Latitude maximale de la bounding box"
    )
    limit = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=10000,
        default=1000,
        help_text="Nombre maximum de résultats"
    )
    only_valid = serializers.BooleanField(
        default=True,
        help_text="Ne retourner que les points valides"
    )
    
    def validate(self, data):
        """
        Valide la cohérence des paramètres de bbox.
        """
        bbox_params = ['min_lon', 'max_lon', 'min_lat', 'max_lat']
        bbox_provided = [param for param in bbox_params if param in data]
        
        # Si une bbox est fournie, tous les paramètres doivent l'être
        if bbox_provided and len(bbox_provided) != 4:
            raise serializers.ValidationError(
                "All bbox parameters (min_lon, max_lon, min_lat, max_lat) must be provided together"
            )
        
        # Validation de la cohérence de la bbox
        if len(bbox_provided) == 4:
            if data['min_lon'] >= data['max_lon']:
                raise serializers.ValidationError("min_lon must be less than max_lon")
            if data['min_lat'] >= data['max_lat']:
                raise serializers.ValidationError("min_lat must be less than max_lat")
        
        # Validation des dates
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError("start_date must be before end_date")
        
        return data