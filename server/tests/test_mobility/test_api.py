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
        
        # DEBUG: Print created points
        print(f"\n{'='*70}")
        print(f"DEBUG: Created {GPSPoint.objects.count()} test points")
        for i, point in enumerate(GPSPoint.objects.all().order_by('timestamp')):
            print(f"  Point {i}: entity={point.entity_id}, time={point.timestamp}, speed={point.speed}")
        print(f"{'='*70}\n")
    
    def test_filter_points_by_time_range(self):
        """Test filtering points by time range."""
        base_time = timezone.now()
        start_time = (base_time + timedelta(minutes=3)).isoformat()
        end_time = (base_time + timedelta(minutes=7)).isoformat()
        
        # DEBUG: Print time range
        print(f"\n{'='*70}")
        print(f"DEBUG: Time range filter test")
        print(f"  Start time: {start_time}")
        print(f"  End time: {end_time}")
        
        # DEBUG: Check what should be included
        all_points = GPSPoint.objects.all().order_by('timestamp')
        print(f"\n  All points timestamps:")
        for i, point in enumerate(all_points):
            in_range = (base_time + timedelta(minutes=3)) <= point.timestamp <= (base_time + timedelta(minutes=7))
            print(f"    Point {i}: {point.timestamp} - In range: {in_range}")
        
        url = reverse('mobility:gpspoint-list')
        response = self.client.get(url, {
            'start_time': start_time,
            'end_time': end_time
        })
        
        # DEBUG: Print results
        print(f"\n  API Response:")
        print(f"    Status: {response.status_code}")
        print(f"    Count: {len(response.data['results'])}")
        print(f"    Expected: 5 (indices 3,4,5,6,7)")
        
        if len(response.data['results']) != 5:
            print(f"\n  ❌ MISMATCH! Got {len(response.data['results'])} instead of 5")
            print(f"    Returned points:")
            for i, point in enumerate(response.data['results']):
                print(f"      {i}: entity={point['entity_id']}, time={point['timestamp']}")
        print(f"{'='*70}\n")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
    
    def test_query_points_with_entity(self):
        """Test query with entity filter."""
        url = reverse('mobility:gpspoint-query')
        
        query_data = {
            'dataset': str(self.dataset.id),
            'entity_id': 'entity_1',
            'limit': 100
        }
        
        # DEBUG
        print(f"\n{'='*70}")
        print(f"DEBUG: Query with entity filter")
        print(f"  Entity: entity_1")
        
        # Check expected points
        expected_points = GPSPoint.objects.filter(entity_id='entity_1')
        print(f"  Expected points count: {expected_points.count()}")
        print(f"  Expected point indices: 1, 4, 7 (pattern: i % 3 == 1)")
        for point in expected_points:
            print(f"    - {point.entity_id} at {point.timestamp}")
        
        response = self.client.post(url, query_data, format='json')
        
        print(f"\n  API Response:")
        print(f"    Status: {response.status_code}")
        print(f"    Count: {response.data.get('count', 'N/A')}")
        
        if response.data.get('count') != 3:
            print(f"  ❌ MISMATCH! Got {response.data.get('count')} instead of 3")
        print(f"{'='*70}\n")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
    
    def test_get_points_by_entity(self):
        """Test getting all points for specific entity."""
        # DEBUG
        print(f"\n{'='*70}")
        print(f"DEBUG: Get points by entity")
        print(f"  Entity: entity_2")
        
        expected = GPSPoint.objects.filter(entity_id='entity_2')
        print(f"  Expected points: {expected.count()} (indices 2, 5, 8)")
        
        url = reverse('mobility:gpspoint-by-entity')
        response = self.client.get(url, {'entity_id': 'entity_2'})
        
        print(f"  API Response count: {len(response.data['results'])}")
        
        if len(response.data['results']) != 3:
            print(f"  ❌ MISMATCH! Got {len(response.data['results'])} instead of 3")
            print(f"  Returned entities:")
            for point in response.data['results']:
                print(f"    - {point['entity_id']}")
        print(f"{'='*70}\n")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)


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
    
    def test_get_entity_statistics(self):
        """Test getting statistics for specific entity."""
        # DEBUG
        print(f"\n{'='*70}")
        print(f"DEBUG: Entity statistics test")
        
        # Check what's in database
        from django.db.models import Avg
        db_stats = GPSPoint.objects.filter(
            entity_id='entity_1',
            is_valid=True
        ).aggregate(avg_speed=Avg('speed'))
        
        print(f"  Database stats for entity_1:")
        print(f"    avg_speed from DB: {db_stats['avg_speed']}")
        print(f"    Total points: {GPSPoint.objects.filter(entity_id='entity_1').count()}")
        
        url = reverse('mobility:entity-detail', args=['entity_1'])
        response = self.client.get(url, {'dataset': str(self.dataset.id)})
        
        print(f"\n  API Response:")
        print(f"    Status: {response.status_code}")
        print(f"    Keys in response: {list(response.data.keys())}")
        
        if 'avg_speed' not in response.data:
            print(f"  ❌ avg_speed NOT IN RESPONSE!")
            print(f"  Full response data: {json.dumps(response.data, indent=2, default=str)}")
        else:
            print(f"  ✅ avg_speed found: {response.data['avg_speed']}")
        print(f"{'='*70}\n")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['entity_id'], 'entity_1')
        self.assertEqual(response.data['total_points'], 10)
        self.assertIn('avg_speed', response.data)

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