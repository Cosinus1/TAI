// client/angular/src/app/map/layers/gps-layer.ts
import { Injectable, effect, inject } from '@angular/core';
import * as L from 'leaflet';
import { Gps } from '../services/gps';
import { Mode } from '../services/mode';
import { GeometryParser } from '../services/geometry-parser';

interface GeoJSONFeature {
  type: 'Feature';
  geometry: {
    type: string;
    coordinates: number[] | number[][];
  };
  properties?: {
    entity_id?: string;
    timestamp?: string;
    speed?: number;
    trajectory_date?: string;
    duration_seconds?: number;
    total_distance_meters?: number;
    avg_speed_kmh?: number;
    max_speed_kmh?: number;
    point_count?: number;
  };
}

@Injectable()
export class GpsLayer {
  private gps = inject(Gps);
  private mode = inject(Mode);
  private geometryParser = inject(GeometryParser);
  
  private map!: L.Map;
  private markersLayer!: L.LayerGroup;
  private trajectoriesLayer!: L.LayerGroup;
  
  private currentDatasetId: string | null = null;
  private currentEntityId: string | null = null;
  
  constructor() {
    // React to mode changes
    effect(() => {
      const currentMode = this.mode.mode();
      console.log('[GpsLayer] Mode changed to:', currentMode);
      this.refreshLayers();
    });
  }
  
  initialize(map: L.Map) {
    this.map = map;
    this.markersLayer = L.layerGroup().addTo(map);
    this.trajectoriesLayer = L.layerGroup().addTo(map);
  }
  
  setDataset(datasetId: string | null) {
    this.currentDatasetId = datasetId;
    this.currentEntityId = null;
    this.refreshLayers();
  }
  
  setEntity(entityId: string | null) {
    this.currentEntityId = entityId;
    this.refreshLayers();
  }
  
  private refreshLayers() {
    this.clearLayers();
    
    if (!this.currentDatasetId) {
      return;
    }
    
    const currentMode = this.mode.mode();
    
    if (currentMode === 'gps') {
      this.loadGPSPoints();
    } else if (currentMode === 'trajectory') {
      this.loadTrajectories();
    }
  }
  
  private loadGPSPoints() {
    console.log('[GpsLayer] Loading GPS points for dataset:', this.currentDatasetId);
    
    const params: any = {
      dataset: this.currentDatasetId!,
      page_size: 1000,
      format: 'geojson'
    };
    
    if (this.currentEntityId) {
      params.entity_id = this.currentEntityId;
    }
    
    this.gps.getPoints(params).subscribe({
      next: (response: any) => {
        console.log('[GpsLayer] Received GeoJSON response:', response);
        
        // Response is already GeoJSON from backend
        const features = response.features;
        
        console.log('[GpsLayer] Parsed features:', features.length);
        
        let markerCount = 0;
        features.forEach((feature: GeoJSONFeature) => {
          if (feature.geometry.type === 'Point') {
            const coords = feature.geometry.coordinates as number[];
            const [lng, lat] = coords;
            const marker = L.circleMarker([lat, lng], {
              radius: 6,
              fillColor: '#3b82f6',
              color: '#fff',
              weight: 2,
              opacity: 1,
              fillOpacity: 0.8
            });
            
            if (feature.properties) {
              marker.bindPopup(`
                <strong>Entity:</strong> ${feature.properties.entity_id}<br>
                <strong>Time:</strong> ${feature.properties.timestamp}<br>
                <strong>Speed:</strong> ${feature.properties.speed || 'N/A'} km/h
              `);
            }
            
            marker.addTo(this.markersLayer);
            markerCount++;
          }
        });
        
        console.log('[GpsLayer] Rendered:', markerCount, 'markers');
      },
      error: (err) => console.error('[GpsLayer] Failed to load points:', err)
    });
  }
  
  private loadTrajectories() {
    console.log('[GpsLayer] Loading trajectories for dataset:', this.currentDatasetId);
    
    const params: any = {
      dataset: this.currentDatasetId!,
      page_size: 1000,
      format: 'geojson'
    };
    
    if (this.currentEntityId) {
      params.entity_id = this.currentEntityId;
    }
    
    this.gps.getTrajectories(params).subscribe({
      next: (response: any) => {
        console.log('[GpsLayer] Received trajectories GeoJSON:', response);
        
        // Response is already GeoJSON from backend
        const features = response.features;
        
        console.log('[GpsLayer] Parsed trajectory features:', features.length);
        
        let trajectoryCount = 0;
        features.forEach((feature: GeoJSONFeature) => {
          if (feature.geometry.type === 'LineString') {
            const coords = feature.geometry.coordinates as number[][];
            const latLngs = coords.map(
              (coord: number[]) => [coord[1], coord[0]] as [number, number]
            );
            
            const polyline = L.polyline(latLngs, {
              color: this.getEntityColor(feature.properties?.entity_id || 'unknown'),
              weight: 3,
              opacity: 0.7
            });
            
            if (feature.properties) {
              const distanceKm = (feature.properties.total_distance_meters || 0) / 1000;
              const durationMin = Math.round((feature.properties.duration_seconds || 0) / 60);
              
              polyline.bindPopup(`
                <strong>Entity:</strong> ${feature.properties.entity_id}<br>
                <strong>Date:</strong> ${feature.properties.trajectory_date}<br>
                <strong>Duration:</strong> ${durationMin} min<br>
                <strong>Distance:</strong> ${distanceKm.toFixed(2)} km<br>
                <strong>Points:</strong> ${feature.properties.point_count}<br>
                <strong>Avg Speed:</strong> ${feature.properties.avg_speed_kmh?.toFixed(1) || 'N/A'} km/h<br>
                <strong>Max Speed:</strong> ${feature.properties.max_speed_kmh?.toFixed(1) || 'N/A'} km/h
              `);
            }
            
            polyline.addTo(this.trajectoriesLayer);
            trajectoryCount++;
          }
        });
        
        console.log('[GpsLayer] Rendered:', trajectoryCount, 'trajectories');
      },
      error: (err) => console.error('[GpsLayer] Failed to load trajectories:', err)
    });
  }
  
  private getEntityColor(entityId: string): string {
    // Simple hash function to generate consistent colors per entity
    let hash = 0;
    for (let i = 0; i < entityId.length; i++) {
      hash = entityId.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    const hue = Math.abs(hash % 360);
    return `hsl(${hue}, 70%, 50%)`;
  }
  
  private clearLayers() {
    this.markersLayer.clearLayers();
    this.trajectoriesLayer.clearLayers();
  }
  
  destroy() {
    this.clearLayers();
    this.markersLayer.remove();
    this.trajectoriesLayer.remove();
  }
}