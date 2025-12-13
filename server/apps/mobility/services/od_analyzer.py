"""
============================================================================
Origin-Destination Analysis Service using osmnx, networkx, and h3
============================================================================
Description: Enhanced OD analysis using spatial network analysis and geospatial indexing
            for route analysis, network connectivity, and spatial aggregation
============================================================================
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

# Spatial analysis libraries
try:
    import osmnx as ox
    import networkx as nx
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    logging.warning("osmnx not available")

try:
    import h3
    H3_AVAILABLE = True
except ImportError:
    H3_AVAILABLE = False
    logging.warning("h3 not available")

try:
    import geopandas as gpd
    from shapely.geometry import Point, LineString, Polygon
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    logging.warning("geopandas not available")

from django.db import models
from django.contrib.gis.geos import Point, LineString
from apps.mobility.models import TDriveRawPoint, TDriveTrajectory


class ODAnalyzer:
    """
    Enhanced Origin-Destination analysis service using spatial network analysis.
    
    Features:
    - OD matrix generation and analysis
    - Route analysis using street networks
    - Spatial aggregation using H3 indexing
    - Network connectivity analysis
    """
    
    def __init__(self, h3_resolution: int = 8, 
                 network_type: str = 'drive',
                 max_route_distance_km: float = 50.0):
        """
        Initialize the OD analyzer.
        
        Args:
            h3_resolution: H3 spatial resolution (7-10 recommended for urban areas)
            network_type: OSM network type ('drive', 'walk', 'bike', 'all')
            max_route_distance_km: Maximum distance for route calculation
        """
        self.h3_resolution = h3_resolution
        self.network_type = network_type
        self.max_route_distance = max_route_distance_km
        self.street_network = None
        
        if not OSMNX_AVAILABLE:
            logging.warning("osmnx not available - network analysis disabled")
        
        if not H3_AVAILABLE:
            logging.warning("h3 not available - spatial indexing disabled")
    
    def analyze_od_patterns(self, taxi_ids: List[str], 
                          start_date: datetime, 
                          end_date: datetime) -> Dict:
        """
        Analyze Origin-Destination patterns for multiple taxis.
        
        Args:
            taxi_ids: List of taxi identifiers
            start_date: Start of analysis period
            end_date: End of analysis period
        
        Returns:
            Dictionary with OD analysis results
        """
        # Query trajectories
        trajectories = TDriveTrajectory.objects.filter(
            taxi_id__in=taxi_ids,
            trajectory_date__range=(start_date, end_date)
        ).select_related()
        
        if not trajectories:
            return {"error": "No trajectories found for the specified criteria"}
        
        od_data = []
        
        for traj in trajectories:
            # Extract OD information from trajectory
            od_info = self._extract_od_from_trajectory(traj)
            if od_info:
                od_data.append(od_info)
        
        if not od_data:
            return {"error": "No valid OD pairs extracted"}
        
        # Create OD matrix
        od_matrix = self._create_od_matrix(od_data)
        
        # Analyze spatial patterns
        spatial_analysis = self._analyze_spatial_patterns(od_data)
        
        return {
            'taxi_count': len(taxi_ids),
            'trajectory_count': len(trajectories),
            'od_pair_count': len(od_data),
            'od_matrix': od_matrix,
            'spatial_analysis': spatial_analysis,
            'od_data': od_data
        }
    
    def _extract_od_from_trajectory(self, trajectory: TDriveTrajectory) -> Optional[Dict]:
        """
        Extract Origin-Destination information from a trajectory.
        
        Args:
            trajectory: TDriveTrajectory object
        
        Returns:
            OD information dictionary or None if invalid
        """
        try:
            # Get raw points for this trajectory
            points = TDriveRawPoint.objects.filter(
                taxi_id=trajectory.taxi_id,
                timestamp__date=trajectory.trajectory_date,
                is_valid=True
            ).order_by('timestamp')
            
            if len(points) < 2:
                return None
            
            # Extract origin and destination
            origin = points.first()
            destination = points.last()
            
            od_info = {
                'taxi_id': trajectory.taxi_id,
                'date': trajectory.trajectory_date,
                'origin_lat': origin.latitude,
                'origin_lng': origin.longitude,
                'destination_lat': destination.latitude,
                'destination_lng': destination.longitude,
                'departure_time': origin.timestamp,
                'arrival_time': destination.timestamp,
                'trip_duration_minutes': (destination.timestamp - origin.timestamp).total_seconds() / 60,
                'point_count': len(points)
            }
            
            # Add H3 indices if available
            if H3_AVAILABLE:
                od_info['origin_h3'] = h3.geo_to_h3(
                    origin.latitude, origin.longitude, self.h3_resolution
                )
                od_info['destination_h3'] = h3.geo_to_h3(
                    destination.latitude, destination.longitude, self.h3_resolution
                )
            
            return od_info
        
        except Exception as e:
            logging.error(f"Error extracting OD from trajectory {trajectory.id}: {e}")
            return None
    
    def _create_od_matrix(self, od_data: List[Dict]) -> Dict:
        """
        Create Origin-Destination matrix from OD data.
        
        Args:
            od_data: List of OD information dictionaries
        
        Returns:
            OD matrix with counts and statistics
        """
        if not od_data:
            return {}
        
        # Create DataFrame
        df = pd.DataFrame(od_data)
        
        # Group by origin and destination H3 cells
        if H3_AVAILABLE and 'origin_h3' in df.columns and 'destination_h3' in df.columns:
            od_matrix = df.groupby(['origin_h3', 'destination_h3']).agg({
                'taxi_id': 'count',
                'trip_duration_minutes': ['mean', 'std'],
                'point_count': 'mean'
            }).reset_index()
            
            # Flatten column names
            od_matrix.columns = ['origin_h3', 'destination_h3', 'trip_count', 
                               'avg_duration', 'std_duration', 'avg_points']
            
            return od_matrix.to_dict('records')
        
        else:
            # Fallback: simple count by origin/destination coordinates (rounded)
            df['origin_rounded'] = df.apply(
                lambda x: f"{x['origin_lat']:.3f},{x['origin_lng']:.3f}", axis=1
            )
            df['destination_rounded'] = df.apply(
                lambda x: f"{x['destination_lat']:.3f},{x['destination_lng']:.3f}", axis=1
            )
            
            od_matrix = df.groupby(['origin_rounded', 'destination_rounded']).agg({
                'taxi_id': 'count',
                'trip_duration_minutes': ['mean', 'std']
            }).reset_index()
            
            od_matrix.columns = ['origin', 'destination', 'trip_count', 
                               'avg_duration', 'std_duration']
            
            return od_matrix.to_dict('records')
    
    def _analyze_spatial_patterns(self, od_data: List[Dict]) -> Dict:
        """
        Analyze spatial patterns in OD data.
        
        Args:
            od_data: List of OD information dictionaries
        
        Returns:
            Spatial analysis results
        """
        if not od_data:
            return {}
        
        df = pd.DataFrame(od_data)
        
        analysis = {
            'total_trips': len(df),
            'unique_origins': df[['origin_lat', 'origin_lng']].drop_duplicates().shape[0],
            'unique_destinations': df[['destination_lat', 'destination_lng']].drop_duplicates().shape[0],
            'avg_trip_duration_minutes': df['trip_duration_minutes'].mean(),
            'median_trip_duration_minutes': df['trip_duration_minutes'].median(),
            'trip_distance_stats': self._calculate_trip_distances(df)
        }
        
        # Add H3-based analysis if available
        if H3_AVAILABLE and 'origin_h3' in df.columns:
            analysis.update(self._analyze_h3_patterns(df))
        
        return analysis
    
    def _calculate_trip_distances(self, df: pd.DataFrame) -> Dict:
        """Calculate trip distance statistics using Haversine formula."""
        distances = []
        
        for _, row in df.iterrows():
            # Haversine distance calculation
            lat1, lon1 = np.radians(row['origin_lat']), np.radians(row['origin_lng'])
            lat2, lon2 = np.radians(row['destination_lat']), np.radians(row['destination_lng'])
            
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            distance_km = 6371 * c
            
            distances.append(distance_km)
        
        return {
            'avg_distance_km': np.mean(distances) if distances else 0,
            'median_distance_km': np.median(distances) if distances else 0,
            'max_distance_km': np.max(distances) if distances else 0,
            'min_distance_km': np.min(distances) if distances else 0
        }
    
    def _analyze_h3_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze spatial patterns using H3 indexing."""
        h3_analysis = {}
        
        try:
            # Most frequent origins and destinations
            top_origins = df['origin_h3'].value_counts().head(10).to_dict()
            top_destinations = df['destination_h3'].value_counts().head(10).to_dict()
            
            # OD flow analysis
            od_flows = df.groupby(['origin_h3', 'destination_h3']).size().reset_index(name='count')
            top_flows = od_flows.nlargest(10, 'count').to_dict('records')
            
            h3_analysis.update({
                'top_origins': top_origins,
                'top_destinations': top_destinations,
                'top_flows': top_flows,
                'h3_resolution': self.h3_resolution
            })
        
        except Exception as e:
            logging.error(f"Error in H3 pattern analysis: {e}")
        
        return h3_analysis
    
    def load_street_network(self, center_point: Tuple[float, float], 
                          network_distance: float = 5000) -> bool:
        """
        Load street network for a specific area.
        
        Args:
            center_point: (latitude, longitude) center point
            network_distance: Distance in meters to extend the network
        
        Returns:
            True if network loaded successfully, False otherwise
        """
        if not OSMNX_AVAILABLE:
            logging.error("osmnx not available - cannot load street network")
            return False
        
        try:
            self.street_network = ox.graph_from_point(
                center_point,
                dist=network_distance,
                network_type=self.network_type,
                simplify=True
            )
            
            # Add edge speeds and travel times
            self.street_network = ox.add_edge_speeds(self.street_network)
            self.street_network = ox.add_edge_travel_times(self.street_network)
            
            logging.info(f"Street network loaded with {len(self.street_network)} nodes")
            return True
        
        except Exception as e:
            logging.error(f"Error loading street network: {e}")
            self.street_network = None
            return False
    
    def calculate_optimal_routes(self, origins: List[Tuple[float, float]], 
                               destinations: List[Tuple[float, float]]) -> List[Dict]:
        """
        Calculate optimal routes between origins and destinations.
        
        Args:
            origins: List of (lat, lng) origin points
            destinations: List of (lat, lng) destination points
        
        Returns:
            List of route information dictionaries
        """
        if not OSMNX_AVAILABLE or self.street_network is None:
            return [{"error": "Street network not available"}]
        
        routes = []
        
        try:
            for i, (origin, destination) in enumerate(zip(origins, destinations)):
                # Find nearest network nodes
                orig_node = ox.distance.nearest_nodes(self.street_network, origin[1], origin[0])
                dest_node = ox.distance.nearest_nodes(self.street_network, destination[1], destination[0])
                
                # Calculate shortest path
                try:
                    route = nx.shortest_path(
                        self.street_network, 
                        orig_node, 
                        dest_node, 
                        weight='travel_time'
                    )
                    
                    # Calculate route metrics
                    route_length = nx.shortest_path_length(
                        self.street_network, 
                        orig_node, 
                        dest_node, 
                        weight='length'
                    )
                    
                    route_time = nx.shortest_path_length(
                        self.street_network, 
                        orig_node, 
                        dest_node, 
                        weight='travel_time'
                    )
                    
                    routes.append({
                        'origin': origin,
                        'destination': destination,
                        'route_nodes': route,
                        'distance_meters': route_length,
                        'travel_time_seconds': route_time,
                        'success': True
                    })
                
                except nx.NetworkXNoPath:
                    routes.append({
                        'origin': origin,
                        'destination': destination,
                        'error': "No path found",
                        'success': False
                    })
        
        except Exception as e:
            logging.error(f"Error calculating routes: {e}")
        
        return routes
    
    def aggregate_od_by_h3(self, od_data: List[Dict]) -> Dict:
        """
        Aggregate OD data using H3 spatial indexing.
        
        Args:
            od_data: List of OD information dictionaries
        
        Returns:
            Aggregated OD data by H3 cells
        """
        if not H3_AVAILABLE:
            return {"error": "H3 not available"}
        
        df = pd.DataFrame(od_data)
        
        # Add H3 indices if not present
        if 'origin_h3' not in df.columns:
            df['origin_h3'] = df.apply(
                lambda x: h3.geo_to_h3(x['origin_lat'], x['origin_lng'], self.h3_resolution), 
                axis=1
            )
        
        if 'destination_h3' not in df.columns:
            df['destination_h3'] = df.apply(
                lambda x: h3.geo_to_h3(x['destination_lat'], x['destination_lng'], self.h3_resolution), 
                axis=1
            )
        
        # Aggregate by H3 cells
        origin_aggregation = df.groupby('origin_h3').agg({
            'taxi_id': 'count',
            'trip_duration_minutes': 'mean'
        }).rename(columns={'taxi_id': 'departure_count', 'trip_duration_minutes': 'avg_departure_duration'})
        
        destination_aggregation = df.groupby('destination_h3').agg({
            'taxi_id': 'count',
            'trip_duration_minutes': 'mean'
        }).rename(columns={'taxi_id': 'arrival_count', 'trip_duration_minutes': 'avg_arrival_duration'})
        
        # Combine aggregations
        h3_aggregation = pd.concat([origin_aggregation, destination_aggregation], axis=1)
        h3_aggregation = h3_aggregation.fillna(0)
        
        # Calculate net flow
        h3_aggregation['net_flow'] = h3_aggregation['arrival_count'] - h3_aggregation['departure_count']
        
        return h3_aggregation.reset_index().to_dict('records')
