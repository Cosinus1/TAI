"""
============================================================================
Django REST Framework Serializers - FIXED
============================================================================
Key fix: Added avg_speed field to EntityStatisticsSerializer
============================================================================
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from apps.mobility.models import (
    Dataset,
    GPSPoint,
    Trajectory,
    ImportJob,
    ValidationError
)


# ============================================================================
# Dataset Serializers
# ============================================================================

class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for Dataset management."""
    
    total_points = serializers.SerializerMethodField()
    total_entities = serializers.SerializerMethodField()
    
    class Meta:
        model = Dataset
        fields = [
            'id',
            'name',
            'description',
            'dataset_type',
            'data_format',
            'field_mapping',
            'source_url',
            'geographic_scope',
            'temporal_range_start',
            'temporal_range_end',
            'is_active',
            'created_at',
            'updated_at',
            'total_points',
            'total_entities'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_points(self, obj):
        """Count total GPS points in dataset."""
        return obj.gps_points.count()
    
    def get_total_entities(self, obj):
        """Count distinct entities in dataset."""
        return obj.gps_points.values('entity_id').distinct().count()


class DatasetListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dataset lists."""
    
    class Meta:
        model = Dataset
        fields = [
            'id',
            'name',
            'dataset_type',
            'geographic_scope',
            'is_active',
            'created_at'
        ]


# ============================================================================
# GPS Point Serializers
# ============================================================================

class GPSPointGeoJSONSerializer(GeoFeatureModelSerializer):
    """
    GeoJSON serializer for GPS points.
    
    Output format:
    {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {...}
    }
    """
    
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    
    class Meta:
        model = GPSPoint
        geo_field = 'geom'
        fields = [
            'id',
            'dataset',
            'dataset_name',
            'entity_id',
            'timestamp',
            'longitude',
            'latitude',
            'altitude',
            'accuracy',
            'speed',
            'heading',
            'is_valid',
            'extra_attributes'
        ]
        read_only_fields = ['id', 'dataset_name']


class GPSPointListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for point lists (no geometry)."""
    
    class Meta:
        model = GPSPoint
        fields = [
            'id',
            'entity_id',
            'timestamp',
            'longitude',
            'latitude',
            'speed',
            'is_valid'
        ]


class GPSPointCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating GPS points via API.
    Used when users upload their own data.
    """
    
    class Meta:
        model = GPSPoint
        fields = [
            'dataset',
            'entity_id',
            'timestamp',
            'longitude',
            'latitude',
            'altitude',
            'accuracy',
            'speed',
            'heading',
            'extra_attributes'
        ]
    
    def validate(self, data):
        """Validate coordinate ranges."""
        lon = data.get('longitude')
        lat = data.get('latitude')
        
        if lon is not None and not (-180 <= lon <= 180):
            raise serializers.ValidationError(
                {'longitude': 'Must be between -180 and 180'}
            )
        
        if lat is not None and not (-90 <= lat <= 90):
            raise serializers.ValidationError(
                {'latitude': 'Must be between -90 and 90'}
            )
        
        return data


# ============================================================================
# Trajectory Serializers
# ============================================================================

class TrajectoryGeoJSONSerializer(GeoFeatureModelSerializer):
    """
    GeoJSON serializer for trajectories.
    
    Output format:
    {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[lon, lat], ...]},
        "properties": {...}
    }
    """
    
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    
    class Meta:
        model = Trajectory
        geo_field = 'geom'
        fields = [
            'id',
            'dataset',
            'dataset_name',
            'entity_id',
            'trajectory_date',
            'start_time',
            'end_time',
            'duration_seconds',
            'point_count',
            'total_distance_meters',
            'avg_speed_kmh',
            'max_speed_kmh',
            'metrics',
            'created_at'
        ]
        read_only_fields = ['id', 'dataset_name', 'created_at']


class TrajectoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for trajectory lists."""
    
    class Meta:
        model = Trajectory
        fields = [
            'id',
            'entity_id',
            'trajectory_date',
            'point_count',
            'total_distance_meters',
            'avg_speed_kmh',
            'duration_seconds'
        ]


