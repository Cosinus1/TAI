"""
============================================================================
Trajectory Calculator Service
============================================================================
Calculates trajectories from GPS points at import time
============================================================================
"""

from django.db import transaction
from django.contrib.gis.geos import LineString
from datetime import timedelta
from typing import List, Dict
import logging

from apps.mobility.models import GPSPoint, Trajectory, Dataset

logger = logging.getLogger(__name__)


class TrajectoryCalculator:
    """
    Service for calculating trajectories from GPS points.
    Called automatically after data import.
    """
    
    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self.min_points = 5
        self.max_gap_minutes = 30
    
    def calculate_all_trajectories(self) -> Dict:
        """
        Calculate trajectories for all entities in the dataset.
        
        Returns:
            Statistics about trajectory calculation
        """
        stats = {
            'total_entities': 0,
            'total_trajectories': 0,
            'total_points_processed': 0,
            'errors': 0
        }
        
        entities = GPSPoint.objects.filter(
            dataset=self.dataset,
            is_valid=True
        ).values('entity_id').distinct()
        
        stats['total_entities'] = len(entities)
        
        for entity in entities:
            entity_id = entity['entity_id']
            try:
                entity_stats = self.calculate_entity_trajectories(entity_id)
                stats['total_trajectories'] += entity_stats['trajectories']
                stats['total_points_processed'] += entity_stats['points']
            except Exception as e:
                logger.error(f"Error calculating trajectories for {entity_id}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def calculate_entity_trajectories(self, entity_id: str) -> Dict:
        """
        Calculate trajectories for a single entity.
        Groups points by date and time gaps.
        """
        stats = {'trajectories': 0, 'points': 0}
        
        points = GPSPoint.objects.filter(
            dataset=self.dataset,
            entity_id=entity_id,
            is_valid=True
        ).order_by('timestamp')
        
        if len(points) < self.min_points:
            return stats
        
        daily_groups = self._group_by_date(points)
        
        for date, day_points in daily_groups.items():
            trajectories = self._split_by_time_gaps(day_points)
            
            for traj_points in trajectories:
                if len(traj_points) >= self.min_points:
                    self._create_trajectory(entity_id, date, traj_points)
                    stats['trajectories'] += 1
                    stats['points'] += len(traj_points)
        
        return stats
    
    def _group_by_date(self, points) -> Dict:
        """Group points by date."""
        groups = {}
        for point in points:
            date = point.timestamp.date()
            if date not in groups:
                groups[date] = []
            groups[date].append(point)
        return groups
    
    def _split_by_time_gaps(self, points: List) -> List[List]:
        """Split points into segments when time gaps exceed threshold."""
        if not points:
            return []
        
        segments = []
        current_segment = [points[0]]
        
        for i in range(1, len(points)):
            time_diff = (points[i].timestamp - points[i-1].timestamp).total_seconds() / 60
            
            if time_diff <= self.max_gap_minutes:
                current_segment.append(points[i])
            else:
                if len(current_segment) >= self.min_points:
                    segments.append(current_segment)
                current_segment = [points[i]]
        
        if len(current_segment) >= self.min_points:
            segments.append(current_segment)
        
        return segments
    
    @transaction.atomic
    def _create_trajectory(self, entity_id: str, date, points: List):
        """Create a trajectory record from points."""
        try:
            start_time = points[0].timestamp
            end_time = points[-1].timestamp
            duration = (end_time - start_time).total_seconds()
            
            coords = [(p.longitude, p.latitude) for p in points]
            geom = LineString(coords, srid=4326) if len(coords) >= 2 else None
            
            total_distance = 0
            speeds = []
            for i in range(1, len(points)):
                if points[i].geom and points[i-1].geom:
                    dist = points[i].geom.distance(points[i-1].geom) * 111000
                    total_distance += dist
                    
                    time_diff = (points[i].timestamp - points[i-1].timestamp).total_seconds()
                    if time_diff > 0:
                        speed_kmh = (dist / time_diff) * 3.6
                        speeds.append(speed_kmh)
            
            avg_speed = sum(speeds) / len(speeds) if speeds else None
            max_speed = max(speeds) if speeds else None
            
            Trajectory.objects.update_or_create(
                dataset=self.dataset,
                entity_id=entity_id,
                trajectory_date=date,
                defaults={
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_seconds': int(duration),
                    'point_count': len(points),
                    'total_distance_meters': total_distance,
                    'avg_speed_kmh': avg_speed,
                    'max_speed_kmh': max_speed,
                    'geom': geom,
                    'metrics': {
                        'min_speed_kmh': min(speeds) if speeds else None,
                        'median_speed_kmh': sorted(speeds)[len(speeds)//2] if speeds else None
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating trajectory: {e}")
            raise