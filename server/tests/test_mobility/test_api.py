"""
============================================================================
Test Cases for REST API Endpoints
============================================================================
File: server/tests/test_mobility/test_api.py
Description: Tests for dataset, GPS points, trajectories, and import APIs
============================================================================
"""

import json
import tempfile
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from apps.mobility.models import (
    Dataset,
    GPSPoint,
    Trajectory,
    ImportJob,
    ValidationError
)


class DatasetAPITestCase(APITestCase):
    """Test Dataset API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.dataset_data = {
            'name': 'Test API Dataset',
            'description': 'Dataset for API testing',
            'dataset_type': 'gps_trace',
            'data_format': 'csv',
            'geographic_scope': 'Test City',
            'field_mapping': {
                'entity_id': 'vehicle_id',
                'timestamp': 'datetime',
                'longitude': 'lon',
                'latitude': 'lat'
            }
        }
        
        self.dataset = Dataset.objects.create(**self.dataset_data)
    
    def test_list_datasets(self):
        """Test listing all datasets."""
        url = reverse('mobility:dataset-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_create_dataset(self):
        """Test creating a new dataset via API."""
        url = reverse('mobility:dataset-list')
        
        new_dataset = {
            'name': 'New API Dataset',
            'dataset_type': 'gps_trace',
            'data_format': 'txt',
            'field_mapping': {}
        }
        
        response = self.client.post(url, new_dataset, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New API Dataset')
        self.assertTrue(Dataset.objects.filter(
            name='New API Dataset'
        ).exists())
    
    def test_retrieve_dataset(self):
        """Test retrieving a specific dataset."""
        url = reverse('mobility:dataset-detail', args=[self.dataset.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.dataset.name)
        self.assertEqual(
            response.data['dataset_type'],
            self.dataset.dataset_type
        )
    
    def test_update_dataset(self):
        """Test updating a dataset."""
        url = reverse('mobility:dataset-detail', args=[self.dataset.id])
        
        update_data = {
            'name': self.dataset.name,
            'description': 'Updated description',
            'dataset_type': self.dataset.dataset_type,
            'data_format': self.dataset.data_format,
            'field_mapping': self.dataset.field_mapping
        }
        
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Updated description')
        
        # Verify in database
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.description, 'Updated description')
    
    def test_delete_dataset(self):
        """Test deleting a dataset."""
        url = reverse('mobility:dataset-detail', args=[self.dataset.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Dataset.objects.filter(
            id=self.dataset.id
        ).exists())
    
    def test_dataset_statistics(self):
        """Test dataset statistics endpoint."""
        # Add some points
        for i in range(5):
            GPSPoint.objects.create(
                dataset=self.dataset,
                entity_id='test_entity',
                timestamp=timezone.now() + timedelta(minutes=i),
                longitude=116.40734 + (i * 0.001),
                latitude=39.90469 + (i * 0.001),
                is_valid=True
            )
        
        url = reverse('mobility:dataset-statistics', args=[self.dataset.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_points'], 5)
        self.assertEqual(response.data['total_entities'], 1)
        self.assertIsNotNone(response.data['date_range'])
    
    def test_deactivate_dataset(self):
        """Test deactivating a dataset."""
        url = reverse('mobility:dataset-deactivate', args=[self.dataset.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.dataset.refresh_from_db()
        self.assertFalse(self.dataset.is_active)
    
    def test_activate_dataset(self):
        """Test activating a dataset."""
        self.dataset.is_active = False
        self.dataset.save()
        
        url = reverse('mobility:dataset-activate', args=[self.dataset.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.dataset.refresh_from_db()
        self.assertTrue(self.dataset.is_active)
    
    def test_filter_datasets_by_type(self):
        """Test filtering datasets by type."""
        # Create datasets of different types
        Dataset.objects.create(
            name='OD Dataset',
            dataset_type='od_matrix',
            data_format='csv'
        )
        
        url = reverse('mobility:dataset-list')
        response = self.client.get(url, {'type': 'gps_trace'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # All results should be gps_trace type
        for dataset in response.data['results']:
            self.assertEqual(dataset['dataset_type'], 'gps_trace')


class GPSPointAPITestCase(APITestCase):
    """Test GPS Point API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.dataset = Dataset.objects.create(
            name='GPS Point Test Dataset',
            dataset_type='gps_trace',
            data_format='txt'
        )
        
        # Create test points
        base_time = timezone.now()
        for i in range(10):
            GPSPoint.objects.create(
                dataset=self.dataset,
                entity_id=f'entity_{i % 3}',
                timestamp=base_time + timedelta(minutes=i),
                longitude=116.40734 + (i * 0.001),
                latitude=39.90469 + (i * 0.001),
                speed=25.0 + i,
                is_valid=True
            )
    
    def test_list_gps_points(self):
        """Test listing GPS points."""
        url = reverse('mobility:gpspoint-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
    
    def test_filter_points_by_dataset(self):
        """Test filtering points by dataset."""
        url = reverse('mobility:gpspoint-list')
        response = self.client.get(url, {'dataset': str(self.dataset.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        for point in response.data['results']:
            # In list view, we don't return full dataset object
            pass
    
    def test_filter_points_by_entity(self):
        """Test filtering points by entity_id."""
        url = reverse('mobility:gpspoint-list')
        response = self.client.get(url, {'entity_id': 'entity_0'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have points for entity_0 (indices 0, 3, 6, 9)
        self.assertEqual(len(response.data['results']), 4)
    
    def test_filter_points_by_time_range(self):
        """Test filtering points by time range."""
        base_time = timezone.now()
        start_time = (base_time + timedelta(minutes=3)).isoformat()
        end_time = (base_time + timedelta(minutes=7)).isoformat()
        
        url = reverse('mobility:gpspoint-list')
        response = self.client.get(url, {
            'start_time': start_time,
            'end_time': end_time
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have points 3, 4, 5, 6, 7 = 5 points
        self.assertEqual(len(response.data['results']), 5)
    
    def test_query_points_bbox(self):
        """Test spatial query with bounding box."""
        url = reverse('mobility:gpspoint-query')
        
        query_data = {
            'dataset': str(self.dataset.id),
            'min_lon': 116.407,
            'max_lon': 116.410,
            'min_lat': 39.904,
            'max_lat': 39.907,
            'limit': 100
        }
        
        response = self.client.post(url, query_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], 'FeatureCollection')
        self.assertIn('features', response.data)
        self.assertGreater(len(response.data['features']), 0)
    
    def test_query_points_with_entity(self):
        """Test query with entity filter."""
        url = reverse('mobility:gpspoint-query')
        
        query_data = {
            'dataset': str(self.dataset.id),
            'entity_id': 'entity_1',
            'limit': 100
        }
        
        response = self.client.post(url, query_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have points for entity_1 (indices 1, 4, 7)
        self.assertEqual(response.data['count'], 3)
    
    def test_get_points_by_entity(self):
        """Test getting all points for specific entity."""
        url = reverse('mobility:gpspoint-by-entity')
        response = self.client.get(url, {'entity_id': 'entity_2'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have points for entity_2 (indices 2, 5, 8)
        self.assertEqual(len(response.data['results']), 3)
    
    def test_create_gps_point(self):
        """Test creating a GPS point via API."""
        url = reverse('mobility:gpspoint-list')
        
        point_data = {
            'dataset': str(self.dataset.id),
            'entity_id': 'new_entity',
            'timestamp': timezone.now().isoformat(),
            'longitude': 116.41,
            'latitude': 39.91,
            'speed': 30.0
        }
        
        response = self.client.post(url, point_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(GPSPoint.objects.filter(
            entity_id='new_entity'
        ).exists())
    
    def test_pagination(self):
        """Test point listing pagination."""
        url = reverse('mobility:gpspoint-list')
        response = self.client.get(url, {'page_size': 5})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        self.assertIsNotNone(response.data.get('next'))


class TrajectoryAPITestCase(APITestCase):
    """Test Trajectory API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.dataset = Dataset.objects.create(
            name='Trajectory Test Dataset',
            dataset_type='trajectory',
            data_format='txt'
        )
        
        # Create test trajectories
        base_date = timezone.now().date()
        for i in range(5):
            Trajectory.objects.create(
                dataset=self.dataset,
                entity_id=f'entity_{i % 2}',
                trajectory_date=base_date + timedelta(days=i),
                start_time=timezone.now() + timedelta(days=i, hours=8),
                end_time=timezone.now() + timedelta(days=i, hours=10),
                duration_seconds=7200,
                point_count=100 + i * 10,
                total_distance_meters=5000 + i * 500,
                avg_speed_kmh=30.0 + i
            )
    
    def test_list_trajectories(self):
        """Test listing trajectories."""
        url = reverse('mobility:trajectory-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
    
    def test_filter_trajectories_by_entity(self):
        """Test filtering trajectories by entity."""
        url = reverse('mobility:trajectory-list')
        response = self.client.get(url, {'entity_id': 'entity_0'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have 3 trajectories (indices 0, 2, 4)
        self.assertEqual(len(response.data['results']), 3)
    
    def test_filter_trajectories_by_date(self):
        """Test filtering trajectories by specific date."""
        target_date = (timezone.now().date() + timedelta(days=2)).isoformat()
        
        url = reverse('mobility:trajectory-list')
        response = self.client.get(url, {'date': target_date})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_query_trajectories(self):
        """Test advanced trajectory query."""
        url = reverse('mobility:trajectory-query')
        
        query_data = {
            'dataset': str(self.dataset.id),
            'entity_id': 'entity_1',
            'min_distance': 5000,
            'max_distance': 6000
        }
        
        response = self.client.post(url, query_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_analyze_trajectory(self):
        """Test trajectory analysis endpoint."""
        trajectory = Trajectory.objects.first()
        
        url = reverse('mobility:trajectory-analyze', args=[trajectory.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['entity_id'], trajectory.entity_id)


class ImportJobAPITestCase(APITestCase):
    """Test Import Job API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.dataset = Dataset.objects.create(
            name='Import Test Dataset',
            dataset_type='gps_trace',
            data_format='csv',
            field_mapping={
                'entity_id': 'vehicle_id',
                'timestamp': 'datetime',
                'longitude': 'lon',
                'latitude': 'lat'
            }
        )
        
        self.import_job = ImportJob.objects.create(
            dataset=self.dataset,
            source_type='file',
            source_path='/test/data.csv',
            total_records=100,
            processed_records=50,
            successful_records=48,
            failed_records=2,
            status='processing'
        )
    
    def test_list_import_jobs(self):
        """Test listing import jobs."""
        url = reverse('mobility:importjob-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)
    
    def test_filter_imports_by_dataset(self):
        """Test filtering imports by dataset."""
        url = reverse('mobility:importjob-list')
        response = self.client.get(url, {'dataset': str(self.dataset.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_filter_imports_by_status(self):
        """Test filtering imports by status."""
        url = reverse('mobility:importjob-list')
        response = self.client.get(url, {'status': 'processing'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        for job in response.data['results']:
            self.assertEqual(job['status'], 'processing')
    
    def test_get_import_progress(self):
        """Test import progress endpoint."""
        url = reverse('mobility:importjob-progress', args=[self.import_job.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'processing')
        self.assertEqual(response.data['processed_records'], 50)
        self.assertEqual(response.data['progress_percentage'], 50.0)
    
    def test_start_import_csv(self):
        """Test starting a CSV import."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.csv',
            delete=False
        ) as f:
            f.write('vehicle_id,datetime,lon,lat\n')
            f.write('car_1,2024-01-15 08:00:00,116.40734,39.90469\n')
            f.write('car_1,2024-01-15 08:05:00,116.41234,39.90569\n')
            temp_path = f.name
        
        try:
            url = reverse('mobility:importjob-start-import')
            
            import_data = {
                'dataset_id': str(self.dataset.id),
                'source_type': 'file',
                'source_path': temp_path,
                'file_format': 'csv',
                'field_mapping': self.dataset.field_mapping,
                'delimiter': ',',
                'skip_header': True
            }
            
            response = self.client.post(url, import_data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('id', response.data)
            self.assertIn('status', response.data)
            
            # Verify job was created
            job_id = response.data['id']
            job = ImportJob.objects.get(id=job_id)
            self.assertEqual(job.dataset, self.dataset)
            
        finally:
            import os
            os.unlink(temp_path)


class EntityAPITestCase(APITestCase):
    """Test Entity statistics API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.dataset = Dataset.objects.create(
            name='Entity Test Dataset',
            dataset_type='gps_trace',
            data_format='txt'
        )
        
        # Create points for multiple entities
        base_time = timezone.now()
        
        # Entity 1: 10 points
        for i in range(10):
            GPSPoint.objects.create(
                dataset=self.dataset,
                entity_id='entity_1',
                timestamp=base_time + timedelta(hours=i),
                longitude=116.40734,
                latitude=39.90469,
                speed=25.0,
                is_valid=True
            )
        
        # Entity 2: 5 points
        for i in range(5):
            GPSPoint.objects.create(
                dataset=self.dataset,
                entity_id='entity_2',
                timestamp=base_time + timedelta(hours=i),
                longitude=116.41734,
                latitude=39.91469,
                speed=30.0,
                is_valid=True
            )
    
    def test_list_entities(self):
        """Test listing entities with statistics."""
        url = reverse('mobility:entity-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_filter_entities_by_dataset(self):
        """Test filtering entities by dataset."""
        url = reverse('mobility:entity-list')
        response = self.client.get(url, {'dataset': str(self.dataset.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_filter_entities_by_min_points(self):
        """Test filtering entities by minimum points."""
        url = reverse('mobility:entity-list')
        response = self.client.get(url, {'min_points': 8})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only entity_1 has 10 points
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['entity_id'], 'entity_1')
    
    def test_get_entity_statistics(self):
        """Test getting statistics for specific entity."""
        url = reverse('mobility:entity-detail', args=['entity_1'])
        response = self.client.get(url, {'dataset': str(self.dataset.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['entity_id'], 'entity_1')
        self.assertEqual(response.data['total_points'], 10)
        self.assertIn('avg_speed', response.data)
    
    def test_entity_not_found(self):
        """Test handling of non-existent entity."""
        url = reverse('mobility:entity-detail', args=['nonexistent'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class APIErrorHandlingTestCase(APITestCase):
    """Test API error handling."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
    
    def test_invalid_dataset_id(self):
        """Test handling of invalid dataset ID."""
        url = reverse('mobility:dataset-detail', args=['invalid-uuid'])
        response = self.client.get(url)
        
        # Should return 404 or 400
        self.assertIn(
            response.status_code,
            [status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST]
        )
    
    def test_missing_required_fields(self):
        """Test creating dataset without required fields."""
        url = reverse('mobility:dataset-list')
        
        incomplete_data = {
            'name': 'Incomplete Dataset'
            # Missing dataset_type, data_format
        }
        
        response = self.client.post(url, incomplete_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_invalid_coordinate_range(self):
        """Test creating point with invalid coordinates."""
        dataset = Dataset.objects.create(
            name='Test Dataset',
            dataset_type='gps_trace',
            data_format='txt'
        )
        
        url = reverse('mobility:gpspoint-list')
        
        invalid_point = {
            'dataset': str(dataset.id),
            'entity_id': 'test',
            'timestamp': timezone.now().isoformat(),
            'longitude': 190.0,  # Invalid
            'latitude': 39.90469
        }
        
        response = self.client.post(url, invalid_point, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_query_without_dataset(self):
        """Test query without specifying dataset."""
        url = reverse('mobility:gpspoint-query')
        
        query_data = {
            'min_lon': 116.0,
            'max_lon': 117.0,
            'min_lat': 39.0,
            'max_lat': 40.0
        }
        
        response = self.client.post(url, query_data, format='json')
        
        # Should work without dataset (queries all datasets)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


if __name__ == '__main__':
    import django
    django.setup()
    
    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=2)
    runner.run_tests(['tests.test_mobility.test_api'])