"""
============================================================================
Test Cases for Data Import Functionality
============================================================================
File: server/tests/test_mobility/test_import.py
Description: Comprehensive tests for dataset import, validation, and processing
============================================================================
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.mobility.models import (
    Dataset,
    GPSPoint,
    Trajectory,
    ImportJob,
    ValidationError
)
from apps.mobility.services.generic_importer import (
    MobilityDataImporter,
    DataValidator,
    TDriveImporter
)


class DatasetModelTestCase(TestCase):
    """Test Dataset model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.dataset_data = {
            'name': 'Test Beijing Taxi Dataset',
            'description': 'Test dataset for unit testing',
            'dataset_type': 'gps_trace',
            'data_format': 'txt',
            'geographic_scope': 'Beijing, China',
            'field_mapping': {
                'entity_id': 'taxi_id',
                'timestamp': 'timestamp',
                'longitude': 'longitude',
                'latitude': 'latitude'
            }
        }
    
    def test_create_dataset(self):
        """Test creating a new dataset."""
        dataset = Dataset.objects.create(**self.dataset_data)
        
        self.assertIsNotNone(dataset.id)
        self.assertEqual(dataset.name, 'Test Beijing Taxi Dataset')
        self.assertEqual(dataset.dataset_type, 'gps_trace')
        self.assertTrue(dataset.is_active)
        self.assertIsNotNone(dataset.created_at)
    
    def test_dataset_unique_name(self):
        """Test that dataset names must be unique."""
        Dataset.objects.create(**self.dataset_data)
        
        with self.assertRaises(Exception):
            Dataset.objects.create(**self.dataset_data)
    
    def test_dataset_field_mapping(self):
        """Test JSON field mapping storage."""
        dataset = Dataset.objects.create(**self.dataset_data)
        
        self.assertEqual(
            dataset.field_mapping['entity_id'],
            'taxi_id'
        )
        self.assertIsInstance(dataset.field_mapping, dict)
    
    def test_dataset_string_representation(self):
        """Test dataset __str__ method."""
        dataset = Dataset.objects.create(**self.dataset_data)
        expected = f"{dataset.name} ({dataset.dataset_type})"
        
        self.assertEqual(str(dataset), expected)


