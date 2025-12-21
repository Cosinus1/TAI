"""
============================================================================
Trajectory Analysis Service using scikit-mobility and movingpandas
============================================================================
Description: Enhanced trajectory analysis using specialized mobility libraries
            for trajectory segmentation, stop detection, and pattern analysis
============================================================================
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

try:
    import skmob
    from skmob import TrajDataFrame
    from skmob.preprocessing import detection, clustering
    from skmob.measures.individual import radius_of_gyration, number_of_locations
    SKMOB_AVAILABLE = True
except ImportError:
    SKMOB_AVAILABLE = False
    TrajDataFrame = pd.DataFrame
    logging.warning("scikit-mobility not available")

try:
    import movingpandas as mpd
    from movingpandas import TrajectoryCollection
    MOVINGPANDAS_AVAILABLE = True
except ImportError:
    MOVINGPANDAS_AVAILABLE = False
    logging.warning("movingpandas not available")

try:
    import trackintel as ti
    from trackintel.preprocessing import positionfixes
    TRACKINTEL_AVAILABLE = True
except ImportError:
    TRACKINTEL_AVAILABLE = False
    logging.warning("trackintel not available")

from django.db import models
from django.contrib.gis.geos import LineString, Point
from apps.mobility.models import TDriveRawPoint, TDriveTrajectory


class TrajectoryAnalyzer:
    """
    Enhanced trajectory analysis service using specialized mobility libraries.
    
    Features:
    - Trajectory segmentation and stop detection
    - Movement pattern analysis
    - Origin-Destination extraction
    - Mobility metrics calculation
    """
    
    def __init__(self, min_points_per_trajectory: int = 10, 
                 stop_detection_threshold: int = 300,
                 max_speed_kmh: float = 120.0):
        """
        Initialize the trajectory analyzer.
        
        Args:
            min_points_per_trajectory: Minimum points to consider a valid trajectory
            stop_detection_threshold: Time threshold (seconds) for stop detection
            max_speed_kmh: Maximum plausible speed for filtering outliers
        """
        self.min_points = min_points_per_trajectory
        self.stop_threshold = stop_detection_threshold
        self.max_speed = max_speed_kmh
        
        if not SKMOB_AVAILABLE:
            logging.error("scikit-mobility is required for trajectory analysis")
        
        if not MOVINGPANDAS_AVAILABLE:
            logging.error("movingpandas is required for trajectory operations")
    
    def analyze_taxi_trajectories(self, taxi_id: str, date: Optional[datetime] = None) -> Dict:
        """
        Analyze trajectories for a specific taxi using scikit-mobility.
        
        Args:
            taxi_id: Taxi identifier
            date: Specific date to analyze (None for all dates)
        
        Returns:
            Dictionary with trajectory analysis results
        """
        if not SKMOB_AVAILABLE:
            return {"error": "scikit-mobility not available"}
        
        # Query raw points
        query = TDriveRawPoint.objects.filter(taxi_id=taxi_id, is_valid=True)
        if date:
            query = query.filter(timestamp__date=date)
        
        points = query.order_by('timestamp').values('timestamp', 'longitude', 'latitude')
        
        if len(points) < self.min_points:
            return {"error": f"Insufficient points: {len(points)} < {self.min_points}"}
        
        # Convert to DataFrame
        df = pd.DataFrame(list(points))
        df.rename(columns={
            'timestamp': 'datetime',
            'longitude': 'lng',
            'latitude': 'lat'
        }, inplace=True)
        
        # Create TrajDataFrame
        tdf = TrajDataFrame(df, latitude='lat', longitude='lng', datetime='datetime')
        
        # Calculate mobility metrics
        metrics = self._calculate_mobility_metrics(tdf, taxi_id)
        
        # Detect stops
        stops = self._detect_stops(tdf)
        
        # Extract OD pairs
        od_pairs = self._extract_od_pairs(tdf)
        
        return {
            'taxi_id': taxi_id,
            'date': date,
            'total_points': len(tdf),
            'metrics': metrics,
            'stops': stops,
            'od_pairs': od_pairs
        }
    
    def _calculate_mobility_metrics(self, tdf: TrajDataFrame, taxi_id: str) -> Dict:
        """Calculate comprehensive mobility metrics."""
        metrics = {}
        
        try:
            # Radius of gyration
            metrics['radius_of_gyration_km'] = radius_of_gyration(tdf)
            
            # Number of distinct locations
            metrics['number_of_locations'] = number_of_locations(tdf)
            
            # Temporal metrics
            time_range = tdf['datetime'].max() - tdf['datetime'].min()
            metrics['duration_hours'] = time_range.total_seconds() / 3600
            metrics['points_per_hour'] = len(tdf) / metrics['duration_hours'] if metrics['duration_hours'] > 0 else 0
            
            # Spatial extent
            metrics['max_latitude'] = tdf['lat'].max()
            metrics['min_latitude'] = tdf['lat'].min()
            metrics['max_longitude'] = tdf['lng'].max()
            metrics['min_longitude'] = tdf['lng'].min()
            
        except Exception as e:
            logging.error(f"Error calculating metrics for taxi {taxi_id}: {e}")
            metrics['error'] = str(e)
        
        return metrics
    
    def _detect_stops(self, tdf: TrajDataFrame) -> List[Dict]:
        """Detect stops in trajectory using scikit-mobility."""
        if not SKMOB_AVAILABLE:
            return []
        
        try:
            # Detect stops using time and distance thresholds
            stops_tdf = detection.stops(
                tdf, 
                minutes_for_a_stop=self.stop_threshold / 60,  # Convert to minutes
                spatial_radius_km=0.2,  # 200 meters
                leaving_time=True
            )
            
            stops = []
            for _, stop in stops_tdf.iterrows():
                stops.append({
                    'latitude': stop['lat'],
                    'longitude': stop['lng'],
                    'start_time': stop['datetime'],
                    'end_time': stop['leaving_datetime'],
                    'duration_minutes': (stop['leaving_datetime'] - stop['datetime']).total_seconds() / 60
                })
            
            return stops
        
        except Exception as e:
            logging.error(f"Error detecting stops: {e}")
            return []
    
    def _extract_od_pairs(self, tdf: TrajDataFrame) -> List[Dict]:
        """Extract Origin-Destination pairs from trajectory."""
        if len(tdf) < 2:
            return []
        
        od_pairs = []
        
        try:
            # Simple OD extraction: consecutive stops or significant moves
            stops = self._detect_stops(tdf)
            
            if len(stops) >= 2:
                for i in range(len(stops) - 1):
                    origin = stops[i]
                    destination = stops[i + 1]
                    
                    od_pairs.append({
                        'origin_lat': origin['latitude'],
                        'origin_lng': origin['longitude'],
                        'destination_lat': destination['latitude'],
                        'destination_lng': destination['longitude'],
                        'departure_time': origin['end_time'],
                        'arrival_time': destination['start_time'],
                        'trip_duration_minutes': (destination['start_time'] - origin['end_time']).total_seconds() / 60
                    })
        
        except Exception as e:
            logging.error(f"Error extracting OD pairs: {e}")
        
        return od_pairs
    
    def create_trajectory_collection(self, taxi_ids: List[str], 
                                   start_date: datetime, 
                                   end_date: datetime) -> Optional[TrajectoryCollection]:
        """
        Create a MovingPandas TrajectoryCollection for multiple taxis.
        
        Args:
            taxi_ids: List of taxi identifiers
            start_date: Start of time range
            end_date: End of time range
        
        Returns:
            TrajectoryCollection object or None if movingpandas not available
        """
        if not MOVINGPANDAS_AVAILABLE:
            return None
        
        try:
            # Query points for all specified taxis
            points = TDriveRawPoint.objects.filter(
                taxi_id__in=taxi_ids,
                timestamp__range=(start_date, end_date),
                is_valid=True
            ).order_by('taxi_id', 'timestamp').values(
                'taxi_id', 'timestamp', 'longitude', 'latitude'
            )
            
            if not points:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(list(points))
            df.rename(columns={
                'timestamp': 't',
                'longitude': 'longitude',
                'latitude': 'latitude'
            }, inplace=True)
            
            # Create TrajectoryCollection
            collection = TrajectoryCollection(
                df, 
                traj_id_col='taxi_id',
                t='t',
                x='longitude', 
                y='latitude',
                crs='EPSG:4326'
            )
            
            return collection
        
        except Exception as e:
            logging.error(f"Error creating trajectory collection: {e}")
            return None
    
    def segment_trajectories_by_time(self, collection: TrajectoryCollection, 
                                   time_threshold_minutes: int = 30) -> TrajectoryCollection:
        """
        Segment trajectories by time gaps using MovingPandas.
        
        Args:
            collection: TrajectoryCollection to segment
            time_threshold_minutes: Maximum time gap between points in same segment
        
        Returns:
            Segmented TrajectoryCollection
        """
        if not MOVINGPANDAS_AVAILABLE:
            return collection
        
        try:
            # Segment trajectories by time gaps
            segmented = collection.split_by_time_gap(
                tolerance=timedelta(minutes=time_threshold_minutes)
            )
            return segmented
        
        except Exception as e:
            logging.error(f"Error segmenting trajectories: {e}")
            return collection
    
    def calculate_trajectory_metrics(self, collection: TrajectoryCollection) -> Dict:
        """
        Calculate comprehensive metrics for a trajectory collection.
        
        Args:
            collection: TrajectoryCollection to analyze
        
        Returns:
            Dictionary with trajectory metrics
        """
        if not MOVINGPANDAS_AVAILABLE:
            return {"error": "movingpandas not available"}
        
        metrics = {
            'total_trajectories': len(collection.trajectories),
            'total_points': 0,
            'total_distance_km': 0,
            'total_duration_hours': 0,
            'trajectory_details': []
        }
        
        try:
            for traj in collection.trajectories:
                traj_metrics = {
                    'taxi_id': traj.id,
                    'points_count': len(traj.df),
                    'distance_km': traj.get_length() / 1000,  # Convert to km
                    'duration_hours': (traj.get_end_time() - traj.get_start_time()).total_seconds() / 3600,
                    'start_time': traj.get_start_time(),
                    'end_time': traj.get_end_time(),
                    'avg_speed_kmh': 0
                }
                
                # Calculate average speed
                if traj_metrics['duration_hours'] > 0:
                    traj_metrics['avg_speed_kmh'] = traj_metrics['distance_km'] / traj_metrics['duration_hours']
                
                metrics['total_points'] += traj_metrics['points_count']
                metrics['total_distance_km'] += traj_metrics['distance_km']
                metrics['total_duration_hours'] += traj_metrics['duration_hours']
                metrics['trajectory_details'].append(traj_metrics)
            
            return metrics
        
        except Exception as e:
            logging.error(f"Error calculating trajectory metrics: {e}")
            return {"error": str(e)}
