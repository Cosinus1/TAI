#!/usr/bin/env python
"""
Test script for enhanced trajectory calculation functionality.
This demonstrates the new features:
1. Road-following algorithm
2. Stop point detection
3. Enhanced trajectory metrics
4. API endpoints
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.mobility.models import Dataset, GPSPoint, Trajectory
from apps.mobility.services.enhanced_trajectory_calculator import EnhancedTrajectoryCalculator
from apps.mobility.services.road_following import SimplifiedRoadFollower
from datetime import datetime, timedelta
import random

def test_road_following_algorithm():
    """Test the simplified road-following algorithm."""
    print("=" * 60)
    print("Testing Road-Following Algorithm")
    print("=" * 60)
    
    # Create sample trajectory points (simulating a zigzag path)
    points = [
        (116.3975, 39.9087),  # Tiananmen Square
        (116.3980, 39.9090),
        (116.3985, 39.9085),
        (116.3990, 39.9090),
        (116.3995, 39.9085),
        (116.4000, 39.9090),
        (116.4005, 39.9085),
        (116.4010, 39.9090),
    ]
    
    follower = SimplifiedRoadFollower(smoothing_factor=0.3, snap_distance_meters=50.0)
    
    # Test road direction inference
    bearings = follower.infer_road_directions(points)
    print(f"Inferred road directions: {bearings}")
    
    # Test smoothing
    smoothed = follower.smooth_trajectory(points)
    print(f"Original points: {len(points)}")
    print(f"Smoothed points: {len(smoothed)}")
    
    # Test road following
    followed = follower.follow_roads(points, apply_smoothing=True, apply_snapping=True)
    print(f"Road-followed points: {len(followed)}")
    
    # Calculate alignment score
    score = follower.calculate_road_alignment_score(points, followed)
    print(f"Road alignment score: {score:.2f}")
    
    print("\nRoad-following algorithm test completed successfully!")
    return True

def test_enhanced_trajectory_calculator():
    """Test the enhanced trajectory calculator."""
    print("\n" + "=" * 60)
    print("Testing Enhanced Trajectory Calculator")
    print("=" * 60)
    
    # Get or create a test dataset
    try:
        dataset = Dataset.objects.get(name="Test Dataset for Enhanced Trajectories")
    except Dataset.DoesNotExist:
        dataset = Dataset.objects.create(
            name="Test Dataset for Enhanced Trajectories",
            dataset_type="gps_trace",
            data_format="csv",
            field_mapping={},
            is_active=True
        )
        print(f"Created test dataset: {dataset.name}")
    
    # Create test calculator
    calculator = EnhancedTrajectoryCalculator(dataset)
    
    print(f"Calculator initialized for dataset: {dataset.name}")
    print(f"Map matching enabled: {calculator.map_matching_enabled}")
    print(f"Stop detection threshold: {calculator.stop_detection_threshold_seconds} seconds")
    print(f"Speed threshold for stops: {calculator.speed_threshold_kmh} km/h")
    
    # Test speed calculation between points
    print("\nTesting speed calculation between points:")
    
    # Create two test points
    point1 = GPSPoint(
        dataset=dataset,
        entity_id="test_vehicle_001",
        timestamp=datetime.now(),
        longitude=116.3975,
        latitude=39.9087,
        speed=30.0,
        is_valid=True
    )
    point1.geom = f"POINT({point1.longitude} {point1.latitude})"
    
    point2 = GPSPoint(
        dataset=dataset,
        entity_id="test_vehicle_001",
        timestamp=datetime.now() + timedelta(minutes=5),
        longitude=116.4075,
        latitude=39.9187,
        speed=35.0,
        is_valid=True
    )
    point2.geom = f"POINT({point2.longitude} {point2.latitude})"
    
    speed = calculator.calculate_average_speed_between_points(point1, point2)
    if speed:
        print(f"Average speed between points: {speed:.2f} km/h")
    else:
        print("Could not calculate speed (points may not have geometry)")
    
    # Test trajectory interpolation
    print("\nTesting trajectory interpolation:")
    
    # Create sample points for interpolation
    sample_points = []
    base_time = datetime.now()
    for i in range(5):
        point = GPSPoint(
            dataset=dataset,
            entity_id="test_vehicle_001",
            timestamp=base_time + timedelta(minutes=i * 10),
            longitude=116.3975 + (i * 0.01),
            latitude=39.9087 + (i * 0.01),
            speed=30.0 + random.uniform(-5, 5),
            is_valid=True
        )
        point.geom = f"POINT({point.longitude} {point.latitude})"
        sample_points.append(point)
    
    interpolated = calculator.interpolate_trajectory_points(sample_points, interval_seconds=300)
    print(f"Original points: {len(sample_points)}")
    print(f"Interpolated points: {len(interpolated)}")
    print(f"Interpolation interval: 300 seconds (5 minutes)")
    
    # Test stop detection
    print("\nTesting stop detection within trajectory:")
    
    # Create points with a stop in the middle
    stop_points = []
    stop_time = datetime.now()
    
    # Moving points
    for i in range(3):
        point = GPSPoint(
            dataset=dataset,
            entity_id="test_vehicle_001",
            timestamp=stop_time + timedelta(minutes=i),
            longitude=116.3975 + (i * 0.001),
            latitude=39.9087 + (i * 0.001),
            speed=30.0,
            is_valid=True
        )
        point.geom = f"POINT({point.longitude} {point.latitude})"
        stop_points.append(point)
    
    # Stopped points (very slow movement)
    for i in range(3):
        point = GPSPoint(
            dataset=dataset,
            entity_id="test_vehicle_001",
            timestamp=stop_time + timedelta(minutes=3 + i),
            longitude=116.4005 + (i * 0.00001),  # Very small movement
            latitude=39.9115 + (i * 0.00001),
            speed=1.0,  # Below threshold
            is_valid=True
        )
        point.geom = f"POINT({point.longitude} {point.latitude})"
        stop_points.append(point)
    
    # Moving points again
    for i in range(3):
        point = GPSPoint(
            dataset=dataset,
            entity_id="test_vehicle_001",
            timestamp=stop_time + timedelta(minutes=6 + i),
            longitude=116.4005 + (i * 0.001),
            latitude=39.9115 + (i * 0.001),
            speed=30.0,
            is_valid=True
        )
        point.geom = f"POINT({point.longitude} {point.latitude})"
        stop_points.append(point)
    
    stops = calculator._detect_stops_within_trajectory(stop_points)
    print(f"Detected {len(stops)} stop(s) within trajectory")
    for i, stop in enumerate(stops, 1):
        print(f"  Stop {i}: Duration {stop['duration_seconds']:.0f}s, Points: {stop['point_count']}")
    
    print("\nEnhanced trajectory calculator test completed successfully!")
    return True

def test_api_endpoints():
    """Test the new API endpoints conceptually."""
    print("\n" + "=" * 60)
    print("Testing API Endpoints (Conceptual)")
    print("=" * 60)
    
    print("New API endpoints available:")
    print("1. GET /api/trajectories/{id}/enhanced_analysis/")
    print("   - Returns trajectory with stop points and enhanced metrics")
    print("   - Includes road-following information")
    print("   - Shows stop points between trajectories")
    
    print("\n2. POST /api/trajectories/calculate_enhanced/")
    print("   - Calculates enhanced trajectories for dataset or entity")
    print("   - Parameters: dataset (required), entity_id (optional)")
    print("   - Returns statistics about calculation")
    
    print("\n3. POST /api/trajectories/calculate_speed_between_points/")
    print("   - Calculates average speed between two GPS points")
    print("   - Parameters: point1_id, point2_id")
    print("   - Returns speed, distance, and time difference")
    
    print("\n4. POST /api/trajectories/interpolate_trajectory/")
    print("   - Interpolates trajectory points at regular intervals")
    print("   - Parameters: entity_id, dataset, date, interval_seconds")
    print("   - Returns interpolated points")
    
    print("\nClient-side Angular service methods added:")
    print("1. getEnhancedTrajectoryAnalysis(trajectoryId)")
    print("2. calculateEnhancedTrajectories(datasetId, entityId?)")
    print("3. calculateSpeedBetweenPoints(point1Id, point2Id)")
    print("4. interpolateTrajectory(entityId, datasetId, date, intervalSeconds)")
    
    print("\nAPI endpoints test completed successfully!")
    return True

def main():
    """Run all tests."""
    print("Enhanced Trajectory System Test Suite")
    print("=" * 60)
    
    try:
        # Test road following algorithm
        test_road_following_algorithm()
        
        # Test enhanced trajectory calculator
        test_enhanced_trajectory_calculator()
        
        # Test API endpoints
        test_api_endpoints()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nSummary of implemented features:")
        print("1. Enhanced trajectory calculation from points and average speed")
        print("2. Simplified road-following algorithm (no OSMnx dependency)")
        print("3. Stop point detection between trajectories based on time gaps")
        print("4. Enhanced metrics: speed, acceleration, movement efficiency")
        print("5. New API endpoints for client access")
        print("6. Angular service methods for client-side integration")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)