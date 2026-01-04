"""
============================================================================
Django Models for Generic Mobility Data Management
============================================================================
Description: Flexible models for handling various mobility datasets
            (GPS traces, OD pairs, trajectories)
Author: Refactored for scalability
============================================================================
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


# ============================================================================
# Core Mobility Models
# ============================================================================

class Dataset(models.Model):
    """
    Master table for managing different mobility datasets.
    Allows system to handle multiple data sources.
    """
    
    DATASET_TYPE_CHOICES = [
        ('gps_trace', 'GPS Trace Data'),
        ('od_matrix', 'Origin-Destination Matrix'),
        ('trajectory', 'Aggregated Trajectories'),
        ('stop_event', 'Stop Events'),
        ('custom', 'Custom Dataset'),
    ]
    
    DATA_FORMAT_CHOICES = [
        ('csv', 'CSV File'),
        ('txt', 'Text File'),
        ('json', 'JSON File'),
        ('geojson', 'GeoJSON File'),
        ('shapefile', 'Shapefile'),
        ('api', 'API Endpoint'),
    ]
    
    # Identity
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique dataset name"
    )
    description = models.TextField(
        blank=True,
        help_text="Dataset description and context"
    )
    
    # Dataset configuration
    dataset_type = models.CharField(
        max_length=50,
        choices=DATASET_TYPE_CHOICES,
        help_text="Type of mobility data"
    )
    data_format = models.CharField(
        max_length=50,
        choices=DATA_FORMAT_CHOICES,
        help_text="Source data format"
    )
    
    # Field mapping configuration (JSON)
    field_mapping = models.JSONField(
        default=dict,
        help_text="Maps source fields to standard schema"
    )
    
    # Metadata
    source_url = models.URLField(
        blank=True,
        null=True,
        help_text="Original data source URL"
    )
    geographic_scope = models.CharField(
        max_length=255,
        blank=True,
        help_text="Geographic coverage (e.g., 'Beijing, China')"
    )
    temporal_range_start = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Start of temporal coverage"
    )
    temporal_range_end = models.DateTimeField(
        blank=True,
        null=True,
        help_text="End of temporal coverage"
    )
    
    # System fields
    is_active = models.BooleanField(
        default=True,
        help_text="Dataset is available for queries"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mobility_dataset'
        verbose_name = "Mobility Dataset"
        verbose_name_plural = "Mobility Datasets"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.dataset_type})"


class GPSPoint(gis_models.Model):
    """
    Generic GPS point model for all trace datasets.
    Replaces dataset-specific point models.
    """
    
    # Dataset reference
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name='gps_points',
        db_index=True,
        help_text="Parent dataset"
    )
    
    # Core identification
    entity_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Entity identifier (vehicle, person, device)"
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="Recording timestamp"
    )
    
    # Spatial data
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude (WGS84)"
    )
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude (WGS84)"
    )
    geom = gis_models.PointField(
        srid=4326,
        spatial_index=True,
        null=True,
        blank=True,
        help_text="PostGIS geometry (auto-generated)"
    )
    
    # Optional attributes
    altitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Altitude in meters"
    )
    accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text="GPS accuracy in meters"
    )
    speed = models.FloatField(
        null=True,
        blank=True,
        help_text="Instantaneous speed (km/h)"
    )
    heading = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(360)],
        help_text="Direction of travel (degrees)"
    )
    
    # Extended attributes (JSON for flexibility)
    extra_attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional dataset-specific attributes"
    )
    
    # Quality control
    is_valid = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Point passed validation"
    )
    validation_flags = models.JSONField(
        default=dict,
        blank=True,
        help_text="Validation issues (if any)"
    )
    
    # System fields
    imported_at = models.DateTimeField(
        default=timezone.now,
        help_text="Import timestamp"
    )
    
    class Meta:
        db_table = 'mobility_gpspoint'
        verbose_name = "GPS Point"
        verbose_name_plural = "GPS Points"
        ordering = ['dataset', 'entity_id', 'timestamp']
        indexes = [
            models.Index(fields=['dataset', 'entity_id', 'timestamp'], name='idx_gps_dataset_entity_time'),
            models.Index(fields=['dataset', 'timestamp'], name='idx_gps_dataset_time'),
            models.Index(fields=['entity_id', 'timestamp'], name='idx_gps_entity_time'),
        ]
        # Prevent duplicate points
        unique_together = [['dataset', 'entity_id', 'timestamp']]
    
    def __str__(self):
        return f"{self.entity_id} @ {self.timestamp}"
    
    def save(self, *args, **kwargs):
        """Auto-generate geometry from coordinates if not provided."""
        if not self.geom and self.longitude and self.latitude:
            from django.contrib.gis.geos import Point
            self.geom = Point(self.longitude, self.latitude, srid=4326)
        super().save(*args, **kwargs)


class Trajectory(gis_models.Model):
    """
    Aggregated trajectory for a single entity over a time period.
    Can represent daily trips, complete journeys, etc.
    """
    
    # Dataset reference
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name='trajectories',
        db_index=True
    )
    
    # Identity
    entity_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Entity identifier"
    )
    trajectory_date = models.DateField(
        db_index=True,
        help_text="Date of trajectory"
    )
    
    # Temporal bounds
    start_time = models.DateTimeField(help_text="Trajectory start")
    end_time = models.DateTimeField(help_text="Trajectory end")
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total duration"
    )
    
    # Statistics
    point_count = models.IntegerField(help_text="Number of GPS points")
    total_distance_meters = models.FloatField(
        null=True,
        blank=True,
        help_text="Total distance traveled"
    )
    avg_speed_kmh = models.FloatField(
        null=True,
        blank=True,
        help_text="Average speed"
    )
    max_speed_kmh = models.FloatField(
        null=True,
        blank=True,
        help_text="Maximum speed"
    )
    
    # Geometry
    geom = gis_models.LineStringField(
        srid=4326,
        spatial_index=True,
        null=True,
        blank=True,
        help_text="Full trajectory line"
    )
    bbox = gis_models.PolygonField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Bounding box"
    )
    
    # Extended metrics (JSON for flexibility)
    metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional computed metrics"
    )
    
    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mobility_trajectory'
        verbose_name = "Trajectory"
        verbose_name_plural = "Trajectories"
        ordering = ['dataset', 'entity_id', 'trajectory_date']
        unique_together = [['dataset', 'entity_id', 'trajectory_date']]
        indexes = [
            models.Index(fields=['dataset', 'entity_id'], name='idx_traj_dataset_entity'),
            models.Index(fields=['dataset', 'trajectory_date'], name='idx_traj_dataset_date'),
        ]
    
    def __str__(self):
        return f"{self.entity_id} - {self.trajectory_date}"


# ============================================================================
# Import Management Models
# ============================================================================

class ImportJob(models.Model):
    """
    Tracks data import operations for any dataset type.
    """
    
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Identity
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name='import_jobs',
        help_text="Target dataset"
    )
    
    # Source information
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('file', 'File Upload'),
            ('directory', 'Directory Scan'),
            ('url', 'URL Download'),
            ('api', 'API Import'),
        ],
        help_text="Import source type"
    )
    source_path = models.TextField(
        help_text="Path, URL, or identifier of source"
    )
    
    # Import configuration
    import_config = models.JSONField(
        default=dict,
        help_text="Import-specific settings"
    )
    
    # Progress tracking
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )
    total_records = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total records to process"
    )
    processed_records = models.IntegerField(
        default=0,
        help_text="Records processed so far"
    )
    successful_records = models.IntegerField(
        default=0,
        help_text="Successfully imported"
    )
    failed_records = models.IntegerField(
        default=0,
        help_text="Failed imports"
    )
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Processing start time"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Processing end time"
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Total processing time"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error details if failed"
    )
    
    class Meta:
        db_table = 'mobility_importjob'
        verbose_name = "Import Job"
        verbose_name_plural = "Import Jobs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Import {self.id} - {self.status}"
    
    @property
    def success_rate(self):
        """Calculate import success rate."""
        if self.processed_records == 0:
            return 0.0
        return round((self.successful_records / self.processed_records) * 100, 2)


class ValidationError(models.Model):
    """
    Records validation errors during import.
    """
    
    import_job = models.ForeignKey(
        ImportJob,
        on_delete=models.CASCADE,
        related_name='validation_errors'
    )
    
    # Error details
    record_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Line/record number in source"
    )
    raw_data = models.TextField(
        blank=True,
        help_text="Raw data that failed validation"
    )
    error_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Error category"
    )
    error_message = models.TextField(help_text="Detailed error message")
    
    # Context
    field_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Field that caused error"
    )
    expected_value = models.CharField(
        max_length=255,
        blank=True,
        help_text="Expected value format"
    )
    actual_value = models.CharField(
        max_length=255,
        blank=True,
        help_text="Actual value received"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mobility_validationerror'
        verbose_name = "Validation Error"
        verbose_name_plural = "Validation Errors"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['import_job', 'error_type'], name='idx_val_job_type'),
        ]
    
    def __str__(self):
        return f"{self.error_type} - Record {self.record_number}"


# ============================================================================
# Legacy Compatibility Models (Deprecated - To Be Migrated)
# ============================================================================

# TODO: Create data migration to move TDriveRawPoint -> GPSPoint
# TODO: Create data migration to move TDriveTrajectory -> Trajectory
# TODO: Remove these models after migration is complete

class TDriveRawPoint(gis_models.Model):
    """DEPRECATED: Use GPSPoint instead. Kept for migration only."""
    
    taxi_id = models.CharField(max_length=50, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    longitude = models.FloatField()
    latitude = models.FloatField()
    geom = gis_models.PointField(srid=4326, null=True, blank=True)
    imported_at = models.DateTimeField(default=timezone.now)
    source_file = models.CharField(max_length=255, null=True, blank=True)
    is_valid = models.BooleanField(default=True)
    validation_notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'mobility_tdriverawpoint'
        managed = False  # Don't create/modify during migrations


class TDriveTrajectory(gis_models.Model):
    """DEPRECATED: Use Trajectory instead. Kept for migration only."""
    
    taxi_id = models.CharField(max_length=50, db_index=True)
    trajectory_date = models.DateField(db_index=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    point_count = models.IntegerField()
    total_distance_meters = models.FloatField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    avg_speed_kmh = models.FloatField(null=True, blank=True)
    geom = gis_models.LineStringField(srid=4326, null=True, blank=True)
    bbox_geom = gis_models.PolygonField(srid=4326, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mobility_tdrivetrajectory'
        managed = False


class TDriveImportLog(models.Model):
    """DEPRECATED: Use ImportJob instead. Kept for migration only."""
    
    import_batch_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    file_name = models.CharField(max_length=255)
    file_path = models.TextField(null=True, blank=True)
    total_lines = models.IntegerField(null=True, blank=True)
    successful_imports = models.IntegerField(default=0)
    failed_imports = models.IntegerField(default=0)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=50, default='pending')
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'mobility_tdriveimportlog'
        managed = False


class TDriveValidationError(models.Model):
    """DEPRECATED: Use ValidationError instead. Kept for migration only."""
    
    import_log = models.ForeignKey(
        TDriveImportLog,
        on_delete=models.CASCADE,
        related_name='validation_errors'
    )
    line_number = models.IntegerField(null=True, blank=True)
    raw_line = models.TextField(null=True, blank=True)
    error_type = models.CharField(max_length=100)
    error_message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'mobility_tdrivevalidationerror'
        managed = False