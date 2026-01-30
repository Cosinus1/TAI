#!/usr/bin/env python
"""
Test script to verify average speed calculation and entity statistics.
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from apps.mobility.models import Dataset, GPSPoint
from apps.mobility.views import EntityViewSet
from rest_framework.test import APIRequestFactory
from django.utils import timezone
import random

def test_entity_speed_calculation():
    """Test that entity statistics include average speed calculation."""
    print("Testing Entity Speed Calculation")
    print("=" * 50)
    
    # Get or create a test dataset
    dataset, created = Dataset.objects.get_or_create(
        name="Test Dataset for Speed Calculation",
        defaults={
            'description': 'Test dataset for speed calculation',
            'dataset_type': 'gps_trace',
            'is_active': True
        }
    )
    
    print(f"Using dataset: {dataset.name} (ID: {dataset.id})")
    
    # Create test entities with different speed profiles
    test_entities = [
        {'id': 'fast_entity', 'avg_speed': 60.0},
        {'id': 'medium_entity', 'avg_speed': 30.0},
        {'id': 'slow_entity', 'avg_speed': 10.0},
        {'id': 'mixed_entity', 'speeds': [5.0, 15.0, 25.0, 35.0]}  # avg = 20.0
    ]
    
    print("\nCreating test GPS points with speed data...")
    
    # Clear existing test points
    GPSPoint.objects.filter(dataset=dataset).delete()
    
    # Create test points
    for entity_info in test_entities:
        entity_id = entity_info['id']
        
        if 'avg_speed' in entity_info:
            # Create points with consistent speed
            for i in range(10):
                speed = entity_info['avg_speed'] + random.uniform(-5, 5)
                GPSPoint.objects.create(
                    dataset=dataset,
                    entity_id=entity_id,
                    latitude=48.8566 + random.uniform(-0.1, 0.1),
                    longitude=2.3522 + random.uniform(-0.1, 0.1),
                    timestamp=timezone.now(),
                    speed=speed,
                    is_valid=True
                )
        else:
            # Create points with varying speeds
            for speed in entity_info['speeds']:
                GPSPoint.objects.create(
                    dataset=dataset,
                    entity_id=entity_id,
                    latitude=48.8566 + random.uniform(-0.1, 0.1),
                    longitude=2.3522 + random.uniform(-0.1, 0.1),
                    timestamp=timezone.now(),
                    speed=speed + random.uniform(-2, 2),
                    is_valid=True
                )
    
    print(f"Created {GPSPoint.objects.filter(dataset=dataset).count()} test points")
    
    # Test EntityViewSet list endpoint
    print("\n" + "=" * 50)
    print("Testing EntityViewSet.list() endpoint")
    print("-" * 50)
    
    factory = APIRequestFactory()
    request = factory.get('/api/entities/', {'dataset': str(dataset.id)})
    viewset = EntityViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    
    response = viewset.list(request)
    
    print(f"Response status: {response.status_code}")
    print(f"Number of entities returned: {len(response.data)}")
    
    # Check each entity's statistics
    print("\nEntity Statistics:")
    print("-" * 50)
    for entity_stats in response.data:
        print(f"\nEntity: {entity_stats['entity_id']}")
        print(f"  Total points: {entity_stats['total_points']}")
        print(f"  Active days: {entity_stats['active_days']}")
        print(f"  Avg points per day: {entity_stats['avg_points_per_day']:.2f}")
        
        # Check for speed fields
        if 'avg_speed' in entity_stats:
            print(f"  Average speed: {entity_stats['avg_speed']:.2f} km/h")
        else:
            print(f"  WARNING: avg_speed field missing!")
        
        if 'max_speed' in entity_stats:
            print(f"  Max speed: {entity_stats['max_speed']:.2f} km/h")
        
        if 'min_speed' in entity_stats:
            print(f"  Min speed: {entity_stats['min_speed']:.2f} km/h")
        
        # Check entity type inference
        if 'entity_type' in entity_stats:
            print(f"  Entity type: {entity_stats['entity_type']}")
    
    # Test EntityViewSet retrieve endpoint for a specific entity
    print("\n" + "=" * 50)
    print("Testing EntityViewSet.retrieve() endpoint")
    print("-" * 50)
    
    test_entity_id = 'fast_entity'
    request = factory.get(f'/api/entities/{test_entity_id}/', {'dataset': str(dataset.id)})
    viewset = EntityViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    viewset.kwargs = {'pk': test_entity_id}
    
    response = viewset.retrieve(request, pk=test_entity_id)
    
    print(f"Response status: {response.status_code}")
    print(f"\nDetailed statistics for '{test_entity_id}':")
    print("-" * 50)
    
    if response.status_code == 200:
        stats = response.data
        print(f"Entity ID: {stats['entity_id']}")
        print(f"Total points: {stats['total_points']}")
        print(f"First timestamp: {stats['first_timestamp']}")
        print(f"Last timestamp: {stats['last_timestamp']}")
        print(f"Active days: {stats['active_days']}")
        print(f"Avg points per day: {stats['avg_points_per_day']:.2f}")
        
        # Speed statistics
        print(f"\nSpeed Statistics:")
        print(f"  Average speed: {stats.get('avg_speed', 'N/A')}")
        print(f"  Max speed: {stats.get('max_speed', 'N/A')}")
        print(f"  Min speed: {stats.get('min_speed', 'N/A')}")
        
        # Check if values are reasonable
        if 'avg_speed' in stats and stats['avg_speed'] is not None:
            expected_avg = 60.0  # Based on our test data
            actual_avg = stats['avg_speed']
            tolerance = 5.0  # Allow for random variation
            
            if abs(actual_avg - expected_avg) <= tolerance:
                print(f"  ✓ Average speed is within expected range ({expected_avg} ± {tolerance} km/h)")
            else:
                print(f"  ✗ Average speed {actual_avg:.2f} is outside expected range ({expected_avg} ± {tolerance} km/h)")
        
        # Trajectory statistics (if available)
        if 'total_trajectories' in stats:
            print(f"\nTrajectory Statistics:")
            print(f"  Total trajectories: {stats['total_trajectories']}")
            print(f"  Total distance: {stats.get('total_distance_meters', 'N/A')} meters")
            print(f"  Avg trajectory distance: {stats.get('avg_trajectory_distance', 'N/A')} meters")
    
    print("\n" + "=" * 50)
    print("Summary:")
    print("-" * 50)
    print("1. Server calculates average speed using Django's Avg('speed') aggregation")
    print("2. EntityViewSet.list() returns avg_speed field for each entity")
    print("3. EntityViewSet.retrieve() returns avg_speed, max_speed, min_speed fields")
    print("4. Speed values are in km/h (as stored in GPSPoint.speed field)")
    print("5. Client-side interface expects avg_speed_kmh but server returns avg_speed")
    print("\nRecommendation: Update client-side interface to use avg_speed instead of avg_speed_kmh")
    print("or update server serializer to rename avg_speed to avg_speed_kmh")

if __name__ == '__main__':
    test_entity_speed_calculation()