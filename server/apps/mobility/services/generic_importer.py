"""
============================================================================
Generic Mobility Data Importer
============================================================================
Description: Flexible importer for various mobility data formats
Usage:
    # Text-based GPS traces (T-Drive style)
    importer = MobilityDataImporter(dataset)
    importer.import_gps_traces(file_path, config)
    
    # CSV with custom column mapping
    config = {
        'field_mapping': {
            'entity_id': 'vehicle_id',
            'timestamp': 'datetime',
            'longitude': 'lon',
            'latitude': 'lat'
        }
    }
    importer.import_from_csv(file_path, config)
============================================================================
"""

import os
import csv
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from apps.mobility.models import (
    Dataset,
    GPSPoint,
    ImportJob,
    ValidationError as ValidationErrorModel
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Validators
# ============================================================================

class DataValidator:
    """Validates GPS and mobility data against quality rules."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize validator with configuration.
        
        Args:
            config: Validation settings including:
                - strict_mode: Reject any invalid data
                - coordinate_bounds: Geographic bounds [min_lon, min_lat, max_lon, max_lat]
                - timestamp_range: Valid date range
                - speed_threshold: Maximum plausible speed (km/h)
        """
        self.config = config or {}
        self.strict_mode = self.config.get('strict_mode', False)
        self.coordinate_bounds = self.config.get('coordinate_bounds', None)
        self.speed_threshold = self.config.get('speed_threshold', 200)  # km/h
    
    def validate_coordinates(self, lon: float, lat: float) -> Tuple[bool, List[str]]:
        """
        Validate longitude and latitude.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Basic range check
        if not (-180 <= lon <= 180):
            errors.append(f"Longitude {lon} out of valid range [-180, 180]")
        if not (-90 <= lat <= 90):
            errors.append(f"Latitude {lat} out of valid range [-90, 90]")
        
        # Custom bounding box check
        if self.coordinate_bounds and len(errors) == 0:
            min_lon, min_lat, max_lon, max_lat = self.coordinate_bounds
            if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                errors.append(
                    f"Coordinates ({lon}, {lat}) outside allowed bounds"
                )
        
        return (len(errors) == 0, errors)
    
    def validate_timestamp(self, timestamp: Any) -> Tuple[bool, Optional[datetime], str]:
        """
        Validate and parse timestamp.
        
        Returns:
            (is_valid, parsed_datetime, error_message)
        """
        if isinstance(timestamp, datetime):
            return (True, timestamp, "")
        
        if isinstance(timestamp, str):
            # Try common datetime formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%d/%m/%Y %H:%M:%S',
                '%m/%d/%Y %H:%M:%S',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp, fmt)
                    return (True, dt, "")
                except ValueError:
                    continue
            
            return (False, None, f"Unable to parse timestamp: {timestamp}")
        
        return (False, None, f"Invalid timestamp type: {type(timestamp)}")
    
    def validate_speed(self, speed: Optional[float]) -> Tuple[bool, str]:
        """Validate speed value."""
        if speed is None:
            return (True, "")
        
        if speed < 0:
            return (False, f"Negative speed: {speed}")
        
        if speed > self.speed_threshold:
            return (False, f"Speed {speed} km/h exceeds threshold {self.speed_threshold}")
        
        return (True, "")
    
    def validate_gps_point(self, data: Dict) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a complete GPS point record.
        
        Returns:
            (is_valid, validation_result) where validation_result contains:
                - errors: List of error messages
                - warnings: List of warning messages
                - parsed_data: Cleaned/parsed data
        """
        result = {
            'errors': [],
            'warnings': [],
            'parsed_data': {}
        }
        
        # Validate coordinates
        lon = data.get('longitude')
        lat = data.get('latitude')
        
        if lon is None or lat is None:
            result['errors'].append("Missing longitude or latitude")
            return (False, result)
        
        try:
            lon = float(lon)
            lat = float(lat)
        except (ValueError, TypeError):
            result['errors'].append(f"Invalid coordinate format: lon={lon}, lat={lat}")
            return (False, result)
        
        coord_valid, coord_errors = self.validate_coordinates(lon, lat)
        if not coord_valid:
            result['errors'].extend(coord_errors)
        
        result['parsed_data']['longitude'] = lon
        result['parsed_data']['latitude'] = lat
        
        # Validate timestamp
        timestamp = data.get('timestamp')
        ts_valid, parsed_ts, ts_error = self.validate_timestamp(timestamp)
        if not ts_valid:
            result['errors'].append(ts_error)
        else:
            result['parsed_data']['timestamp'] = parsed_ts
        
        # Validate optional fields
        if 'speed' in data and data['speed'] is not None:
            try:
                speed = float(data['speed'])
                speed_valid, speed_error = self.validate_speed(speed)
                if not speed_valid:
                    result['warnings'].append(speed_error)
                else:
                    result['parsed_data']['speed'] = speed
            except (ValueError, TypeError):
                result['warnings'].append(f"Invalid speed format: {data['speed']}")
        
        # Overall validity
        is_valid = len(result['errors']) == 0
        if self.strict_mode and len(result['warnings']) > 0:
            is_valid = False
            result['errors'].extend(result['warnings'])
        
        return (is_valid, result)


# ============================================================================
# Generic Data Importer
# ============================================================================

class MobilityDataImporter:
    """
    Generic importer for mobility datasets.
    Handles various file formats and field mappings.
    """
    
    def __init__(self, dataset: Dataset):
        """
        Initialize importer for a specific dataset.
        
        Args:
            dataset: Target Dataset instance
        """
        self.dataset = dataset
        self.validator = None
        self.import_job = None
        self.batch_size = 1000  # Bulk insert batch size
    
    def configure_validator(self, config: Dict) -> None:
        """Set up data validator with custom rules."""
        self.validator = DataValidator(config)
    
    def create_import_job(
        self,
        source_type: str,
        source_path: str,
        config: Optional[Dict] = None
    ) -> ImportJob:
        """
        Create and return a new ImportJob.
        
        Args:
            source_type: Type of import source ('file', 'directory', etc.)
            source_path: Path to data source
            config: Import configuration
        
        Returns:
            Created ImportJob instance
        """
        self.import_job = ImportJob.objects.create(
            dataset=self.dataset,
            source_type=source_type,
            source_path=source_path,
            import_config=config or {},
            status=ImportJob.STATUS_PENDING
        )
        return self.import_job
    
    def log_validation_error(
        self,
        record_number: int,
        error_type: str,
        error_message: str,
        raw_data: Optional[str] = None,
        field_name: Optional[str] = None
    ) -> None:
        """Log a validation error to the database."""
        if not self.import_job:
            return
        
        ValidationErrorModel.objects.create(
            import_job=self.import_job,
            record_number=record_number,
            raw_data=raw_data or "",
            error_type=error_type,
            error_message=error_message,
            field_name=field_name or ""
        )
    
    def _apply_field_mapping(
        self,
        raw_data: Dict,
        field_mapping: Dict[str, str]
    ) -> Dict:
        """
        Apply field mapping to transform source fields to standard schema.
        
        Args:
            raw_data: Original data record
            field_mapping: Maps standard fields to source fields
                Example: {'entity_id': 'taxi_id', 'timestamp': 'datetime'}
        
        Returns:
            Transformed data with standard field names
        """
        mapped_data = {}
        
        for standard_field, source_field in field_mapping.items():
            if source_field in raw_data:
                mapped_data[standard_field] = raw_data[source_field]
        
        # Include extra fields not in mapping
        for key, value in raw_data.items():
            if key not in field_mapping.values() and key not in mapped_data:
                if 'extra_attributes' not in mapped_data:
                    mapped_data['extra_attributes'] = {}
                mapped_data['extra_attributes'][key] = value
        
        return mapped_data
    
    def import_from_csv(
        self,
        file_path: str,
        config: Optional[Dict] = None
    ) -> ImportJob:
        """
        Import GPS data from CSV file.
        
        Args:
            file_path: Path to CSV file
            config: Import configuration including:
                - field_mapping: Column name mapping
                - delimiter: CSV delimiter (default: ',')
                - skip_header: Skip first row (default: True)
                - validation: Validator configuration
        
        Returns:
            Completed ImportJob
        """
        config = config or {}
        field_mapping = config.get('field_mapping', {})
        delimiter = config.get('delimiter', ',')
        skip_header = config.get('skip_header', True)
        
        # Configure validator
        if 'validation' in config:
            self.configure_validator(config['validation'])
        else:
            self.configure_validator({})
        
        # Create import job
        job = self.create_import_job('file', file_path, config)
        job.status = ImportJob.STATUS_PROCESSING
        job.started_at = timezone.now()
        job.save()
        
        points_buffer = []
        record_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                if skip_header:
                    next(reader, None)
                
                for i, row in enumerate(reader, start=1):
                    record_count = i
                    
                    # Apply field mapping
                    if field_mapping:
                        mapped_data = self._apply_field_mapping(row, field_mapping)
                    else:
                        mapped_data = row
                    
                    # Validate
                    is_valid, validation_result = self.validator.validate_gps_point(mapped_data)
                    
                    if is_valid:
                        # Create GPS point
                        point = GPSPoint(
                            dataset=self.dataset,
                            entity_id=mapped_data.get('entity_id', 'unknown'),
                            timestamp=validation_result['parsed_data']['timestamp'],
                            longitude=validation_result['parsed_data']['longitude'],
                            latitude=validation_result['parsed_data']['latitude'],
                            speed=validation_result['parsed_data'].get('speed'),
                            extra_attributes=mapped_data.get('extra_attributes', {}),
                            is_valid=True
                        )
                        points_buffer.append(point)
                        job.successful_records += 1
                    else:
                        # Log validation error
                        self.log_validation_error(
                            record_number=i,
                            error_type='validation_failed',
                            error_message='; '.join(validation_result['errors']),
                            raw_data=str(row)
                        )
                        job.failed_records += 1
                    
                    job.processed_records += 1
                    
                    # Bulk insert
                    if len(points_buffer) >= self.batch_size:
                        GPSPoint.objects.bulk_create(points_buffer, batch_size=self.batch_size)
                        points_buffer = []
                        job.save()  # Update progress
                
                # Insert remaining
                if points_buffer:
                    GPSPoint.objects.bulk_create(points_buffer, batch_size=self.batch_size)
            
            # Complete job
            job.status = ImportJob.STATUS_COMPLETED
            job.total_records = record_count
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            job.status = ImportJob.STATUS_FAILED
            job.error_message = str(e)
        
        finally:
            job.completed_at = timezone.now()
            if job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                job.duration_seconds = duration
            job.save()
        
        return job
    
    def import_text_file(
        self,
        file_path: str,
        config: Optional[Dict] = None
    ) -> ImportJob:
        """
        Import GPS data from text file (T-Drive format).
        
        Expected format: entity_id, timestamp, longitude, latitude
        Example: 1, 2008-02-02 13:30:39, 116.51172, 39.92123
        
        Args:
            file_path: Path to text file
            config: Import configuration
        
        Returns:
            Completed ImportJob
        """
        config = config or {}
        delimiter = config.get('delimiter', ',')
        
        # Configure validator
        if 'validation' in config:
            self.configure_validator(config['validation'])
        else:
            self.configure_validator({})
        
        # Create import job
        job = self.create_import_job('file', file_path, config)
        job.status = ImportJob.STATUS_PROCESSING
        job.started_at = timezone.now()
        job.save()
        
        points_buffer = []
        record_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, start=1):
                    record_count = i
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    try:
                        parts = [p.strip() for p in line.split(delimiter)]
                        
                        if len(parts) < 4:
                            self.log_validation_error(
                                record_number=i,
                                error_type='parsing_error',
                                error_message=f'Expected at least 4 fields, got {len(parts)}',
                                raw_data=line
                            )
                            job.failed_records += 1
                            continue
                        
                        # Parse data
                        data = {
                            'entity_id': parts[0],
                            'timestamp': parts[1],
                            'longitude': parts[2],
                            'latitude': parts[3],
                        }
                        
                        # Validate
                        is_valid, validation_result = self.validator.validate_gps_point(data)
                        
                        if is_valid:
                            point = GPSPoint(
                                dataset=self.dataset,
                                entity_id=data['entity_id'],
                                timestamp=validation_result['parsed_data']['timestamp'],
                                longitude=validation_result['parsed_data']['longitude'],
                                latitude=validation_result['parsed_data']['latitude'],
                                is_valid=True
                            )
                            points_buffer.append(point)
                            job.successful_records += 1
                        else:
                            self.log_validation_error(
                                record_number=i,
                                error_type='validation_failed',
                                error_message='; '.join(validation_result['errors']),
                                raw_data=line
                            )
                            job.failed_records += 1
                        
                    except Exception as e:
                        self.log_validation_error(
                            record_number=i,
                            error_type='parsing_error',
                            error_message=str(e),
                            raw_data=line
                        )
                        job.failed_records += 1
                    
                    job.processed_records += 1
                    
                    # Bulk insert
                    if len(points_buffer) >= self.batch_size:
                        GPSPoint.objects.bulk_create(points_buffer, batch_size=self.batch_size)
                        points_buffer = []
                        job.save()
            
            # Insert remaining
            if points_buffer:
                GPSPoint.objects.bulk_create(points_buffer, batch_size=self.batch_size)
            
            job.status = ImportJob.STATUS_COMPLETED
            job.total_records = record_count
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            job.status = ImportJob.STATUS_FAILED
            job.error_message = str(e)
        
        finally:
            job.completed_at = timezone.now()
            if job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                job.duration_seconds = duration
            job.save()
        
        return job
    
    def import_directory(
        self,
        directory_path: str,
        config: Optional[Dict] = None
    ) -> List[ImportJob]:
        """
        Import all compatible files from a directory.
        
        Args:
            directory_path: Path to directory
            config: Import configuration with optional:
                - file_pattern: Glob pattern for files (default: '*.txt')
                - max_files: Maximum files to process
                - recursive: Search subdirectories
        
        Returns:
            List of ImportJob instances
        """
        config = config or {}
        file_pattern = config.get('file_pattern', '*.txt')
        max_files = config.get('max_files')
        recursive = config.get('recursive', False)
        
        # TODO: Implement directory scanning and batch import
        # - Use pathlib.Path.glob() for file discovery
        # - Process files in parallel using threading/multiprocessing
        # - Track overall progress across all files
        
        raise NotImplementedError("Directory import not yet implemented")
    
    def import_from_api(
        self,
        api_config: Dict
    ) -> ImportJob:
        """
        Import data from external API.
        
        Args:
            api_config: API configuration including:
                - endpoint: API URL
                - method: HTTP method
                - headers: Request headers
                - params: Query parameters
                - auth: Authentication credentials
                - pagination: Pagination strategy
        
        Returns:
            ImportJob instance
        """
        # TODO: Implement API import
        # - Support common API patterns (REST, GraphQL)
        # - Handle pagination automatically
        # - Implement rate limiting
        # - Support authentication methods (API key, OAuth, etc.)
        
        raise NotImplementedError("API import not yet implemented")


# ============================================================================
# Format-Specific Importers
# ============================================================================

class TDriveImporter(MobilityDataImporter):
    """
    Specialized importer for T-Drive dataset format.
    Maintains backward compatibility.
    """
    
    def __init__(self, dataset: Dataset):
        super().__init__(dataset)
        
        # T-Drive specific validation
        beijing_bounds = [116.25, 39.80, 116.60, 40.05]
        self.configure_validator({
            'coordinate_bounds': beijing_bounds,
            'strict_mode': False,
            'speed_threshold': 150
        })
    
    def import_tdrive_file(self, file_path: str) -> ImportJob:
        """Import single T-Drive format file."""
        return self.import_text_file(file_path)


# TODO: Add more specialized importers
# class GeoJSONImporter(MobilityDataImporter): ...
# class ShapefileImporter(MobilityDataImporter): ...
# class GPXImporter(MobilityDataImporter): ...