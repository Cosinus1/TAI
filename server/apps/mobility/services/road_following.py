"""
============================================================================
Simplified Road-Following Algorithm
============================================================================
A lightweight road-following algorithm that doesn't require OSMnx.
Uses road network inference and point snapping techniques.
============================================================================
"""

import numpy as np
from typing import List, Tuple, Optional
import logging
from scipy.spatial import KDTree
from scipy.interpolate import interp1d
import math

logger = logging.getLogger(__name__)


class SimplifiedRoadFollower:
    """
    Simplified road-following algorithm that:
    1. Infers road directions from trajectory points
    2. Snaps points to inferred road centerlines
    3. Smooths trajectories to follow more natural paths
    """
    
    def __init__(self, smoothing_factor: float = 0.3, snap_distance_meters: float = 50.0):
        """
        Initialize the road follower.
        
        Args:
            smoothing_factor: How much to smooth the trajectory (0-1)
            snap_distance_meters: Maximum distance to snap points to roads
        """
        self.smoothing_factor = smoothing_factor
        self.snap_distance_meters = snap_distance_meters
        self.earth_radius_km = 6371.0
    
    def degrees_to_radians(self, degrees: float) -> float:
        """Convert degrees to radians."""
        return degrees * math.pi / 180.0
    
    def radians_to_degrees(self, radians: float) -> float:
        """Convert radians to degrees."""
        return radians * 180.0 / math.pi
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points.
        
        Args:
            lat1, lon1: First point coordinates in degrees
            lat2, lon2: Second point coordinates in degrees
            
        Returns:
            Distance in kilometers
        """
        lat1_rad = self.degrees_to_radians(lat1)
        lon1_rad = self.degrees_to_radians(lon1)
        lat2_rad = self.degrees_to_radians(lat2)
        lon2_rad = self.degrees_to_radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return self.earth_radius_km * c
    
    def meters_to_degrees(self, meters: float, latitude: float) -> Tuple[float, float]:
        """
        Convert meters to approximate degrees at a given latitude.
        
        Args:
            meters: Distance in meters
            latitude: Latitude for conversion
            
        Returns:
            Tuple of (degrees_latitude, degrees_longitude)
        """
        # 1 degree of latitude ≈ 111 km everywhere
        degrees_lat = meters / 111000.0
        
        # 1 degree of longitude varies with latitude
        degrees_lon = meters / (111000.0 * math.cos(self.degrees_to_radians(latitude)))
        
        return degrees_lat, degrees_lon
    
    def infer_road_directions(self, points: List[Tuple[float, float]]) -> List[float]:
        """
        Infer road directions from trajectory points.
        
        Args:
            points: List of (longitude, latitude) tuples
            
        Returns:
            List of inferred bearing angles in degrees
        """
        if len(points) < 2:
            return []
        
        bearings = []
        
        for i in range(1, len(points)):
            lon1, lat1 = points[i-1]
            lon2, lat2 = points[i]
            
            # Calculate bearing
            lat1_rad = self.degrees_to_radians(lat1)
            lat2_rad = self.degrees_to_radians(lat2)
            dlon_rad = self.degrees_to_radians(lon2 - lon1)
            
            y = math.sin(dlon_rad) * math.cos(lat2_rad)
            x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
            
            bearing = math.atan2(y, x)
            bearing_deg = self.radians_to_degrees(bearing)
            
            # Normalize to 0-360
            bearing_deg = (bearing_deg + 360) % 360
            bearings.append(bearing_deg)
        
        return bearings
    
    def smooth_trajectory(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Smooth trajectory using moving average.
        
        Args:
            points: List of (longitude, latitude) tuples
            
        Returns:
            Smoothed trajectory points
        """
        if len(points) < 3:
            return points
        
        smoothed = []
        window_size = 3
        
        for i in range(len(points)):
            # Get window indices
            start = max(0, i - window_size // 2)
            end = min(len(points), i + window_size // 2 + 1)
            
            # Calculate weighted average
            window_points = points[start:end]
            weights = [1.0 / (abs(j - i) + 1) for j in range(start, end)]
            total_weight = sum(weights)
            
            avg_lon = sum(p[0] * w for p, w in zip(window_points, weights)) / total_weight
            avg_lat = sum(p[1] * w for p, w in zip(window_points, weights)) / total_weight
            
            # Blend with original point
            orig_lon, orig_lat = points[i]
            blended_lon = orig_lon * (1 - self.smoothing_factor) + avg_lon * self.smoothing_factor
            blended_lat = orig_lat * (1 - self.smoothing_factor) + avg_lat * self.smoothing_factor
            
            smoothed.append((blended_lon, blended_lat))
        
        return smoothed
    
    def snap_to_road_network(self, points: List[Tuple[float, float]], 
                           road_segments: Optional[List[Tuple[Tuple[float, float], Tuple[float, float]]]] = None) -> List[Tuple[float, float]]:
        """
        Snap points to nearest road segments.
        
        Args:
            points: List of (longitude, latitude) tuples
            road_segments: Optional list of road segments as ((lon1, lat1), (lon2, lat2))
            
        Returns:
            Snapped points
        """
        if not road_segments:
            # If no road network provided, infer from trajectory
            return self._infer_and_snap(points)
        
        snapped_points = []
        
        for point in points:
            nearest_point = self._find_nearest_point_on_segments(point, road_segments)
            if nearest_point:
                # Check if snap distance is reasonable
                distance_km = self.haversine_distance(point[1], point[0], nearest_point[1], nearest_point[0])
                if distance_km * 1000 <= self.snap_distance_meters:
                    snapped_points.append(nearest_point)
                else:
                    snapped_points.append(point)
            else:
                snapped_points.append(point)
        
        return snapped_points
    
    def _infer_and_snap(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Infer road network from trajectory and snap points.
        
        Args:
            points: List of (longitude, latitude) tuples
            
        Returns:
            Snapped points
        """
        if len(points) < 2:
            return points
        
        # Create inferred road segments from trajectory
        inferred_segments = []
        for i in range(1, len(points)):
            inferred_segments.append((points[i-1], points[i]))
        
        # Snap points to inferred segments
        return self.snap_to_road_network(points, inferred_segments)
    
    def _find_nearest_point_on_segments(self, point: Tuple[float, float], 
                                      segments: List[Tuple[Tuple[float, float], Tuple[float, float]]]) -> Optional[Tuple[float, float]]:
        """
        Find nearest point on any road segment.
        
        Args:
            point: (longitude, latitude) to snap
            segments: List of road segments
            
        Returns:
            Nearest point on segments or None
        """
        if not segments:
            return None
        
        min_distance = float('inf')
        nearest_point = None
        
        for segment in segments:
            p1, p2 = segment
            projected = self._project_point_on_line(point, p1, p2)
            
            if projected:
                distance = self.haversine_distance(point[1], point[0], projected[1], projected[0])
                if distance < min_distance:
                    min_distance = distance
                    nearest_point = projected
        
        return nearest_point
    
    def _project_point_on_line(self, point: Tuple[float, float], 
                             line_start: Tuple[float, float], 
                             line_end: Tuple[float, float]) -> Optional[Tuple[float, float]]:
        """
        Project a point onto a line segment.
        
        Args:
            point: Point to project
            line_start: Start of line segment
            line_end: End of line segment
            
        Returns:
            Projected point or None
        """
        # Convert to numpy arrays for easier math
        p = np.array(point)
        a = np.array(line_start)
        b = np.array(line_end)
        
        # Calculate projection
        ap = p - a
        ab = b - a
        
        # Check if line segment has zero length
        ab_norm_sq = np.dot(ab, ab)
        if ab_norm_sq == 0:
            return tuple(a)
        
        # Project point onto line
        t = np.dot(ap, ab) / ab_norm_sq
        
        # Clamp to line segment
        t = max(0, min(1, t))
        
        # Calculate projected point
        projection = a + t * ab
        
        return (float(projection[0]), float(projection[1]))
    
    def follow_roads(self, points: List[Tuple[float, float]], 
                    apply_smoothing: bool = True,
                    apply_snapping: bool = True) -> List[Tuple[float, float]]:
        """
        Main method to apply road-following to trajectory points.
        
        Args:
            points: List of (longitude, latitude) tuples
            apply_smoothing: Whether to smooth the trajectory
            apply_snapping: Whether to snap points to roads
            
        Returns:
            Road-followed trajectory points
        """
        if len(points) < 2:
            return points
        
        result_points = points.copy()
        
        # Step 1: Smooth trajectory
        if apply_smoothing:
            result_points = self.smooth_trajectory(result_points)
        
        # Step 2: Snap to road network
        if apply_snapping:
            result_points = self.snap_to_road_network(result_points)
        
        # Step 3: Ensure connectivity (no large jumps)
        result_points = self._ensure_connectivity(result_points)
        
        return result_points
    
    def _ensure_connectivity(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Ensure points are reasonably connected (no large jumps).
        
        Args:
            points: List of (longitude, latitude) tuples
            
        Returns:
            Connected points
        """
        if len(points) < 2:
            return points
        
        connected_points = [points[0]]
        
        for i in range(1, len(points)):
            prev_point = connected_points[-1]
            current_point = points[i]
            
            # Calculate distance
            distance_km = self.haversine_distance(
                prev_point[1], prev_point[0],
                current_point[1], current_point[0]
            )
            
            # If distance is too large, interpolate intermediate points
            max_distance_km = 0.5  # 500 meters
            if distance_km > max_distance_km:
                # Calculate number of intermediate points needed
                num_intermediate = int(distance_km / max_distance_km)
                
                # Interpolate
                for j in range(1, num_intermediate + 1):
                    t = j / (num_intermediate + 1)
                    interp_lon = prev_point[0] + t * (current_point[0] - prev_point[0])
                    interp_lat = prev_point[1] + t * (current_point[1] - prev_point[1])
                    connected_points.append((interp_lon, interp_lat))
            
            connected_points.append(current_point)
        
        return connected_points
    
    def calculate_road_alignment_score(self, original_points: List[Tuple[float, float]], 
                                     followed_points: List[Tuple[float, float]]) -> float:
        """
        Calculate how well the followed trajectory aligns with roads.
        
        Args:
            original_points: Original trajectory points
            followed_points: Road-followed trajectory points
            
        Returns:
            Alignment score (0-1, higher is better)
        """
        if len(original_points) != len(followed_points) or len(original_points) < 2:
            return 0.0
        
        total_distance = 0.0
        total_deviation = 0.0
        
        for i in range(len(original_points)):
            orig = original_points[i]
            followed = followed_points[i]
            
            # Calculate deviation
            deviation_km = self.haversine_distance(orig[1], orig[0], followed[1], followed[0])
            total_deviation += deviation_km
            
            # Calculate segment distance
            if i > 0:
                prev_orig = original_points[i-1]
                segment_distance = self.haversine_distance(prev_orig[1], prev_orig[0], orig[1], orig[0])
                total_distance += segment_distance
        
        if total_distance == 0:
            return 1.0  # No movement
        
        # Score is inversely proportional to average deviation
        avg_deviation_km = total_deviation / len(original_points)
        avg_segment_distance_km = total_distance / (len(original_points) - 1) if len(original_points) > 1 else 1.0
        
        # Normalize deviation by segment distance
        normalized_deviation = avg_deviation_km / avg_segment_distance_km if avg_segment_distance_km > 0 else 0.0
        
        # Convert to score (0-1)
        score = max(0.0, 1.0 - normalized_deviation)
        
        return score