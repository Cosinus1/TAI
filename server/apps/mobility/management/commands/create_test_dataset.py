#!/usr/bin/env python3
"""
============================================================================
Management Command: Create Test Dataset
============================================================================
Creates a test dataset with 20 entities (bus, bike, car) in Paris
Each entity has 50 GPS points
============================================================================
"""

import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.mobility.models import Dataset, GPSPoint


class Command(BaseCommand):
    help = 'Create a test dataset with Paris mobility data (20 entities, 50 points each)'

    # Paris bounding box
    PARIS_BOUNDS = {
        'min_lon': 2.25,
        'max_lon': 2.42,
        'min_lat': 48.82,
        'max_lat': 48.90
    }

    # Entity types with their characteristics
    ENTITY_TYPES = {
        'bus': {
            'count': 7,
            'prefix': 'bus',
            'speed_range': (15, 40),  # km/h
            'color': '#FF5722'  # Orange
        },
        'bike': {
            'count': 7,
            'prefix': 'bike',
            'speed_range': (8, 25),  # km/h
            'color': '#4CAF50'  # Green
        },
        'car': {
            'count': 6,
            'prefix': 'car',
            'speed_range': (20, 60),  # km/h
            'color': '#2196F3'  # Blue
        }
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of dataset if it exists',
        )
        parser.add_argument(
            '--points',
            type=int,
            default=50,
            help='Number of GPS points per entity (default: 50)',
        )

    def handle(self, *args, **options):
        force = options['force']
        points_per_entity = options['points']

        dataset_name = 'Paris Test Dataset'

        # Check if dataset already exists
        existing = Dataset.objects.filter(name=dataset_name).first()
        if existing:
            if force:
                self.stdout.write(f'Deleting existing dataset: {dataset_name}')
                existing.delete()
            else:
                self.stdout.write(
                    self.style.WARNING(f'Dataset "{dataset_name}" already exists. Use --force to recreate.')
                )
                return

        # Create the dataset
        self.stdout.write(f'Creating dataset: {dataset_name}')
        
        dataset = Dataset.objects.create(
            name=dataset_name,
            description='Test dataset with Paris mobility data: buses, bikes, and cars',
            dataset_type='gps_trace',
            data_format='json',
            geographic_scope='Paris, France',
            field_mapping={
                'entity_id': 'entity_id',
                'timestamp': 'timestamp',
                'longitude': 'longitude',
                'latitude': 'latitude',
                'entity_type': 'entity_type'
            },
            is_active=True
        )

        self.stdout.write(f'Dataset created with ID: {dataset.id}')

        # Generate GPS points for each entity type
        total_points = 0
        base_time = timezone.now() - timedelta(hours=2)

        for entity_type, config in self.ENTITY_TYPES.items():
            self.stdout.write(f'Generating {config["count"]} {entity_type}(s)...')
            
            for i in range(config['count']):
                entity_id = f'{config["prefix"]}_{i + 1:03d}'
                points = self._generate_trajectory(
                    dataset=dataset,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    num_points=points_per_entity,
                    base_time=base_time + timedelta(minutes=random.randint(0, 30)),
                    speed_range=config['speed_range']
                )
                total_points += len(points)
                
                # Bulk create points
                GPSPoint.objects.bulk_create(points, batch_size=100)

        # Update dataset temporal range
        dataset.temporal_range_start = base_time
        dataset.temporal_range_end = base_time + timedelta(hours=2)
        dataset.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {total_points} GPS points for 20 entities'
            )
        )
        self.stdout.write(f'Dataset ID: {dataset.id}')

    def _generate_trajectory(self, dataset, entity_id, entity_type, num_points, base_time, speed_range):
        """Generate a realistic trajectory within Paris bounds."""
        points = []
        
        # Random starting point within Paris
        current_lon = random.uniform(
            self.PARIS_BOUNDS['min_lon'] + 0.02,
            self.PARIS_BOUNDS['max_lon'] - 0.02
        )
        current_lat = random.uniform(
            self.PARIS_BOUNDS['min_lat'] + 0.01,
            self.PARIS_BOUNDS['max_lat'] - 0.01
        )
        
        # Random initial heading (direction in degrees)
        heading = random.uniform(0, 360)
        
        current_time = base_time
        
        for i in range(num_points):
            # Generate speed for this segment
            speed = random.uniform(speed_range[0], speed_range[1])
            
            # Time interval (30 seconds to 2 minutes)
            time_delta = timedelta(seconds=random.randint(30, 120))
            
            # Calculate movement (simplified: convert speed to coordinate change)
            # 1 degree latitude ≈ 111 km, 1 degree longitude ≈ 75 km at Paris latitude
            distance_km = (speed * time_delta.total_seconds()) / 3600
            
            # Add some randomness to heading
            heading += random.uniform(-30, 30)
            heading = heading % 360
            
            # Convert to coordinate changes
            import math
            lon_change = (distance_km / 75) * math.cos(math.radians(heading))
            lat_change = (distance_km / 111) * math.sin(math.radians(heading))
            
            # Update position
            new_lon = current_lon + lon_change
            new_lat = current_lat + lat_change
            
            # Keep within bounds (bounce off edges)
            if new_lon < self.PARIS_BOUNDS['min_lon'] or new_lon > self.PARIS_BOUNDS['max_lon']:
                heading = 180 - heading
                new_lon = max(self.PARIS_BOUNDS['min_lon'], min(new_lon, self.PARIS_BOUNDS['max_lon']))
            
            if new_lat < self.PARIS_BOUNDS['min_lat'] or new_lat > self.PARIS_BOUNDS['max_lat']:
                heading = -heading
                new_lat = max(self.PARIS_BOUNDS['min_lat'], min(new_lat, self.PARIS_BOUNDS['max_lat']))
            
            current_lon = new_lon
            current_lat = new_lat
            
            # Create GPS point
            point = GPSPoint(
                dataset=dataset,
                entity_id=entity_id,
                timestamp=current_time,
                longitude=round(current_lon, 6),
                latitude=round(current_lat, 6),
                speed=round(speed, 1),
                heading=round(heading % 360, 1),
                is_valid=True,
                extra_attributes={
                    'entity_type': entity_type
                }
            )
            points.append(point)
            
            current_time += time_delta
        
        return points