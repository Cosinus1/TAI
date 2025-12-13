"""
============================================================================
GPS Processing Service using scikit-move, traja, and pymove
============================================================================
Description: Enhanced GPS data processing using specialized movement analysis libraries
            for data cleaning, feature extraction, and trajectory preprocessing
============================================================================
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

# GPS processing libraries
try:
    import scikit_move as skmove
    from scikit_move.preprocessing import filters, trajectory
    from scikit_move.utils import distance, velocity
    SKMOVE_AVAILABLE = True
except ImportError:
    SKMOVE_AVAILABLE = False
    logging.warning("scikit-move not available")

try:
    import traja
    from traja import TrajaDataFrame
    from traja.models import generative
    TRAJA_AVAILABLE = True
except ImportError:
    TRAJA_AVAILABLE = False
    logging.warning("traja not available")

try:
    import pymove
    from pymove import MoveDataFrame
    from pymove.preprocessing import filters, segmentation
    from pymove.utils.constants import DATETIME, LATITUDE, LONGITUDE, TRAJ_ID
    PYMOVE_AVAILABLE = True
except ImportError:
    PYMOVE_AVAILABLE = False
    logging.warning("pymove not available")

from django.db import models
from django.contrib.gis.geos import Point
from apps.mobility.models import TDriveRawPoint


class GPSProcessor:
    """
    Enhanced GPS processing service using specialized movement analysis libraries.
    
    Features:
    - GPS data cleaning and filtering
    - Movement feature extraction
    - Trajectory preprocessing
    - Outlier detection and removal
    """
    
    def __init__(self, max_speed_kmh: float = 120.0, 
                 min_speed_kmh: float = 1.0,
                 sampling_rate_seconds: int = 30):
        """
        Initialize the GPS processor.
        
        Args:
            max_speed_kmh: Maximum plausible speed for filtering outliers
            min_speed_kmh: Minimum speed threshold for movement detection
            sampling_rate_seconds: Expected sampling rate for interpolation
        """
        self.max_speed = max_speed_kmh
        self.min_speed = min_speed_kmh
        self.sampling_rate = sampling_rate_seconds
        
        if not SKMOVE_AVAILABLE:
            logging.warning("scikit-move not available - limited functionality")
        
        if not TRAJA_AVAILABLE:
            logging.warning("traja not available - limited functionality")
    
    def clean_gps_data(self, taxi_id: str, date: Optional[datetime] = None) -> Dict:
        """
        Clean and preprocess GPS data for a specific taxi.
        
        Args:
            taxi_id: Taxi identifier
            date: Specific date to process (None for all dates)
        
        Returns:
            Dictionary with cleaning results and statistics
        """
        # Query raw points
        query = TDriveRawPoint.objects.filter(taxi_id=taxi_id, is_valid=True)
        if date:
            query = query.filter(timestamp__date=date)
        
        points = query.order_by('timestamp').values('id', 'timestamp', 'longitude', 'latitude')
        
        if not points:
            return {"error": "No valid points found"}
        
        # Convert to DataFrame
        df = pd.DataFrame(list(points))
        df.rename(columns={
            'timestamp': 'datetime',
            'longitude': 'lng',
            'latitude': 'lat'
        }, inplace=True)
        
        # Apply cleaning pipeline
        cleaned_df = self._apply_cleaning_pipeline(df, taxi_id)
        
        # Calculate statistics
        stats = self._calculate_cleaning_stats(df, cleaned_df)
        
        return {
            'taxi_id': taxi_id,
            'date': date,
            'original_points': len(df),
            'cleaned_points': len(cleaned_df),
            'removed_points': len(df) - len(cleaned_df),
            'cleaning_stats': stats,
            'cleaned_data': cleaned_df.to_dict('records')
        }
    
    def _apply_cleaning_pipeline(self, df: pd.DataFrame, taxi_id: str) -> pd.DataFrame:
        """
        Apply comprehensive GPS data cleaning pipeline.
        
        Args:
            df: Raw GPS data DataFrame
            taxi_id: Taxi identifier for logging
        
        Returns:
            Cleaned DataFrame
        """
        cleaned_df = df.copy()
        
        try:
            # 1. Remove duplicates
            cleaned_df = cleaned_df.drop_duplicates(subset=['datetime'], keep='first')
            
            # 2. Sort by timestamp
            cleaned_df = cleaned_df.sort_values('datetime').reset_index(drop=True)
            
            # 3. Remove outliers using different methods based on available libraries
            if SKMOVE_AVAILABLE:
                cleaned_df = self._remove_outliers_skmove(cleaned_df, taxi_id)
            elif PYMOVE_AVAILABLE:
                cleaned_df = self._remove_outliers_pymove(cleaned_df, taxi_id)
            else:
                # Fallback: basic speed-based filtering
                cleaned_df = self._remove_outliers_basic(cleaned_df, taxi_id)
            
            # 4. Interpolate missing points if needed
            cleaned_df = self._interpolate_missing_points(cleaned_df, taxi_id)
            
            return cleaned_df
        
        except Exception as e:
            logging.error(f"Error in cleaning pipeline for taxi {taxi_id}: {e}")
            return df  # Return original data if cleaning fails
    
    def _remove_outliers_skmove(self, df: pd.DataFrame, taxi_id: str) -> pd.DataFrame:
        """Remove outliers using scikit-move."""
        try:
            # Convert to scikit-move format
            move_df = skmove.MoveDataFrame(
                df,
                latitude='lat',
                longitude='lng',
                datetime='datetime'
            )
            
            # Remove speed outliers
            filtered_df = filters.filter_by_speed(
                move_df,
                max_speed=self.max_speed / 3.6  # Convert km/h to m/s
            )
            
            return filtered_df.to_dataframe()
        
        except Exception as e:
            logging.error(f"Error removing outliers with scikit-move for taxi {taxi_id}: {e}")
            return df
    
    def _remove_outliers_pymove(self, df: pd.DataFrame, taxi_id: str) -> pd.DataFrame:
        """Remove outliers using pymove."""
        try:
            # Convert to pymove format
            move_df = MoveDataFrame(
                df,
                latitude='lat',
                longitude='lng',
                datetime='datetime'
            )
            
            # Filter by speed
            move_df = filters.by_speed(
                move_df,
                max_speed=self.max_speed / 3.6  # Convert km/h to m/s
            )
            
            return move_df.to_dataframe()
        
        except Exception as e:
            logging.error(f"Error removing outliers with pymove for taxi {taxi_id}: {e}")
            return df
    
    def _remove_outliers_basic(self, df: pd.DataFrame, taxi_id: str) -> pd.DataFrame:
        """Basic outlier removal using speed calculation."""
        try:
            if len(df) < 2:
                return df
            
            # Calculate speeds between consecutive points
            speeds = []
            for i in range(1, len(df)):
                point1 = df.iloc[i-1]
                point2 = df.iloc[i]
                
                # Calculate distance using Haversine formula
                lat1, lon1 = np.radians(point1['lat']), np.radians(point1['lng'])
                lat2, lon2 = np.radians(point2['lat']), np.radians(point2['lng'])
                
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
                c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
                distance_km = 6371 * c  # Earth radius in km
                
                # Calculate time difference in hours
                time_diff = (point2['datetime'] - point1['datetime']).total_seconds() / 3600
                
                if time_diff > 0:
                    speed_kmh = distance_km / time_diff
                else:
                    speed_kmh = 0
                
                speeds.append(speed_kmh)
            
            # Add speeds to DataFrame (first point gets speed 0)
            speeds = [0] + speeds
            
            # Filter points with reasonable speeds
            mask = (np.array(speeds) <= self.max_speed) & (np.array(speeds) >= 0)
            filtered_df = df[mask].copy()
            
            return filtered_df
        
        except Exception as e:
            logging.error(f"Error in basic outlier removal for taxi {taxi_id}: {e}")
            return df
    
    def _interpolate_missing_points(self, df: pd.DataFrame, taxi_id: str) -> pd.DataFrame:
        """Interpolate missing GPS points to regular time intervals."""
        try:
            if len(df) < 2:
                return df
            
            # Set datetime as index
            df = df.set_index('datetime')
            
            # Create regular time index
            start_time = df.index.min()
            end_time = df.index.max()
            regular_index = pd.date_range(
                start=start_time,
                end=end_time,
                freq=f'{self.sampling_rate}S'
            )
            
            # Reindex and interpolate
            df_regular = df.reindex(regular_index)
            
            # Interpolate coordinates
            df_regular['lat'] = df_regular['lat'].interpolate(method='linear')
            df_regular['lng'] = df_regular['lng'].interpolate(method='linear')
            
            # Forward fill other columns
            df_regular['id'] = df_regular['id'].ffill()
            
            # Reset index
            df_regular = df_regular.reset_index().rename(columns={'index': 'datetime'})
            
            return df_regular
        
        except Exception as e:
            logging.error(f"Error interpolating points for taxi {taxi_id}: {e}")
            return df.reset_index().rename(columns={'index': 'datetime'})
    
    def _calculate_cleaning_stats(self, original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> Dict:
        """Calculate statistics about the cleaning process."""
        stats = {
            'removed_duplicates': len(original_df) - len(original_df.drop_duplicates(subset=['datetime'])),
            'removed_outliers': len(original_df) - len(cleaned_df),
            'cleaning_efficiency': (len(cleaned_df) / len(original_df)) * 100 if len(original_df) > 0 else 0
        }
        
        # Calculate time coverage
        if len(cleaned_df) >= 2:
            time_range = cleaned_df['datetime'].max() - cleaned_df['datetime'].min()
            stats['time_coverage_hours'] = time_range.total_seconds() / 3600
            stats['points_per_hour'] = len(cleaned_df) / stats['time_coverage_hours']
        else:
            stats['time_coverage_hours'] = 0
            stats['points_per_hour'] = 0
        
        return stats
    
    def extract_movement_features(self, taxi_id: str, date: Optional[datetime] = None) -> Dict:
        """
        Extract comprehensive movement features from GPS data.
        
        Args:
            taxi_id: Taxi identifier
            date: Specific date to analyze (None for all dates)
        
        Returns:
            Dictionary with extracted features
        """
        # Query cleaned points
        query = TDriveRawPoint.objects.filter(taxi_id=taxi_id, is_valid=True)
        if date:
            query = query.filter(timestamp__date=date)
        
        points = query.order_by('timestamp').values('timestamp', 'longitude', 'latitude')
        
        if len(points) < 2:
            return {"error": "Insufficient points for feature extraction"}
        
        # Convert to DataFrame
        df = pd.DataFrame(list(points))
        df.rename(columns={
            'timestamp': 'datetime',
            'longitude': 'lng',
            'latitude': 'lat'
        }, inplace=True)
        
        features = {}
        
        # Extract features using available libraries
        if SKMOVE_AVAILABLE:
            features.update(self._extract_features_skmove(df, taxi_id))
        elif TRAJA_AVAILABLE:
            features.update(self._extract_features_traja(df, taxi_id))
        else:
            features.update(self._extract_features_basic(df, taxi_id))
        
        return {
            'taxi_id': taxi_id,
            'date': date,
            'total_points': len(df),
            'features': features
        }
    
    def _extract_features_skmove(self, df: pd.DataFrame, taxi_id: str) -> Dict:
        """Extract movement features using scikit-move."""
        try:
            # Convert to scikit-move format
            move_df = skmove.MoveDataFrame(
                df,
                latitude='lat',
                longitude='lng',
                datetime='datetime'
            )
            
            features = {}
            
            # Calculate basic statistics
            features['total_distance_km'] = trajectory.total_distance(move_df) / 1000
            features['avg_speed_kmh'] = trajectory.average_speed(move_df) * 3.6
            features['max_speed_kmh'] = trajectory.max_speed(move_df) * 3.6
            
            # Calculate movement metrics
            features['stop_ratio'] = trajectory.stop_ratio(move_df)
            features['entropy'] = trajectory.entropy(move_df)
            
            return features
        
        except Exception as e:
            logging.error(f"Error extracting features with scikit-move for taxi {taxi_id}: {e}")
            return {}
    
    def _extract_features_traja(self, df: pd.DataFrame, taxi_id: str) -> Dict:
        """Extract movement features using traja."""
        try:
            # Convert to traja format
            traj_df = TrajaDataFrame(
                df,
                x='lng',
                y='lat',
                time='datetime'
            )
            
            features = {}
            
            # Calculate basic trajectory metrics
            features['total_distance_km'] = traj_df.trajectory.distance / 1000
            features['straightness'] = traj_df.trajectory.straightness()
            features['tortuosity'] = traj_df.trajectory.tortuosity()
            
            return features
        
        except Exception as e:
            logging.error(f"Error extracting features with traja for taxi {taxi_id}: {e}")
            return {}
    
    def _extract_features_basic(self, df: pd.DataFrame, taxi_id: str) -> Dict:
        """Extract basic movement features without specialized libraries."""
        features = {}
        
        try:
            if len(df) < 2:
                return features
            
            # Calculate total distance
            total_distance = 0
            speeds = []
            
            for i in range(1, len(df)):
                point1 = df.iloc[i-1]
                point2 = df.iloc[i]
                
                # Calculate distance using Haversine formula
                lat1, lon1 = np.radians(point1['lat']), np.radians(point1['lng'])
                lat2, lon2 = np.radians(point2['lat']), np.radians(point2['lng'])
                
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
                c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
                distance_km = 6371 * c
                
                total_distance += distance_km
                
                # Calculate speed
                time_diff = (point2['datetime'] - point1['datetime']).total_seconds() / 3600
                if time_diff > 0:
                    speed_kmh = distance_km / time_diff
                    speeds.append(speed_kmh)
            
            features['total_distance_km'] = total_distance
            features['avg_speed_kmh'] = np.mean(speeds) if speeds else 0
            features['max_speed_kmh'] = np.max(speeds) if speeds else 0
            features['std_speed_kmh'] = np.std(speeds) if speeds else 0
            
            return features
        
        except Exception as e:
            logging.error(f"Error extracting basic features for taxi {taxi_id}: {e}")
            return {}
