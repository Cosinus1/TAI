#!/usr/bin/env python
"""
Script to import OpenStreetMap data for Points of Interest.
"""

import os
import sys
import django
import requests
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.poi.models import POI
from utils.geo_utils import create_point_from_coordinates


def fetch_osm_data(bbox, poi_types=None):
    """
    Fetch POI data from OpenStreetMap Overpass API.
    
    Args:
        bbox: Tuple of (min_lon, min_lat, max_lon, max_lat)
        poi_types: List of OSM amenity types to fetch
    
    Returns:
        List of POI data
    """
    if poi_types is None:
        poi_types = ['restaurant', 'cafe', 'bar', 'pub', 'bank', 'pharmacy', 
                    'hospital', 'school', 'university', 'library', 'cinema', 
                    'theatre', 'museum', 'hotel', 'fuel', 'parking']
    
    overpass_query = f"""
    [out:json][timeout:25];
    (
        node["amenity"~"{'|'.join(poi_types)}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
        way["amenity"~"{'|'.join(poi_types)}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
        relation["amenity"~"{'|'.join(poi_types)}"]({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]});
    );
    out center;
    """
    
    try:
        response = requests.post(
            'https://overpass-api.de/api/interpreter',
            data=overpass_query,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching OSM data: {e}")
        return None


def process_osm_data(osm_data):
    """
    Process OSM data and create POI objects.
    
    Args:
        osm_data: Raw OSM API response
    
    Returns:
        Number of POIs created
    """
    if not osm_data or 'elements' not in osm_data:
        print("No data found in OSM response")
        return 0
    
    created_count = 0
    
    for element in osm_data['elements']:
        try:
            # Extract coordinates
            if element['type'] == 'node':
                lat = element.get('lat')
                lon = element.get('lon')
            elif element['type'] in ['way', 'relation']:
                if 'center' in element:
                    lat = element['center'].get('lat')
                    lon = element['center'].get('lon')
                else:
                    continue
            else:
                continue
            
            if not lat or not lon:
                continue
            
            # Extract POI information
            tags = element.get('tags', {})
            name = tags.get('name', 'Unnamed POI')
            amenity = tags.get('amenity', 'unknown')
            address = tags.get('addr:street', '')
            
            # Create POI object
            poi = POI(
                name=name,
                category=amenity,
                latitude=lat,
                longitude=lon,
                address=address,
                osm_id=element['id'],
                osm_type=element['type'],
                tags=tags
            )
            poi.save()
            created_count += 1
            
        except Exception as e:
            print(f"Error processing element {element.get('id')}: {e}")
            continue
    
    return created_count


def main():
    """Main function to import OSM data."""
    # Example: Paris bounding box
    paris_bbox = (2.2241, 48.8156, 2.4699, 48.9022)
    
    print("Fetching OSM data...")
    osm_data = fetch_osm_data(paris_bbox)
    
    if osm_data:
        print(f"Found {len(osm_data['elements'])} elements in OSM response")
        created_count = process_osm_data(osm_data)
        print(f"Successfully created {created_count} POIs")
    else:
        print("Failed to fetch OSM data")


if __name__ == '__main__':
    main()
