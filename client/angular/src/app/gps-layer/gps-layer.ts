// client/angular/src/app/gps-layer/gps-layer.ts
import { Component, Input, inject, OnDestroy, effect, OnChanges, SimpleChanges } from '@angular/core';
import * as L from 'leaflet';
import { Gps } from '../services/gps';
import { Mode } from '../services/mode';
import { Bbox, GeoJsonFeature } from '../interfaces/gps';

// Entity type colors
const ENTITY_COLORS: { [key: string]: string } = {
  'bus': '#FF5722',
  'bike': '#4CAF50',
  'car': '#2196F3',
  'taxi': '#FFC107',
  'unknown': '#9E9E9E'
};

@Component({
  selector: 'app-gps-layer',
  standalone: true,
  imports: [],
  templateUrl: './gps-layer.html',
  styleUrl: './gps-layer.scss',
})
export class GpsLayer implements OnDestroy, OnChanges {
  @Input({ required: true }) map!: L.Map;
  @Input() selectedEntity: string | null = null;
  @Input() datasetId?: string;
  @Input() entityTypeFilter?: string | null = null;
  @Input() minSpeedFilter?: number | null = null;
  @Input() maxSpeedFilter?: number | null = null;

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

  ngOnChanges(changes: SimpleChanges): void {
    // Reload when filters change
    if (changes['entityTypeFilter'] || changes['minSpeedFilter'] || changes['maxSpeedFilter'] || changes['datasetId']) {
      if (this.datasetId) {
        this.currentDatasetId = this.datasetId;
      }
      if (this.mode.mode() === 'gps' && this.map) {
        this.loadPointsInViewport();
      }
    }
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
          const points = resp.results || [];
          const features = this.convertPointsToFeatures(points);
          console.log('[GpsLayer] features for entity', features.length);
          this.render(features);
        },
        error: err => console.error('[GpsLayer] Error loading entity points:', err),
      });
      return;
    }

    // Load points in bounding box with filters
    const b = this.map.getBounds();
    const bbox: Bbox = {
      minLon: b.getWest(),
      maxLon: b.getEast(),
      minLat: b.getSouth(),
      maxLat: b.getNorth(),
    };

    console.log('[GpsLayer] request bbox', bbox, 'entityType:', this.entityTypeFilter);

    this.gps.getPointsInBbox(bbox, {
      dataset: this.currentDatasetId,
      entity_type: this.entityTypeFilter || undefined,
      limit: limit,
      only_valid: true
    }).subscribe({
      next: resp => {
        console.log('[GpsLayer] raw response:', resp);

        let features: GeoJsonFeature[] = [];
        
        if (resp && typeof resp === 'object') {
          if ('features' in resp && Array.isArray(resp.features)) {
            features = resp.features;
          } else if ('results' in resp && Array.isArray(resp.results)) {
            features = this.convertPointsToFeatures(resp.results);
          } else if (Array.isArray(resp)) {
            features = resp;
          }
        }
        
        // Apply client-side speed filtering if needed
        /*if (this.minSpeedFilter !== null || this.maxSpeedFilter !== null) {
          features = features.filter(f => {
            const speed = f.properties?.speed;
            if (speed === null || speed === undefined) return true;
            if (this.minSpeedFilter !== null && speed < this.minSpeedFilter) return false;
            if (this.maxSpeedFilter !== null && speed > this.maxSpeedFilter) return false;
            return true;
          });
        }*/
        
        console.log('[GpsLayer] extracted features count:', features.length);
        
        this.render(features);
      },
      error: err => {
        console.error('[GpsLayer] Error loading bbox points:', err);
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
        dataset_name: point.dataset_name,
        extra_attributes: point.extra_attributes
      }
    }));
  }

  /**
   * Get entity type from entity_id or extra_attributes
   */
  private getEntityType(props: any): string {
    // Check extra_attributes first
    if (props.extra_attributes?.entity_type) {
      return props.extra_attributes.entity_type;
    }
    
    // Infer from entity_id prefix
    const entityId = props.entity_id || '';
    for (const prefix of ['bus', 'bike', 'car', 'taxi']) {
      if (entityId.startsWith(prefix)) {
        return prefix;
      }
    }
    
    return 'unknown';
  }

  /**
   * Get color for entity type
   */
  private getEntityColor(entityType: string): string {
    return ENTITY_COLORS[entityType] || ENTITY_COLORS['unknown'];
  }

  private render(features: GeoJsonFeature[]) {
    console.log('[GpsLayer] render called with', features.length, 'features');

    this.layer.clearLayers();

    if (!Array.isArray(features)) {
      console.error('[GpsLayer] features is not an array:', features);
      return;
    }

    let rendered = 0;

    for (const f of features) {
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

      // Determine entity type and color
      const entityType = this.getEntityType(props);
      const fillColor = props.is_valid ? this.getEntityColor(entityType) : '#ff6b6b';

      const marker = L.circleMarker([lat, lng], {
        radius: 5,
        fillColor: fillColor,
        color: '#fff',
        weight: 1,
        fillOpacity: 0.8,
      });

      // Build popup content with entity type
      let popupContent = `
        <strong>Entity: ${props.entity_id}</strong><br/>
        <strong>Type:</strong> ${entityType}<br/>
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

  /**
   * Public method to force reload
   */
  reload() {
    if (this.mode.mode() === 'gps' && this.map) {
      this.loadPointsInViewport();
    }
  }

  ngOnDestroy(): void {
    console.log('[GpsLayer] destroy');
    this.detach();
  }
}