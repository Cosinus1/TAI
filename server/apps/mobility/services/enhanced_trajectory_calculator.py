"""
============================================================================
Enhanced Trajectory Calculator Service
============================================================================
Enhanced trajectory calculation with:
1. Road-following algorithm using map matching
2. Stop point detection between trajectories
3. Advanced speed and distance calculations
4. Trajectory segmentation and analysis
============================================================================
"""

from django.db import transaction
from django.contrib.gis.geos import LineString, Point
from datetime import timedelta
from typing import List, Dict, Tuple, Optional
import logging
import math
import numpy as np
from scipy.spatial import KDTree
from scipy.interpolate import interp1d

from apps.mobility.models import GPSPoint, Trajectory, Dataset
from .road_following import SimplifiedRoadFollower

logger = logging.getLogger(__name__)


class EnhancedTrajectoryCalculator:
    """
    Enhanced service for calculating trajectories from GPS points with:
    - Road-following map matching
    - Stop detection between trajectories
    - Advanced speed calculations
    - Trajectory segmentation
    """
    
    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self.min_points = 5
        self.max_gap_minutes = 30
        self.stop_detection_threshold_seconds = 300  # 5 minutes
        self.speed_threshold_kmh = 2.0  # Below this speed is considered stopped
        self.map_matching_enabled = False  # Will be enabled if OSMnx is available
        
        # Check for OSMnx availability for road-following
        try:
            import osmnx as ox
            self.map_matching_enabled = True
            logger.info("OSMnx available for road-following map matching")
        except ImportError:
            logger.warning("OSMnx not available, using simplified road-following")
    
    def calculate_enhanced_trajectories(self, entity_id: str = None) -> Dict:
        """
        Calculate enhanced trajectories for all entities or a specific entity.
        
        Args:
            entity_id: Optional specific entity ID
            
        Returns:
            Statistics about trajectory calculation
        """
        stats = {
            'total_entities': 0,
            'total_trajectories': 0,
            'total_points_processed': 0,
            'stop_points_detected': 0,
            'road_following_applied': 0,
            'errors': 0
        }
        
        if entity_id:
            entities = [{'entity_id': entity_id}]
        else:
            entities = GPSPoint.objects.filter(
                dataset=self.dataset,
                is_valid=True
            ).values('entity_id').distinct()
        
        stats['total_entities'] = len(entities)
        
        for entity in entities:
            entity_id = entity['entity_id']
            try:
                entity_stats = self.calculate_entity_enhanced_trajectories(entity_id)
                stats['total_trajectories'] += entity_stats['trajectories']
                stats['total_points_processed'] += entity_stats['points']
                stats['stop_points_detected'] += entity_stats['stop_points']
                stats['road_following_applied'] += entity_stats['road_following_applied']
            except Exception as e:
                logger.error(f"Error calculating enhanced trajectories for {entity_id}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def calculate_entity_enhanced_trajectories(self, entity_id: str) -> Dict:
        """
        Calculate enhanced trajectories for a single entity.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'trajectories': 0,
            'points': 0,
            'stop_points': 0,
            'road_following_applied': 0
        }
        
        points = GPSPoint.objects.filter(
            dataset=self.dataset,
            entity_id=entity_id,
            is_valid=True
        ).order_by('timestamp')
        
        if len(points) < self.min_points:
            return stats
        
        # Group points by date and time gaps
        daily_groups = self._group_by_date(points)
        
        for date, day_points in daily_groups.items():
            # Split into trajectory segments based on time gaps
            trajectory_segments = self._split_by_time_gaps(day_points)
            
            # Process each trajectory segment
            for i, segment_points in enumerate(trajectory_segments):
                if len(segment_points) >= self.min_points:
                    # Apply road-following if enabled
                    if self.map_matching_enabled and len(segment_points) > 10:
                        try:
                            matched_points = self._apply_road_following(segment_points)
                            if matched_points:
                                segment_points = matched_points
                                stats['road_following_applied'] += 1
                        except Exception as e:
                            logger.warning(f"Road-following failed for {entity_id}: {e}")
                    
                    # Create enhanced trajectory
                    trajectory = self._create_enhanced_trajectory(
                        entity_id, date, segment_points, segment_index=i
                    )
                    
                    # Detect stop points between trajectories
                    if i > 0:
                        prev_segment = trajectory_segments[i-1]
                        stop_points = self._detect_stop_points_between_trajectories(
                            prev_segment, segment_points
                        )
                        stats['stop_points'] += len(stop_points)
                    
                    stats['trajectories'] += 1
                    stats['points'] += len(segment_points)
        
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
    
    def _apply_road_following(self, points: List) -> Optional[List]:
        """
        Apply road-following map matching to trajectory points.
        Uses OSMnx to snap points to nearest roads.
        
        Args:
            points: List of GPSPoint objects
            
        Returns:
            List of adjusted GPSPoint objects or None if failed
        """
        try:
            import osmnx as ox
            import geopandas as gpd
            from shapely.geometry import Point as ShapelyPoint
            
            # Extract coordinates
            coords = [(p.longitude, p.latitude) for p in points]
            lons, lats = zip(*coords)
            
            # Get bounding box with buffer
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            # Add buffer (0.01 degrees ≈ 1.1 km at equator)
            buffer = 0.01
            north = max_lat + buffer
            south = min_lat - buffer
            east = max_lon + buffer
            west = min_lon - buffer
            
            # Download road network
            logger.info(f"Downloading road network for bbox: {north},{south},{east},{west}")
            G = ox.graph_from_bbox(north, south, east, west, network_type='drive')
            
            # Get road edges as GeoDataFrame
            edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
            
            # Create KDTree for nearest road search
            edge_centroids = edges.geometry.centroid
            edge_coords = [(c.x, c.y) for c in edge_centroids]
            tree = KDTree(edge_coords)
            
            # Snap each point to nearest road
            adjusted_points = []
            for point in points:
                # Find nearest road edge
                distance, idx = tree.query([(point.longitude, point.latitude)])
                nearest_edge = edges.iloc[idx[0]]
                
                # Get the road geometry
                road_geom = nearest_edge.geometry
                
                # Project point onto road geometry
                projected_point = road_geom.interpolate(road_geom.project(
                    ShapelyPoint(point.longitude, point.latitude)
                ))
                
                # Create adjusted point
                adjusted_point = GPSPoint(
                    dataset=point.dataset,
                    entity_id=point.entity_id,
                    timestamp=point.timestamp,
                    longitude=projected_point.x,
                    latitude=projected_point.y,
                    altitude=point.altitude,
                    speed=point.speed,
                    heading=point.heading,
                    extra_attributes={
                        **point.extra_attributes,
                        'map_matched': True,
                        'original_lon': point.longitude,
                        'original_lat': point.latitude,
                        'road_type': nearest_edge.get('highway', 'unknown')
                    }
                )
                adjusted_points.append(adjusted_point)
            
            return adjusted_points
            
        except Exception as e:
            logger.error(f"Road-following failed: {e}")
            return None
    
    def _detect_stop_points_between_trajectories(self, 
                                                prev_trajectory_points: List, 
                                                current_trajectory_points: List) -> List[Dict]:
        """
        Detect stop points between two consecutive trajectories.
        
        Args:
            prev_trajectory_points: Points from previous trajectory
            current_trajectory_points: Points from current trajectory
            
        Returns:
            List of stop point dictionaries
        """
        if not prev_trajectory_points or not current_trajectory_points:
            return []
        
        stop_points = []
        
        # Get the last point of previous trajectory and first point of current trajectory
        last_prev_point = prev_trajectory_points[-1]
        first_current_point = current_trajectory_points[0]
        
        # Calculate time gap between trajectories
        time_gap = (first_current_point.timestamp - last_prev_point.timestamp).total_seconds()
        
        # Calculate distance between end and start points
        if last_prev_point.geom and first_current_point.geom:
            distance = last_prev_point.geom.distance(first_current_point.geom) * 111000  # meters
            
            # Check if this could be a stop (small movement over long time)
            if time_gap > self.stop_detection_threshold_seconds and distance < 100:  # < 100 meters
                # Calculate average position (could be a stop location)
                avg_lon = (last_prev_point.longitude + first_current_point.longitude) / 2
                avg_lat = (last_prev_point.latitude + first_current_point.latitude) / 2
                
                stop_point = {
                    'entity_id': last_prev_point.entity_id,
                    'timestamp_start': last_prev_point.timestamp,
                    'timestamp_end': first_current_point.timestamp,
                    'duration_seconds': time_gap,
                    'longitude': avg_lon,
                    'latitude': avg_lat,
                    'distance_meters': distance,
                    'avg_speed_kmh': (distance / time_gap) * 3.6 if time_gap > 0 else 0,
                    'is_stop': True
                }
                stop_points.append(stop_point)
        
        return stop_points
    
    def _calculate_enhanced_metrics(self, points: List) -> Dict:
        """
        Calculate enhanced trajectory metrics.
        
        Args:
            points: List of GPSPoint objects
            
        Returns:
            Dictionary with enhanced metrics
        """
        if len(points) < 2:
            return {}
        
        metrics = {
            'total_distance_meters': 0,
            'speeds_kmh': [],
            'accelerations_ms2': [],
            'bearing_changes_deg': [],
            'stop_durations_seconds': [],
            'movement_ratio': 0
        }
        
        total_time = (points[-1].timestamp - points[0].timestamp).total_seconds()
        
        for i in range(1, len(points)):
            if points[i].geom and points[i-1].geom:
                # Calculate distance
                dist = points[i].geom.distance(points[i-1].geom) * 111000  # meters
                metrics['total_distance_meters'] += dist
                
                # Calculate time difference
                time_diff = (points[i].timestamp - points[i-1].timestamp).total_seconds()
                
                if time_diff > 0:
                    # Calculate speed
                    speed_kmh = (dist / time_diff) * 3.6
                    metrics['speeds_kmh'].append(speed_kmh)
                    
                    # Check for stop (speed below threshold)
                    if speed_kmh < self.speed_threshold_kmh:
                        metrics['stop_durations_seconds'].append(time_diff)
                    
                    # Calculate acceleration (if we have previous speed)
                    if i > 1 and len(metrics['speeds_kmh']) > 1:
                        prev_speed = metrics['speeds_kmh'][-2]
                        acceleration = (speed_kmh - prev_speed) / (time_diff * 3.6)  # m/s²
                        metrics['accelerations_ms2'].append(acceleration)
        
        # Calculate movement ratio (time moving vs total time)
        if total_time > 0:
            moving_time = total_time - sum(metrics['stop_durations_seconds'])
            metrics['movement_ratio'] = moving_time / total_time
        
        # Calculate statistics
        if metrics['speeds_kmh']:
            metrics['avg_speed_kmh'] = np.mean(metrics['speeds_kmh'])
            metrics['max_speed_kmh'] = np.max(metrics['speeds_kmh'])
            metrics['min_speed_kmh'] = np.min(metrics['speeds_kmh'])
            metrics['speed_std_kmh'] = np.std(metrics['speeds_kmh'])
        
        if metrics['accelerations_ms2']:
            metrics['avg_acceleration_ms2'] = np.mean(metrics['accelerations_ms2'])
            metrics['max_acceleration_ms2'] = np.max(metrics['accelerations_ms2'])
            metrics['min_acceleration_ms2'] = np.min(metrics['accelerations_ms2'])
        
        if metrics['stop_durations_seconds']:
            metrics['total_stop_time_seconds'] = sum(metrics['stop_durations_seconds'])
            metrics['avg_stop_duration_seconds'] = np.mean(metrics['stop_durations_seconds'])
        
        return metrics
    
    @transaction.atomic
    def _create_enhanced_trajectory(self, entity_id: str, date, points: List, segment_index: int = 0):
        """
        Create an enhanced trajectory record with detailed metrics.
        
        Args:
            entity_id: Entity identifier
            date: Trajectory date
            points: List of GPSPoint objects
            segment_index: Index of this trajectory segment for the day
        """
        try:
            start_time = points[0].timestamp
            end_time = points[-1].timestamp
            duration = (end_time - start_time).total_seconds()
            
            # Create line geometry
            coords = [(p.longitude, p.latitude) for p in points]
            geom = LineString(coords, srid=4326) if len(coords) >= 2 else None
            
            # Calculate enhanced metrics
            enhanced_metrics = self._calculate_enhanced_metrics(points)
            
            # Calculate basic metrics
            total_distance = enhanced_metrics.get('total_distance_meters', 0)
            avg_speed = enhanced_metrics.get('avg_speed_kmh', None)
            max_speed = enhanced_metrics.get('max_speed_kmh', None)
            
            # Create or update trajectory
            trajectory, created = Trajectory.objects.update_or_create(
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
                        **enhanced_metrics,
                        'segment_index': segment_index,
                        'has_road_following': self.map_matching_enabled,
                        'stop_count': len(enhanced_metrics.get('stop_durations_seconds', [])),
                        'movement_efficiency': enhanced_metrics.get('movement_ratio', 0)
                    }
                }
            )
            
            logger.info(f"{'Created' if created else 'Updated'} enhanced trajectory for {entity_id} on {date}")
            return trajectory
            
        except Exception as e:
            logger.error(f"Error creating enhanced trajectory: {e}")
            raise
    
    def get_trajectory_with_stops(self, entity_id: str, date) -> Dict:
        """
        Get trajectory data with detected stop points.
        
        Args:
            entity_id: Entity identifier
            date: Trajectory date
            
        Returns:
            Dictionary with trajectory and stop points
        """
        try:
            # Get trajectory
            trajectory = Trajectory.objects.get(
                dataset=self.dataset,
                entity_id=entity_id,
                trajectory_date=date
            )
            
            # Get all points for this entity on this date
            points = GPSPoint.objects.filter(
                dataset=self.dataset,
                entity_id=entity_id,
                timestamp__date=date,
                is_valid=True
            ).order_by('timestamp')
            
            # Detect stops within the trajectory
            stop_points = self._detect_stops_within_trajectory(list(points))
            
            return {
                'trajectory': {
                    'id': trajectory.id,
                    'entity_id': trajectory.entity_id,
                    'date': trajectory.trajectory_date,
                    'start_time': trajectory.start_time,
                    'end_time': trajectory.end_time,
                    'duration_seconds': trajectory.duration_seconds,
                    'total_distance_meters': trajectory.total_distance_meters,
                    'avg_speed_kmh': trajectory.avg_speed_kmh,
                    'max_speed_kmh': trajectory.max_speed_kmh,
                    'metrics': trajectory.metrics
                },
                'stop_points': stop_points,
                'total_stops': len(stop_points)
            }
            
        except Trajectory.DoesNotExist:
            logger.error(f"Trajectory not found for {entity_id} on {date}")
            return {'error': 'Trajectory not found'}
        except Exception as e:
            logger.error(f"Error getting trajectory with stops: {e}")
            return {'error': str(e)}
    
    def _detect_stops_within_trajectory(self, points: List) -> List[Dict]:
        """
        Detect stop points within a single trajectory.
        
        Args:
            points: List of GPSPoint objects
            
        Returns:
            List of stop point dictionaries
        """
        if len(points) < 2:
            return []
        
        stop_points = []
        current_stop = None
        
        for i in range(1, len(points)):
            if points[i].geom and points[i-1].geom:
                # Calculate distance and time
                dist = points[i].geom.distance(points[i-1].geom) * 111000  # meters
                time_diff = (points[i].timestamp - points[i-1].timestamp).total_seconds()
                
                if time_diff > 0:
                    speed_kmh = (dist / time_diff) * 3.6
                    
                    # Check if speed indicates a stop
                    if speed_kmh < self.speed_threshold_kmh:
                        if current_stop is None:
                            # Start new stop
                            current_stop = {
                                'start_point': points[i-1],
                                'end_point': points[i],
                                'duration_seconds': time_diff,
                                'points_in_stop': [points[i-1], points[i]]
                            }
                        else:
                            # Continue existing stop
                            current_stop['end_point'] = points[i]
                            current_stop['duration_seconds'] += time_diff
                            current_stop['points_in_stop'].append(points[i])
                    else:
                        # Movement detected, finalize current stop if exists
                        if current_stop is not None:
                            stop_point = self._create_stop_point_record(current_stop)
                            stop_points.append(stop_point)
                            current_stop = None
        
        # Finalize any ongoing stop
        if current_stop is not None:
            stop_point = self._create_stop_point_record(current_stop)
            stop_points.append(stop_point)
        
        return stop_points
    
    def _create_stop_point_record(self, stop_data: Dict) -> Dict:
        """
        Create a stop point record from stop data.
        
        Args:
            stop_data: Dictionary with stop information
            
        Returns:
            Formatted stop point dictionary
        """
        start_point = stop_data['start_point']
        end_point = stop_data['end_point']
        
        # Calculate centroid of all points in stop
        lons = [p.longitude for p in stop_data['points_in_stop']]
        lats = [p.latitude for p in stop_data['points_in_stop']]
        
        centroid_lon = sum(lons) / len(lons)
        centroid_lat = sum(lats) / len(lats)
        
        return {
            'entity_id': start_point.entity_id,
            'timestamp_start': start_point.timestamp,
            'timestamp_end': end_point.timestamp,
            'duration_seconds': stop_data['duration_seconds'],
            'longitude': centroid_lon,
            'latitude': centroid_lat,
            'point_count': len(stop_data['points_in_stop']),
            'avg_speed_kmh': 0,  # Stopped
            'is_stop': True,
            'stop_type': 'within_trajectory'
        }
    
    def calculate_average_speed_between_points(self, point1: GPSPoint, point2: GPSPoint) -> Optional[float]:
        """
        Calculate average speed between two GPS points.
        
        Args:
            point1: First GPS point
            point2: Second GPS point
            
        Returns:
            Average speed in km/h or None if calculation fails
        """
        if not point1.geom or not point2.geom:
            return None
        
        # Calculate distance
        distance = point1.geom.distance(point2.geom) * 111000  # meters
        
        # Calculate time difference
        time_diff = (point2.timestamp - point1.timestamp).total_seconds()
        
        if time_diff <= 0:
            return None
        
        # Calculate speed (km/h)
        speed_kmh = (distance / time_diff) * 3.6
        return speed_kmh
    
    def interpolate_trajectory_points(self, points: List, interval_seconds: int = 60) -> List[Dict]:
        """
        Interpolate trajectory points at regular time intervals.
        
        Args:
            points: List of GPSPoint objects
            interval_seconds: Time interval for interpolation
            
        Returns:
            List of interpolated points
        """
        if len(points) < 2:
            return []
        
        # Extract timestamps and coordinates
        timestamps = [p.timestamp.timestamp() for p in points]
        lons = [p.longitude for p in points]
        lats = [p.latitude for p in points]
        
        # Create interpolation functions
        lon_interp = interp1d(timestamps, lons, kind='linear', fill_value='extrapolate')
        lat_interp = interp1d(timestamps, lats, kind='linear', fill_value='extrapolate')
        
        # Generate interpolated points
        start_time = timestamps[0]
        end_time = timestamps[-1]
        interpolated_points = []
        
        current_time = start_time
        while current_time <= end_time:
            lon = float(lon_interp(current_time))
            lat = float(lat_interp(current_time))
            
            interpolated_points.append({
                'timestamp': current_time,
                'longitude': lon,
                'latitude': lat,
                'is_interpolated': True
            })
            
            current_time += interval_seconds
        
        return interpolated_points
