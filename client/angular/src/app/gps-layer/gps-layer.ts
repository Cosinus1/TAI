// client/angular/src/app/gps-layer/gps-layer.ts
import { Component, Input, inject, OnDestroy, effect } from '@angular/core';
import * as L from 'leaflet';
import { Gps } from '../services/gps';
import { Mode } from '../services/mode';
import { Bbox, GeoJsonFeature } from '../interfaces/gps';

@Component({
  selector: 'app-gps-layer',
  imports: [],
  templateUrl: './gps-layer.html',
  styleUrl: './gps-layer.scss',
})
export class GpsLayer implements OnDestroy {
  @Input({ required: true }) map!: L.Map;
  @Input() selectedEntity: string | null = null;
  @Input() datasetId?: string; // Optional: specify which dataset to use

  private gps = inject(Gps);
  private mode = inject(Mode);

  private layer = L.layerGroup();
  private moveListenerAttached = false;
  private currentDatasetId?: string;

  private onMoveEnd = () => {
    console.log('[GpsLayer] map moveend');
    if (!this.map) return;
    this.loadPointsInViewport();
  };

  constructor() {
    // Initialize dataset
    this.initializeDataset();

    effect(() => {
      const currentMode = this.mode.mode();
      console.log('[GpsLayer] effect triggered, mode =', currentMode);
      
      if (this.mode.mode() !== 'gps' || !this.map) {
        console.log('[GpsLayer] detach layer');
        this.detach();
        return;
      }

      console.log('[GpsLayer] attach layer to map');
      this.layer.addTo(this.map);

      if (!this.moveListenerAttached) {
        console.log('[GpsLayer] attach moveend listener');
        this.map.on('moveend', this.onMoveEnd);
        this.moveListenerAttached = true;
      }

      this.loadPointsInViewport();
    });
  }

  /**
   * Initialize the dataset to use
   */
  private initializeDataset(): void {
    // If dataset ID is provided, use it
    if (this.datasetId) {
      this.currentDatasetId = this.datasetId;
      return;
    }

    // Otherwise, try to get the T-Drive dataset for backward compatibility
    this.gps.getTDriveDataset().subscribe({
      next: dataset => {
        console.log('[GpsLayer] Using dataset:', dataset.name);
        this.currentDatasetId = dataset.id;
        
        // Reload points if we're in GPS mode
        if (this.mode.mode() === 'gps' && this.map) {
          this.loadPointsInViewport();
        }
      },
      error: err => {
        console.error('[GpsLayer] Failed to get default dataset:', err);
        // Continue without dataset filter - will show all points
      }
    });
  }

  private loadPointsInViewport(limit = 1000) {
    // Load points for specific entity (taxi)
    if (this.selectedEntity) {
      console.log('[GpsLayer] load points for entity', this.selectedEntity);
      
      this.gps.getPointsByEntity(this.selectedEntity, {
        dataset: this.currentDatasetId,
        limit: limit
      }).subscribe({
        next: resp => {
          console.log('[GpsLayer] Response for entity:', resp);
          
          // FIXED: Handle paginated response
          const points = resp.results || [];
          const features = this.convertPointsToFeatures(points);
          console.log('[GpsLayer] features for entity', features.length);
          this.render(features);
        },
        error: err => console.error('[GpsLayer] Error loading entity points:', err),
      });
      return;
    }

    // Load points in bounding box
    const b = this.map.getBounds();
    const bbox: Bbox = {
      minLon: b.getWest(),
      maxLon: b.getEast(),
      minLat: b.getSouth(),
      maxLat: b.getNorth(),
    };

    console.log('[GpsLayer] request bbox', bbox);

    this.gps.getPointsInBbox(bbox, {
      dataset: this.currentDatasetId,
      limit: limit,
      only_valid: true
    }).subscribe({
      next: resp => {
        console.log('[GpsLayer] raw response:', resp);

        // FIXED: Safely extract features from response
        let features: GeoJsonFeature[] = [];
        
        if (resp && typeof resp === 'object') {
          if ('features' in resp && Array.isArray(resp.features)) {
            // Standard GeoJSON FeatureCollection
            features = resp.features;
          } else if ('results' in resp && Array.isArray(resp.results)) {
            // Paginated response with results array
            features = this.convertPointsToFeatures(resp.results);
          } else if (Array.isArray(resp)) {
            // Direct array of features
            features = resp;
          }
        }
        
        console.log('[GpsLayer] extracted features count:', features.length);
        
        this.render(features);
      },
      error: err => {
        console.error('[GpsLayer] Error loading bbox points:', err);
        // Clear layer on error
        this.layer.clearLayers();
      },
    });
  }

