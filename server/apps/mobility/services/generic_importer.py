"""
============================================================================
Generic Mobility Data Importer - FIXED v2
============================================================================
Key fixes:
1. Fixed bulk_create to not use ignore_conflicts (doesn't return created objects)
2. Use get_or_create for each point individually
3. Better tracking of successful/failed insertions
============================================================================
"""

import os
import csv
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from django.contrib.gis.geos import Point
from django.db import transaction, IntegrityError
from django.utils import timezone

from apps.mobility.models import (
    Dataset,
    GPSPoint,
    ImportJob,
    ValidationError as ValidationErrorModel
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Validators (unchanged)
# ============================================================================

class DataValidator:
    """Validates GPS and mobility data against quality rules."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.strict_mode = self.config.get('strict_mode', False)
        self.coordinate_bounds = self.config.get('coordinate_bounds', None)
        self.speed_threshold = self.config.get('speed_threshold', 200)
    
    def validate_coordinates(self, lon: float, lat: float) -> Tuple[bool, List[str]]:
        errors = []
        
        if not (-180 <= lon <= 180):
            errors.append(f"Longitude {lon} out of valid range [-180, 180]")
        if not (-90 <= lat <= 90):
            errors.append(f"Latitude {lat} out of valid range [-90, 90]")
        
        if self.coordinate_bounds and len(errors) == 0:
            min_lon, min_lat, max_lon, max_lat = self.coordinate_bounds
            if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                errors.append(f"Coordinates ({lon}, {lat}) outside allowed bounds")
        
        return (len(errors) == 0, errors)
    
    def validate_timestamp(self, timestamp: Any) -> Tuple[bool, Optional[datetime], str]:
        if isinstance(timestamp, datetime):
            return (True, timestamp, "")
        
        if isinstance(timestamp, str):
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
        if speed is None:
            return (True, "")
        
        if speed < 0:
            return (False, f"Negative speed: {speed}")
        
        if speed > self.speed_threshold:
            return (False, f"Speed {speed} km/h exceeds threshold {self.speed_threshold}")
        
        return (True, "")
    
    def validate_gps_point(self, data: Dict) -> Tuple[bool, Dict[str, Any]]:
        result = {
            'errors': [],
            'warnings': [],
            'parsed_data': {}
        }
        
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
        
        timestamp = data.get('timestamp')
        ts_valid, parsed_ts, ts_error = self.validate_timestamp(timestamp)
        if not ts_valid:
            result['errors'].append(ts_error)
        else:
            result['parsed_data']['timestamp'] = parsed_ts
        
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
        
        is_valid = len(result['errors']) == 0
        if self.strict_mode and len(result['warnings']) > 0:
            is_valid = False
            result['errors'].extend(result['warnings'])
        
        return (is_valid, result)


# ============================================================================
# Generic Data Importer - FIXED
# ============================================================================

class MobilityDataImporter:
    """
    Generic importer for mobility datasets.
    """
    
    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self.validator = None
        self.import_job = None
        self.batch_size = 1000
    
    def configure_validator(self, config: Dict) -> None:
        """Set up data validator with custom rules."""
        self.validator = DataValidator(config)
    
    def create_import_job(
        self,
        source_type: str,
        source_path: str,
        config: Optional[Dict] = None
    ) -> ImportJob:
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
        mapped_data = {}
        
        for standard_field, source_field in field_mapping.items():
            if source_field in raw_data:
                mapped_data[standard_field] = raw_data[source_field]
        
        for key, value in raw_data.items():
            if key not in field_mapping.values() and key not in mapped_data:
                if 'extra_attributes' not in mapped_data:
                    mapped_data['extra_attributes'] = {}
                mapped_data['extra_attributes'][key] = value
        
        return mapped_data
    
    def _save_point(self, point_data: Dict) -> Tuple[bool, str]:
        """
        FIX: Save a single point using get_or_create to handle duplicates.
        
        Returns:
            (success, error_message)
        """
        try:
            # Use get_or_create to handle duplicates gracefully
            gps_point, created = GPSPoint.objects.get_or_create(
                dataset=self.dataset,
                entity_id=point_data['entity_id'],
                timestamp=point_data['timestamp'],
                defaults={
                    'longitude': point_data['longitude'],
                    'latitude': point_data['latitude'],
                    'speed': point_data.get('speed'),
                    'heading': point_data.get('heading'),
                    'altitude': point_data.get('altitude'),
                    'accuracy': point_data.get('accuracy'),
                    'extra_attributes': point_data.get('extra_attributes', {}),
                    'is_valid': point_data.get('is_valid', True),
                    'validation_flags': point_data.get('validation_flags', {})
                }
            )
            return (True, "")
        except Exception as e:
            return (False, str(e))
    
    def _bulk_save_points(self, points_data: List[Dict]) -> Tuple[int, int]:
        """
        FIX: Save points individually to handle duplicates properly.
        
        Returns:
            (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        
        for point_data in points_data:
            success, error = self._save_point(point_data)
            if success:
                successful += 1
            else:
                failed += 1
                logger.debug(f"Failed to save point: {error}")
        
        return successful, failed
    
    def import_from_csv(
        self,
        file_path: str,
        config: Optional[Dict] = None
    ) -> ImportJob:
        """Import GPS data from CSV file."""
        config = config or {}
        field_mapping = config.get('field_mapping', {})
        delimiter = config.get('delimiter', ',')
        skip_header = config.get('skip_header', True)
        
        if 'validation' in config:
            self.configure_validator(config['validation'])
        else:
            self.configure_validator({})
        
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
                    
                    if field_mapping:
                        mapped_data = self._apply_field_mapping(row, field_mapping)
                    else:
                        mapped_data = row
                    
                    is_valid, validation_result = self.validator.validate_gps_point(mapped_data)
                    
                    if is_valid:
                        point_data = {
                            'entity_id': mapped_data.get('entity_id', 'unknown'),
                            'timestamp': validation_result['parsed_data']['timestamp'],
                            'longitude': validation_result['parsed_data']['longitude'],
                            'latitude': validation_result['parsed_data']['latitude'],
                            'speed': validation_result['parsed_data'].get('speed'),
                            'extra_attributes': mapped_data.get('extra_attributes', {}),
                            'is_valid': True
                        }
                        points_buffer.append(point_data)
                    else:
                        self.log_validation_error(
                            record_number=i,
                            error_type='validation_failed',
                            error_message='; '.join(validation_result['errors']),
                            raw_data=str(row)
                        )
                        job.failed_records += 1
                    
                    job.processed_records += 1
                    
                    # Process batch
                    if len(points_buffer) >= self.batch_size:
                        successful, failed = self._bulk_save_points(points_buffer)
                        job.successful_records += successful
                        job.failed_records += failed
                        points_buffer = []
                        job.save()
                
                # Process remaining
                if points_buffer:
                    successful, failed = self._bulk_save_points(points_buffer)
                    job.successful_records += successful
                    job.failed_records += failed
            
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
        """Import GPS data from text file."""
        config = config or {}
        delimiter = config.get('delimiter', ',')
        
        if 'validation' in config:
            self.configure_validator(config['validation'])
        else:
            self.configure_validator({})
        
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
                        
                        data = {
                            'entity_id': parts[0],
                            'timestamp': parts[1],
                            'longitude': parts[2],
                            'latitude': parts[3],
                        }
                        
                        is_valid, validation_result = self.validator.validate_gps_point(data)
                        
                        if is_valid:
                            point_data = {
                                'entity_id': data['entity_id'],
                                'timestamp': validation_result['parsed_data']['timestamp'],
                                'longitude': validation_result['parsed_data']['longitude'],
                                'latitude': validation_result['parsed_data']['latitude'],
                                'is_valid': True
                            }
                            points_buffer.append(point_data)
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
                    
                    if len(points_buffer) >= self.batch_size:
                        successful, failed = self._bulk_save_points(points_buffer)
                        job.successful_records += successful
                        job.failed_records += failed
                        points_buffer = []
                        job.save()
            
            if points_buffer:
                successful, failed = self._bulk_save_points(points_buffer)
                job.successful_records += successful
                job.failed_records += failed
            
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


class TDriveImporter(MobilityDataImporter):
    """Specialized importer for T-Drive dataset format."""
    
    def __init__(self, dataset: Dataset):
        super().__init__(dataset)
        
        beijing_bounds = [116.25, 39.80, 116.60, 40.05]
        self.configure_validator({
            'coordinate_bounds': beijing_bounds,
            'strict_mode': False,
            'speed_threshold': 150
        })
    
    def import_tdrive_file(self, file_path: str) -> ImportJob:
        """Import single T-Drive format file."""
        return self.import_text_file(file_path)