class GPSPointModelTestCase(TestCase):
    """Test GPSPoint model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.dataset = Dataset.objects.create(
            name='Test Dataset',
            dataset_type='gps_trace',
            data_format='txt'
        )
        
        self.point_data = {
            'dataset': self.dataset,
            'entity_id': 'taxi_1',
            'timestamp': timezone.now(),
            'longitude': 116.40734,
            'latitude': 39.90469,
            'speed': 25.5,
            'heading': 90.0,
            'is_valid': True
        }
    
    def test_create_gps_point(self):
        """Test creating a GPS point."""
        point = GPSPoint.objects.create(**self.point_data)
        
        self.assertIsNotNone(point.id)
        self.assertEqual(point.entity_id, 'taxi_1')
        self.assertEqual(point.longitude, 116.40734)
        self.assertEqual(point.latitude, 39.90469)
    
    def test_auto_generate_geometry(self):
        """Test automatic geometry generation from coordinates."""
        point = GPSPoint.objects.create(**self.point_data)
        
        self.assertIsNotNone(point.geom)
        self.assertEqual(point.geom.x, 116.40734)
        self.assertEqual(point.geom.y, 39.90469)
        self.assertEqual(point.geom.srid, 4326)
    
    def test_coordinate_validation(self):
        """Test coordinate range validation."""
        # Invalid longitude
        invalid_data = self.point_data.copy()
        invalid_data['longitude'] = 190.0
        
        with self.assertRaises(Exception):
            point = GPSPoint(**invalid_data)
            point.full_clean()
    
    def test_unique_constraint(self):
        """Test unique constraint on dataset, entity_id, timestamp."""
        GPSPoint.objects.create(**self.point_data)
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            GPSPoint.objects.create(**self.point_data)
    
    def test_extra_attributes(self):
        """Test storing extra attributes in JSON field."""
        data = self.point_data.copy()
        data['extra_attributes'] = {
            'weather': 'sunny',
            'traffic': 'light'
        }
        
        point = GPSPoint.objects.create(**data)
        
        self.assertEqual(point.extra_attributes['weather'], 'sunny')
        self.assertIsInstance(point.extra_attributes, dict)


class DataValidatorTestCase(TestCase):
    """Test DataValidator functionality."""
    
    def setUp(self):
        """Set up validator."""
        self.validator = DataValidator({
            'strict_mode': False,
            'coordinate_bounds': [116.25, 39.80, 116.60, 40.05],
            'speed_threshold': 150
        })
    
    def test_validate_coordinates_valid(self):
        """Test validation of valid coordinates."""
        is_valid, errors = self.validator.validate_coordinates(
            116.40734, 39.90469
        )
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_coordinates_invalid_range(self):
        """Test validation of out-of-range coordinates."""
        is_valid, errors = self.validator.validate_coordinates(
            190.0, 39.90469
        )
        
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_validate_coordinates_outside_bounds(self):
        """Test validation against custom bounding box."""
        is_valid, errors = self.validator.validate_coordinates(
            120.0, 35.0  # Valid range but outside Beijing
        )
        
        self.assertFalse(is_valid)
        self.assertIn('outside allowed bounds', errors[0])
    
    def test_validate_timestamp_string(self):
        """Test timestamp parsing from string."""
        is_valid, parsed, error = self.validator.validate_timestamp(
            '2024-01-15 08:30:00'
        )
        
        self.assertTrue(is_valid)
        self.assertIsInstance(parsed, datetime)
        self.assertEqual(error, '')
    
    def test_validate_timestamp_datetime(self):
        """Test validation of datetime object."""
        now = datetime.now()
        is_valid, parsed, error = self.validator.validate_timestamp(now)
        
        self.assertTrue(is_valid)
        self.assertEqual(parsed, now)
    
    def test_validate_timestamp_invalid(self):
        """Test invalid timestamp handling."""
        is_valid, parsed, error = self.validator.validate_timestamp(
            'invalid-date'
        )
        
        self.assertFalse(is_valid)
        self.assertIsNone(parsed)
        self.assertNotEqual(error, '')
    
    def test_validate_speed(self):
        """Test speed validation."""
        # Valid speed
        is_valid, error = self.validator.validate_speed(50.0)
        self.assertTrue(is_valid)
        
        # Negative speed
        is_valid, error = self.validator.validate_speed(-10.0)
        self.assertFalse(is_valid)
        
        # Exceeds threshold
        is_valid, error = self.validator.validate_speed(200.0)
        self.assertFalse(is_valid)
    
    def test_validate_gps_point_complete(self):
        """Test complete GPS point validation."""
        data = {
            'entity_id': 'taxi_1',
            'timestamp': '2024-01-15 08:30:00',
            'longitude': 116.40734,
            'latitude': 39.90469,
            'speed': 25.5
        }
        
        is_valid, result = self.validator.validate_gps_point(data)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(result['errors']), 0)
        self.assertIn('longitude', result['parsed_data'])
        self.assertIn('latitude', result['parsed_data'])
        self.assertIn('timestamp', result['parsed_data'])


class MobilityDataImporterTestCase(TransactionTestCase):
    """Test MobilityDataImporter functionality."""
    
    def setUp(self):
        """Set up test dataset and importer."""
        self.dataset = Dataset.objects.create(
            name='Test Import Dataset',
            dataset_type='gps_trace',
            data_format='txt',
            field_mapping={
                'entity_id': 'taxi_id',
                'timestamp': 'timestamp',
                'longitude': 'longitude',
                'latitude': 'latitude'
            }
        )
        
        self.importer = MobilityDataImporter(self.dataset)
        self.importer.configure_validator({
            'strict_mode': False,
            'coordinate_bounds': [116.25, 39.80, 116.60, 40.05]
        })
    
    def test_create_import_job(self):
        """Test import job creation."""
        job = self.importer.create_import_job(
            source_type='file',
            source_path='/test/data.txt',
            config={'delimiter': ','}
        )
        
        self.assertIsNotNone(job.id)
        self.assertEqual(job.dataset, self.dataset)
        self.assertEqual(job.source_type, 'file')
        self.assertEqual(job.status, 'pending')
    
    def test_field_mapping_application(self):
        """Test field mapping transformation."""
        raw_data = {
            'taxi_id': '1',
            'datetime': '2024-01-15 08:30:00',
            'lon': 116.40734,
            'lat': 39.90469
        }
        
        field_mapping = {
            'entity_id': 'taxi_id',
            'timestamp': 'datetime',
            'longitude': 'lon',
            'latitude': 'lat'
        }
        
        mapped = self.importer._apply_field_mapping(raw_data, field_mapping)
        
        self.assertEqual(mapped['entity_id'], '1')
        self.assertEqual(mapped['longitude'], 116.40734)
        self.assertNotIn('taxi_id', mapped)
    
    def test_import_text_file(self):
        """Test importing text file (T-Drive format)."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False
        ) as f:
            f.write('1,2024-01-15 08:00:00,116.40734,39.90469\n')
            f.write('1,2024-01-15 08:05:00,116.41234,39.90569\n')
            f.write('2,2024-01-15 08:00:00,116.38734,39.92469\n')
            temp_path = f.name
        
        try:
            job = self.importer.import_text_file(temp_path)
            
            self.assertEqual(job.status, 'completed')
            self.assertEqual(job.successful_records, 3)
            self.assertEqual(job.failed_records, 0)
            
            # Verify points were created
            points = GPSPoint.objects.filter(dataset=self.dataset)
            self.assertEqual(points.count(), 3)
            
        finally:
            os.unlink(temp_path)
    
    def test_import_csv_with_mapping(self):
        """Test importing CSV with custom field mapping."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.csv',
            delete=False
        ) as f:
            f.write('bike_id,datetime,lon,lat,speed_kmh\n')
            f.write('100,2024-01-15 09:00:00,2.3522,48.8566,12.5\n')
            f.write('100,2024-01-15 09:05:00,2.3532,48.8576,14.2\n')
            temp_path = f.name
        
        # Update dataset for Paris
        self.dataset.field_mapping = {
            'entity_id': 'bike_id',
            'timestamp': 'datetime',
            'longitude': 'lon',
            'latitude': 'lat',
            'speed': 'speed_kmh'
        }
        self.dataset.save()
        
        # Configure validator for Paris bounds
        self.importer.configure_validator({
            'coordinate_bounds': [2.22, 48.81, 2.47, 48.90]
        })
        
        try:
            config = {
                'field_mapping': self.dataset.field_mapping,
                'delimiter': ',',
                'skip_header': True
            }
            
            job = self.importer.import_from_csv(temp_path, config)
            
            self.assertEqual(job.status, 'completed')
            self.assertEqual(job.successful_records, 2)
            
            # Verify points
            points = GPSPoint.objects.filter(
                dataset=self.dataset,
                entity_id='100'
            )
            self.assertEqual(points.count(), 2)
            self.assertEqual(points.first().speed, 12.5)
            
        finally:
            os.unlink(temp_path)
    
    def test_import_with_validation_errors(self):
        """Test import with validation errors."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False
        ) as f:
            # Valid point
            f.write('1,2024-01-15 08:00:00,116.40734,39.90469\n')
            # Invalid longitude
            f.write('2,2024-01-15 08:00:00,190.0,39.90469\n')
            # Invalid date
            f.write('3,invalid-date,116.40734,39.90469\n')
            temp_path = f.name
        
        try:
            job = self.importer.import_text_file(temp_path)
            
            self.assertEqual(job.successful_records, 1)
            self.assertEqual(job.failed_records, 2)
            
            # Check validation errors were logged
            errors = ValidationError.objects.filter(import_job=job)
            self.assertEqual(errors.count(), 2)
            
        finally:
            os.unlink(temp_path)
    
    def test_batch_processing(self):
        """Test batch processing of large files."""
        # Create file with more than batch_size records
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False
        ) as f:
            for i in range(1500):  # More than default batch_size
                f.write(f'1,2024-01-15 08:{i%60:02d}:00,116.40734,39.90469\n')
            temp_path = f.name
        
        try:
            job = self.importer.import_text_file(temp_path)
            
            self.assertEqual(job.successful_records, 1500)
            
            # Verify all points were created
            points = GPSPoint.objects.filter(dataset=self.dataset)
            self.assertEqual(points.count(), 1500)
            
        finally:
            os.unlink(temp_path)


