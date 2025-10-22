#!/usr/bin/env python
"""
Script to generate test data for the urban mobility analysis system.
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.mobility.models import GPSTrace, OriginDestination
from apps.poi.models import POI


def generate_gps_traces(num_users=10, traces_per_user=50):
    """
    Generate sample GPS traces for testing.
    
    Args:
        num_users: Number of users to generate data for
        traces_per_user: Number of GPS traces per user
    
    Returns:
        Number of traces created
    """
    created_count = 0
    
    # Paris area coordinates
    paris_center = (48.8566, 2.3522)
    radius_km = 10
    
    for user_id in range(1, num_users + 1):
        # Start from a random point in Paris
        base_lat = paris_center[0] + random.uniform(-0.1, 0.1)
        base_lon = paris_center[1] + random.uniform(-0.1, 0.1)
        
        current_time = datetime.now() - timedelta(days=7)
        
        for trace_num in range(traces_per_user):
            # Add some random movement
            lat = base_lat + random.uniform(-0.01, 0.01)
            lon = base_lon + random.uniform(-0.01, 0.01)
            
            # Move base point slightly for next trace
            base_lat += random.uniform(-0.001, 0.001)
            base_lon += random.uniform(-0.001, 0.001)
            
            # Generate trace data
            trace = GPSTrace(
                user_id=user_id,
                timestamp=current_time,
                latitude=lat,
                longitude=lon,
                altitude=random.uniform(30, 50),
                speed=random.uniform(0, 20),
                accuracy=random.uniform(5, 15)
            )
            trace.save()
            created_count += 1
            
            # Move time forward
            current_time += timedelta(minutes=random.randint(1, 10))
    
    return created_count


def generate_od_data(num_trips=100):
    """
    Generate sample Origin-Destination data.
    
    Args:
        num_trips: Number of OD trips to generate
    
    Returns:
        Number of OD records created
    """
    created_count = 0
    
    # Common locations in Paris
    locations = [
        (48.8566, 2.3522),  # Notre-Dame
        (48.8584, 2.2945),  # Eiffel Tower
        (48.8606, 2.3376),  # Louvre
        (48.8795, 2.3284),  # Montmartre
        (48.8462, 2.3371),  # Latin Quarter
        (48.8669, 2.3117),  # Champs-Élysées
        (48.8412, 2.3214),  # Saint-Germain
        (48.8329, 2.2876),  # Issy-les-Moulineaux
    ]
    
    transport_modes = ['walking', 'bicycle', 'metro', 'bus', 'car']
    
    for _ in range(num_trips):
        # Pick random origin and destination
        origin = random.choice(locations)
        destination = random.choice([loc for loc in locations if loc != origin])
        
        # Generate trip data
        start_time = datetime.now() - timedelta(days=random.randint(1, 30))
        duration = random.randint(600, 3600)  # 10-60 minutes
        
        od = OriginDestination(
            user_id=random.randint(1, 20),
            origin_latitude=origin[0],
            origin_longitude=origin[1],
            destination_latitude=destination[0],
            destination_longitude=destination[1],
            start_time=start_time,
            end_time=start_time + timedelta(seconds=duration),
            distance_meters=random.randint(500, 10000),
            duration_seconds=duration,
            transport_mode=random.choice(transport_modes)
        )
        od.save()
        created_count += 1
    
    return created_count


def generate_sample_pois():
    """
    Generate sample Points of Interest.
    
    Returns:
        Number of POIs created
    """
    sample_pois = [
        {
            'name': 'Eiffel Tower',
            'category': 'landmark',
            'latitude': 48.8584,
            'longitude': 2.2945,
            'address': 'Champ de Mars, 5 Avenue Anatole France, 75007 Paris'
        },
        {
            'name': 'Louvre Museum',
            'category': 'museum',
            'latitude': 48.8606,
            'longitude': 2.3376,
            'address': 'Rue de Rivoli, 75001 Paris'
        },
        {
            'name': 'Notre-Dame Cathedral',
            'category': 'religious',
            'latitude': 48.8530,
            'longitude': 2.3499,
            'address': '6 Parvis Notre-Dame - Pl. Jean-Paul II, 75004 Paris'
        },
        {
            'name': 'Café de Flore',
            'category': 'restaurant',
            'latitude': 48.8542,
            'longitude': 2.3327,
            'address': '172 Boulevard Saint-Germain, 75006 Paris'
        },
        {
            'name': 'Gare du Nord',
            'category': 'transport',
            'latitude': 48.8809,
            'longitude': 2.3553,
            'address': '18 Rue de Dunkerque, 75010 Paris'
        }
    ]
    
    created_count = 0
    for poi_data in sample_pois:
        poi = POI(**poi_data)
        poi.save()
        created_count += 1
    
    return created_count


def main():
    """Main function to generate test data."""
    print("Generating test data...")
    
    print("Generating GPS traces...")
    gps_count = generate_gps_traces()
    print(f"Created {gps_count} GPS traces")
    
    print("Generating OD data...")
    od_count = generate_od_data()
    print(f"Created {od_count} OD records")
    
    print("Generating sample POIs...")
    poi_count = generate_sample_pois()
    print(f"Created {poi_count} POIs")
    
    print("Test data generation completed!")


if __name__ == '__main__':
    main()