# ============================================================================
# Import Job Serializers
# ============================================================================

class ValidationErrorSerializer(serializers.ModelSerializer):
    """Serializer for validation errors."""
    
    class Meta:
        model = ValidationError
        fields = [
            'id',
            'record_number',
            'error_type',
            'error_message',
            'field_name',
            'expected_value',
            'actual_value',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ImportJobSerializer(serializers.ModelSerializer):
    """Detailed serializer for import jobs."""
    
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    success_rate = serializers.SerializerMethodField()
    validation_errors = ValidationErrorSerializer(many=True, read_only=True)
    
    class Meta:
        model = ImportJob
        fields = [
            'id',
            'dataset',
            'dataset_name',
            'source_type',
            'source_path',
            'import_config',
            'status',
            'total_records',
            'processed_records',
            'successful_records',
            'failed_records',
            'created_at',
            'started_at',
            'completed_at',
            'duration_seconds',
            'error_message',
            'success_rate',
            'validation_errors'
        ]
        read_only_fields = [
            'id',
            'dataset_name',
            'created_at',
            'started_at',
            'completed_at',
            'success_rate'
        ]
    
    def get_success_rate(self, obj):
        """Calculate import success rate percentage."""
        if obj.processed_records == 0:
            return 0.0
        return round((obj.successful_records / obj.processed_records) * 100, 2)


class ImportJobListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for import job lists."""
    
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = ImportJob
        fields = [
            'id',
            'dataset_name',
            'source_type',
            'status',
            'processed_records',
            'successful_records',
            'failed_records',
            'created_at',
            'duration_seconds',
            'success_rate'
        ]
    
    def get_success_rate(self, obj):
        if obj.processed_records == 0:
            return 0.0
        return round((obj.successful_records / obj.processed_records) * 100, 2)


class ImportJobCreateSerializer(serializers.Serializer):
    """
    Serializer for initiating import jobs.
    Validates user input for starting imports.
    """
    
    dataset_id = serializers.UUIDField(
        required=True,
        help_text="Target dataset UUID"
    )
    
    source_type = serializers.ChoiceField(
        required=True,
        choices=['file', 'directory', 'url', 'api'],
        help_text="Type of import source"
    )
    
    source_path = serializers.CharField(
        required=True,
        help_text="Path, URL, or identifier of data source"
    )
    
    # Optional configuration
    field_mapping = serializers.JSONField(
        required=False,
        help_text="Column/field name mapping"
    )
    
    validation_config = serializers.JSONField(
        required=False,
        help_text="Validation rules configuration"
    )
    
    file_format = serializers.ChoiceField(
        required=False,
        choices=['csv', 'txt', 'json', 'geojson'],
        default='csv',
        help_text="File format"
    )
    
    delimiter = serializers.CharField(
        required=False,
        default=',',
        max_length=5,
        help_text="Field delimiter for CSV/TXT"
    )
    
    skip_header = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Skip first row as header"
    )
    
    max_files = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Maximum files to process (for directory imports)"
    )
    
    def validate_dataset_id(self, value):
        """Ensure dataset exists and is active."""
        try:
            dataset = Dataset.objects.get(id=value, is_active=True)
        except Dataset.DoesNotExist:
            raise serializers.ValidationError("Dataset not found or inactive")
        return value


# ============================================================================
# Query Parameter Serializers
# ============================================================================

class GPSPointQuerySerializer(serializers.Serializer):
    """
    Serializer for GPS point query parameters.
    Validates filters for point retrieval.
    """
    
    dataset = serializers.UUIDField(
        required=False,
        help_text="Filter by dataset UUID"
    )
    
    entity_id = serializers.CharField(
        required=False,
        max_length=100,
        help_text="Filter by entity ID"
    )
    
    start_time = serializers.DateTimeField(
        required=False,
        help_text="Start of time range (ISO 8601)"
    )
    
    end_time = serializers.DateTimeField(
        required=False,
        help_text="End of time range (ISO 8601)"
    )
    
    min_lon = serializers.FloatField(
        required=False,
        min_value=-180,
        max_value=180,
        help_text="Minimum longitude"
    )
    max_lon = serializers.FloatField(
        required=False,
        min_value=-180,
        max_value=180,
        help_text="Maximum longitude"
    )
    min_lat = serializers.FloatField(
        required=False,
        min_value=-90,
        max_value=90,
        help_text="Minimum latitude"
    )
    max_lat = serializers.FloatField(
        required=False,
        min_value=-90,
        max_value=90,
        help_text="Maximum latitude"
    )
    
    only_valid = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Return only validated points"
    )
    
    limit = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=10000,
        default=1000,
        help_text="Maximum results to return"
    )
    
    def validate(self, data):
        """Validate query parameter consistency."""
        
        # Validate time range
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError(
                    "start_time must be before end_time"
                )
        
        # Validate bounding box
        bbox_params = ['min_lon', 'max_lon', 'min_lat', 'max_lat']
        bbox_provided = [p for p in bbox_params if p in data]
        
        if bbox_provided and len(bbox_provided) != 4:
            raise serializers.ValidationError(
                "All bounding box parameters must be provided together"
            )
        
        if len(bbox_provided) == 4:
            if data['min_lon'] >= data['max_lon']:
                raise serializers.ValidationError(
                    "min_lon must be less than max_lon"
                )
            if data['min_lat'] >= data['max_lat']:
                raise serializers.ValidationError(
                    "min_lat must be less than max_lat"
                )
        
        return data


class TrajectoryQuerySerializer(serializers.Serializer):
    """Serializer for trajectory query parameters."""
    
    dataset = serializers.UUIDField(
        required=False,
        help_text="Filter by dataset UUID"
    )
    
    entity_id = serializers.CharField(
        required=False,
        max_length=100,
        help_text="Filter by entity ID"
    )
    
    date = serializers.DateField(
        required=False,
        help_text="Filter by specific date"
    )
    
    start_date = serializers.DateField(
        required=False,
        help_text="Start of date range"
    )
    
    end_date = serializers.DateField(
        required=False,
        help_text="End of date range"
    )
    
    min_distance = serializers.FloatField(
        required=False,
        min_value=0,
        help_text="Minimum trajectory distance (meters)"
    )
    
    max_distance = serializers.FloatField(
        required=False,
        min_value=0,
        help_text="Maximum trajectory distance (meters)"
    )
    
    def validate(self, data):
        """Validate date ranges."""
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError(
                    "start_date must be before end_date"
                )
        
        if data.get('min_distance') and data.get('max_distance'):
            if data['min_distance'] >= data['max_distance']:
                raise serializers.ValidationError(
                    "min_distance must be less than max_distance"
                )
        
        return data


# ============================================================================
# Statistics Serializers - FIXED
# ============================================================================

class EntityStatisticsSerializer(serializers.Serializer):
    """Serializer for entity-level statistics."""
    
    entity_id = serializers.CharField()
    total_points = serializers.IntegerField()
    first_timestamp = serializers.DateTimeField()
    last_timestamp = serializers.DateTimeField()
    active_days = serializers.IntegerField()
    avg_points_per_day = serializers.FloatField()
    total_distance_meters = serializers.FloatField(required=False, allow_null=True)
    avg_speed = serializers.FloatField(required=False, allow_null=True)  # FIX: Changed from avg_speed_kmh to avg_speed
    
    # Optional trajectory statistics
    total_trajectories = serializers.IntegerField(required=False, allow_null=True)
    avg_trajectory_distance = serializers.FloatField(required=False, allow_null=True)


class DatasetStatisticsSerializer(serializers.Serializer):
    """Serializer for dataset-level statistics."""
    
    dataset_id = serializers.UUIDField()
    dataset_name = serializers.CharField()
    total_points = serializers.IntegerField()
    total_entities = serializers.IntegerField()
    total_trajectories = serializers.IntegerField()
    date_range = serializers.DictField()
    validity_rate = serializers.FloatField()
    geographic_bounds = serializers.DictField(required=False)