class TDriveImporterTestCase(TransactionTestCase):
    """Test T-Drive specific importer."""
    
    def setUp(self):
        """Set up T-Drive dataset and importer."""
        self.dataset = Dataset.objects.create(
            name='T-Drive Test',
            dataset_type='gps_trace',
            data_format='txt'
        )
        
        self.importer = TDriveImporter(self.dataset)
    
    def test_beijing_bbox_validation(self):
        """Test Beijing bounding box validation."""
        # Point inside Beijing
        data = {
            'entity_id': '1',
            'timestamp': '2024-01-15 08:00:00',
            'longitude': 116.40734,
            'latitude': 39.90469
        }
        
        is_valid, result = self.importer.validator.validate_gps_point(data)
        self.assertTrue(is_valid)
        
        # Point outside Beijing
        data['longitude'] = 120.0
        data['latitude'] = 35.0
        
        is_valid, result = self.importer.validator.validate_gps_point(data)
        self.assertFalse(is_valid)
    
    def test_tdrive_file_format(self):
        """Test T-Drive specific file format."""
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False
        ) as f:
            # Standard T-Drive format
            f.write('1,2008-02-02 13:30:39,116.51172,39.92123\n')
            f.write('1,2008-02-02 13:35:39,116.51272,39.92223\n')
            temp_path = f.name
        
        try:
            job = self.importer.import_tdrive_file(temp_path)
            
            self.assertEqual(job.status, 'completed')
            self.assertEqual(job.successful_records, 2)
            
        finally:
            os.unlink(temp_path)