  /**
   * Convert GpsPoint[] to GeoJsonFeature[] for rendering
   */
  private convertPointsToFeatures(points: any[]): GeoJsonFeature[] {
    if (!Array.isArray(points)) {
      console.warn('[GpsLayer] convertPointsToFeatures received non-array:', points);
      return [];
    }

    return points.map(point => ({
      id: point.id,
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [point.longitude, point.latitude]
      },
      properties: {
        entity_id: point.entity_id,
        timestamp: point.timestamp,
        longitude: point.longitude,
        latitude: point.latitude,
        is_valid: point.is_valid,
        speed: point.speed,
        heading: point.heading,
        dataset_name: point.dataset_name
      }
    }));
  }

  private render(features: GeoJsonFeature[]) {
    console.log('[GpsLayer] render called with', features.length, 'features');

    this.layer.clearLayers();

    // FIXED: Ensure features is an array
    if (!Array.isArray(features)) {
      console.error('[GpsLayer] features is not an array:', features);
      return;
    }

    let rendered = 0;

    for (const f of features) {
      // FIXED: Handle both feature formats
      const props = f.properties;

      if (!props) {
        console.warn('[GpsLayer] feature without properties', f);
        continue;
      }

      let lat: number;
      let lng: number;

      // Try to get coordinates from geometry first
      if (f.geometry && f.geometry.type === 'Point' && f.geometry.coordinates) {
        lng = f.geometry.coordinates[0];
        lat = f.geometry.coordinates[1];
      } else if (props.latitude != null && props.longitude != null) {
        // Fallback to properties
        lat = props.latitude;
        lng = props.longitude;
      } else {
        console.warn('[GpsLayer] invalid coords', props);
        continue;
      }

      // Validate coordinates
      if (lat == null || lng == null || isNaN(lat) || isNaN(lng)) {
        console.warn('[GpsLayer] invalid coordinate values', { lat, lng });
        continue;
      }

      // Color based on validity
      const fillColor = props.is_valid ? '#3388ff' : '#ff6b6b';

      const marker = L.circleMarker([lat, lng], {
        radius: 5,
        fillColor: fillColor,
        color: '#fff',
        weight: 1,
        fillOpacity: 0.8,
      });

      // Build popup content
      let popupContent = `
        <strong>Entity: ${props.entity_id}</strong><br/>
        <strong>Coords:</strong> ${lat.toFixed(5)}, ${lng.toFixed(5)}<br/>
        <strong>Time:</strong> ${new Date(props.timestamp).toLocaleString()}<br/>
      `;

      if (props.speed != null) {
        popupContent += `<strong>Speed:</strong> ${props.speed.toFixed(1)} km/h<br/>`;
      }

      if (props.heading != null) {
        popupContent += `<strong>Heading:</strong> ${props.heading.toFixed(0)}°<br/>`;
      }

      if (props.dataset_name) {
        popupContent += `<small>Dataset: ${props.dataset_name}</small>`;
      }

      marker.bindPopup(popupContent);

      marker.addTo(this.layer);
      rendered++;
    }
    console.log(`[GpsLayer] markers rendered: ${rendered}`);
  }

  private detach() {
    console.log('[GpsLayer] detach');

    if (this.moveListenerAttached) {
      this.map.off('moveend', this.onMoveEnd);
      this.moveListenerAttached = false;
    }
    this.layer.clearLayers();
    this.layer.remove();
  }

  ngOnDestroy(): void {
    console.log('[GpsLayer] destroy');
    this.detach();
  }
}