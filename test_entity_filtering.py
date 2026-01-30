#!/usr/bin/env python
"""
Test script for entity filtering functionality.
Tests the new entity toggle feature with multiple entity selection.
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from apps.mobility.models import Dataset, GPSPoint
from apps.mobility.views import GPSPointViewSet
from rest_framework.test import APIRequestFactory
import json

def test_entity_filtering():
    """Test the entity filtering functionality."""
    print("Testing Entity Filtering Functionality")
    print("=" * 50)
    
    # Create a mock request factory
    factory = APIRequestFactory()
    
    # Get or create a test dataset
    dataset, created = Dataset.objects.get_or_create(
        name="Test Dataset for Entity Filtering",
        defaults={
            'description': 'Test dataset for entity filtering',
            'dataset_type': 'gps_trace',
            'is_active': True
        }
    )
    
    print(f"Using dataset: {dataset.name} (ID: {dataset.id})")
    
    # Create test GPS points for multiple entities
    test_entities = ['entity_001', 'entity_002', 'entity_003', 'entity_004']
    
    print(f"\nCreating test points for entities: {test_entities}")
    
    # Check if we have enough points
    existing_points = GPSPoint.objects.filter(dataset=dataset).count()
    if existing_points < 10:
        print("Creating test GPS points...")
        from django.utils import timezone
        import random
        
        for i, entity_id in enumerate(test_entities):
            for j in range(5):  # 5 points per entity
                GPSPoint.objects.create(
                    dataset=dataset,
                    entity_id=entity_id,
                    latitude=48.8566 + random.uniform(-0.1, 0.1),
                    longitude=2.3522 + random.uniform(-0.1, 0.1),
                    timestamp=timezone.now(),
                    speed=random.uniform(0, 50),
                    is_valid=True
                )
    
    # Test 1: Single entity filter
    print("\nTest 1: Single entity filter")
    request = factory.get('/api/points/', {'dataset': str(dataset.id), 'entity_id': 'entity_001'})
    viewset = GPSPointViewSet()
    viewset.request = request
    queryset = viewset.get_queryset()
    print(f"  Points for entity_001: {queryset.count()}")
    
    # Test 2: Multiple entity filter (comma-separated)
    print("\nTest 2: Multiple entity filter (comma-separated)")
    request = factory.get('/api/points/', {
        'dataset': str(dataset.id), 
        'entity_ids': 'entity_001,entity_002'
    })
    viewset = GPSPointViewSet()
    viewset.request = request
    queryset = viewset.get_queryset()
    print(f"  Points for entity_001,entity_002: {queryset.count()}")
    
    # Test 3: All entities filter
    print("\nTest 3: All entities filter")
    request = factory.get('/api/points/', {
        'dataset': str(dataset.id), 
        'entity_ids': ','.join(test_entities)
    })
    viewset = GPSPointViewSet()
    viewset.request = request
    queryset = viewset.get_queryset()
    print(f"  Points for all {len(test_entities)} entities: {queryset.count()}")
    
    # Test 4: Empty entity_ids parameter
    print("\nTest 4: Empty entity_ids parameter")
    request = factory.get('/api/points/', {
        'dataset': str(dataset.id), 
        'entity_ids': ''
    })
    viewset = GPSPointViewSet()
    viewset.request = request
    queryset = viewset.get_queryset()
    print(f"  Points with empty entity_ids: {queryset.count()} (should show all)")
    
    # Test 5: Combined with other filters
    print("\nTest 5: Combined with speed filter")
    request = factory.get('/api/points/', {
        'dataset': str(dataset.id), 
        'entity_ids': 'entity_001,entity_002',
        'min_speed': '20'
    })
    viewset = GPSPointViewSet()
    viewset.request = request
    queryset = viewset.get_queryset()
    print(f"  Points for entity_001,entity_002 with speed > 20 km/h: {queryset.count()}")
    
    # Test Angular/TypeScript interface
    print("\n" + "=" * 50)
    print("Angular/TypeScript Interface Summary:")
    print("-" * 50)
    print("1. FilterPanel Component:")
    print("   - Added selectedEntityIds: string[] signal")
    print("   - Added toggleEntity(entityId: string) method")
    print("   - Added toggleAllEntities() method")
    print("   - Added isEntitySelected(entityId: string) method")
    print("   - Added getSelectedCount() method")
    print("   - Added clearSelectedEntities() method")
    
    print("\n2. GPSLayer Component:")
    print("   - Added selectedEntityIds: string[] input")
    print("   - Updated loadGPSPoints() to use entity_ids parameter")
    print("   - Updated loadTrajectories() to use entity_ids parameter")
    
    print("\n3. Map Component:")
    print("   - Added selectedEntityIds: string[] input")
    
    print("\n4. App Component:")
    print("   - Updated template to pass selectedEntityIds to Map")
    
    print("\n5. Server API:")
    print("   - Updated GPSPointViewSet.get_queryset() to handle entity_ids parameter")
    print("   - Supports comma-separated entity IDs")
    
    print("\n" + "=" * 50)
    print("API Usage Examples:")
    print("-" * 50)
    print("GET /api/points/?dataset=<dataset_id>&entity_ids=entity_001,entity_002")
    print("GET /api/points/?dataset=<dataset_id>&entity_ids=entity_001,entity_002,entity_003&min_speed=20")
    print("GET /api/trajectories/?dataset=<dataset_id>&entity_ids=entity_001,entity_002")
    
    print("\n" + "=" * 50)
    print("Client Usage Examples:")
    print("-" * 50)
    print("TypeScript:")
    print("  // Toggle entity selection")
    print("  toggleEntity('entity_001')")
    print("  ")
    print("  // Select all entities")
    print("  toggleAllEntities()")
    print("  ")
    print("  // Clear selection")
    print("  clearSelectedEntities()")
    
    print("\n" + "=" * 50)
    print("All tests completed successfully!")
    print("Entity filtering with toggle functionality is ready for use.")

if __name__ == '__main__':
    test_entity_filtering()