class ImportJobModelTestCase(TestCase):
    """Test ImportJob model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.dataset = Dataset.objects.create(
            name='Test Dataset',
            dataset_type='gps_trace',
            data_format='txt'
        )
    
    def test_create_import_job(self):
        """Test creating import job."""
        job = ImportJob.objects.create(
            dataset=self.dataset,
            source_type='file',
            source_path='/test/data.txt',
            total_records=100
        )
        
        self.assertIsNotNone(job.id)
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.processed_records, 0)
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        job = ImportJob.objects.create(
            dataset=self.dataset,
            source_type='file',
            source_path='/test/data.txt',
            total_records=100,
            processed_records=100,
            successful_records=95,
            failed_records=5
        )
        
        self.assertEqual(job.success_rate, 95.0)
    
    def test_success_rate_zero_processed(self):
        """Test success rate when no records processed."""
        job = ImportJob.objects.create(
            dataset=self.dataset,
            source_type='file',
            source_path='/test/data.txt'
        )
        
        self.assertEqual(job.success_rate, 0.0)


class ValidationErrorModelTestCase(TestCase):
    """Test ValidationError model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.dataset = Dataset.objects.create(
            name='Test Dataset',
            dataset_type='gps_trace',
            data_format='txt'
        )
        
        self.job = ImportJob.objects.create(
            dataset=self.dataset,
            source_type='file',
            source_path='/test/data.txt'
        )
    
    def test_create_validation_error(self):
        """Test creating validation error."""
        error = ValidationError.objects.create(
            import_job=self.job,
            record_number=42,
            error_type='COORDINATE_ERROR',
            error_message='Longitude out of range',
            field_name='longitude',
            expected_value='-180 to 180',
            actual_value='190.5'
        )
        
        self.assertIsNotNone(error.id)
        self.assertEqual(error.error_type, 'COORDINATE_ERROR')
        self.assertEqual(error.record_number, 42)
    
    def test_validation_error_relationship(self):
        """Test relationship with import job."""
        ValidationError.objects.create(
            import_job=self.job,
            error_type='TEST_ERROR',
            error_message='Test error'
        )
        
        ValidationError.objects.create(
            import_job=self.job,
            error_type='TEST_ERROR_2',
            error_message='Test error 2'
        )
        
        errors = self.job.validation_errors.all()
        self.assertEqual(errors.count(), 2)


class ImportIntegrationTestCase(TransactionTestCase):
    """Integration tests for complete import workflow."""
    
    def test_complete_import_workflow(self):
        """Test complete import from file to database."""
        # 1. Create dataset
        dataset = Dataset.objects.create(
            name='Integration Test Dataset',
            dataset_type='gps_trace',
            data_format='csv',
            field_mapping={
                'entity_id': 'vehicle_id',
                'timestamp': 'datetime',
                'longitude': 'lon',
                'latitude': 'lat'
            }
        )
        
        # 2. Create test CSV file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.csv',
            delete=False
        ) as f:
            f.write('vehicle_id,datetime,lon,lat\n')
            f.write('car_1,2024-01-15 08:00:00,116.40734,39.90469\n')
            f.write('car_1,2024-01-15 08:05:00,116.41234,39.90569\n')
            f.write('car_2,2024-01-15 08:00:00,116.38734,39.92469\n')
            temp_path = f.name
        
        try:
            # 3. Import data
            importer = MobilityDataImporter(dataset)
            importer.configure_validator({
                'coordinate_bounds': [116.25, 39.80, 116.60, 40.05]
            })
            
            config = {
                'field_mapping': dataset.field_mapping,
                'delimiter': ',',
                'skip_header': True
            }
            
            job = importer.import_from_csv(temp_path, config)
            
            # 4. Verify job completion
            self.assertEqual(job.status, 'completed')
            self.assertEqual(job.successful_records, 3)
            self.assertEqual(job.failed_records, 0)
            
            # 5. Verify data in database
            points = GPSPoint.objects.filter(dataset=dataset)
            self.assertEqual(points.count(), 3)
            
            # 6. Verify entity filtering
            car1_points = points.filter(entity_id='car_1')
            self.assertEqual(car1_points.count(), 2)
            
            # 7. Verify geometry creation
            point = points.first()
            self.assertIsNotNone(point.geom)
            self.assertEqual(point.geom.srid, 4326)
            
            # 8. Verify temporal ordering
            ordered_points = points.filter(
                entity_id='car_1'
            ).order_by('timestamp')
            self.assertEqual(ordered_points.count(), 2)
            
        finally:
            os.unlink(temp_path)
    
    def test_concurrent_imports(self):
        """Test handling of concurrent import operations."""
        dataset = Dataset.objects.create(
            name='Concurrent Test Dataset',
            dataset_type='gps_trace',
            data_format='txt'
        )
        
        # Create multiple import jobs
        jobs = []
        for i in range(3):
            job = ImportJob.objects.create(
                dataset=dataset,
                source_type='file',
                source_path=f'/test/file_{i}.txt',
                status='processing'
            )
            jobs.append(job)
        
        # Verify all jobs exist
        self.assertEqual(len(jobs), 3)
        
        # Verify they're all for the same dataset
        dataset_jobs = ImportJob.objects.filter(dataset=dataset)
        self.assertEqual(dataset_jobs.count(), 3)
    
    def test_error_recovery(self):
        """Test import recovery after errors."""
        dataset = Dataset.objects.create(
            name='Error Recovery Test',
            dataset_type='gps_trace',
            data_format='txt'
        )
        
        # Create file with mixed valid/invalid data
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False
        ) as f:
            f.write('1,2024-01-15 08:00:00,116.40734,39.90469\n')
            f.write('2,invalid-date,116.40734,39.90469\n')
            f.write('3,2024-01-15 08:00:00,999.0,39.90469\n')
            f.write('4,2024-01-15 08:00:00,116.40734,39.90469\n')
            temp_path = f.name
        
        try:
            importer = MobilityDataImporter(dataset)
            importer.configure_validator({
                'coordinate_bounds': [116.25, 39.80, 116.60, 40.05]
            })
            
            job = importer.import_text_file(temp_path)
            
            # Should import valid points despite errors
            self.assertEqual(job.successful_records, 2)
            self.assertEqual(job.failed_records, 2)
            
            # Verify error logging
            errors = ValidationError.objects.filter(import_job=job)
            self.assertEqual(errors.count(), 2)
            
            # Verify valid points were saved
            points = GPSPoint.objects.filter(dataset=dataset)
            self.assertEqual(points.count(), 2)
            
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    import django
    django.setup()
    
    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=2)
    runner.run_tests(['tests.test_mobility.test_import'])