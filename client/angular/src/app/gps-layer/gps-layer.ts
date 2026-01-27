// client/angular/src/app/gps-layer/gps-layer.ts
import {
  Component,
  Input,
  inject,
  OnDestroy,
  effect,
  OnChanges,
  SimpleChanges
} from '@angular/core';
import * as L from 'leaflet';
import { Gps } from '../services/gps';
import { Mode } from '../services/mode';
import { GeometryParser, ParsedFeature, ParsedFeatureCollection } from '../services/geometry-parser';
import { Bbox } from '../interfaces/gps';

const ENTITY_COLORS: Record<string, string> = {
  bike: '#4CAF50',
  bus: '#FF5722',
  car: '#2196F3',
  taxi: '#FFC107',
  unknown: '#9E9E9E'
};

@Component({
  selector: 'app-gps-layer',
  standalone: true,
  templateUrl: './gps-layer.html',
  styleUrl: './gps-layer.scss',
})
export class GpsLayer implements OnDestroy, OnChanges {
  @Input({ required: true }) map!: L.Map;
  @Input() selectedEntity: string | null = null;
  @Input() datasetId?: string;
  @Input() entityTypeFilter?: string | null;
  @Input() showTrajectories: boolean = true;

  private gps = inject(Gps);
  private mode = inject(Mode);
  private geometryParser = inject(GeometryParser);

  private pointsLayer = L.layerGroup();
  private trajectoriesLayer = L.layerGroup();
  private moveListenerAttached = false;
  private currentDatasetId?: string;

  private onMoveEnd = () => {
    if (this.map) this.loadPointsInViewport();
  };

  constructor() {
    effect(() => {
      if (this.mode.mode() !== 'gps' || !this.map) {
        this.detach();
        return;
      }

      this.pointsLayer.addTo(this.map);
      this.trajectoriesLayer.addTo(this.map);

      if (!this.moveListenerAttached) {
        this.map.on('moveend', this.onMoveEnd);
        this.moveListenerAttached = true;
      }

      this.loadPointsInViewport();
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['datasetId'] || changes['entityTypeFilter'] || changes['selectedEntity']) {
      this.currentDatasetId = this.datasetId;
      if (this.mode.mode() === 'gps' && this.map) {
        this.loadPointsInViewport();
      }
    }
  }

  // -------------------------
  // DATA LOADING
  // -------------------------

  private loadPointsInViewport(limit = 1000) {
    const bounds = this.map.getBounds();

    const bbox: Bbox = {
      minLon: bounds.getWest(),
      maxLon: bounds.getEast(),
      minLat: bounds.getSouth(),
      maxLat: bounds.getNorth(),
    };

    // If a specific entity is selected, load all its points
    if (this.selectedEntity) {
      this.loadEntityPoints(this.selectedEntity);
      return;
    }

    this.gps.getPointsInBbox(bbox, {
      dataset: this.currentDatasetId,
      entity_type: this.entityTypeFilter || undefined,
      limit,
      only_valid: true
    }).subscribe({
      next: resp => {
        console.log('[GpsLayer] raw response:', resp);
        
        // Parse the raw response using geometry parser
        const parsed = this.geometryParser.parseFeatureCollection(resp);
        console.log('[GpsLayer] parsed features:', parsed.count);
        
        this.render(parsed);
      },
      error: err => {
        console.error('[GpsLayer] load error', err);
        this.clearLayers();
      }
    });
  }

  private loadEntityPoints(entityId: string) {
    this.gps.getPointsByEntity(entityId, {
      dataset: this.currentDatasetId,
      limit: 5000
    }).subscribe({
      next: resp => {
        console.log('[GpsLayer] entity points raw response:', resp);
        
        // Transform paginated response to feature collection format
        const features = (resp.results || []).map((point: any, index: number) => ({
          id: point.id || index,
          type: 'Feature',
          geometry: `SRID=4326;POINT (${point.longitude} ${point.latitude})`,
          properties: point
        }));
        
        const parsed = this.geometryParser.parseFeatureCollection({ features });
        console.log('[GpsLayer] parsed entity features:', parsed.count);
        
        this.render(parsed, true);
      },
      error: err => {
        console.error('[GpsLayer] entity load error', err);
        this.clearLayers();
      }
    });
  }

  // -------------------------
  // RENDERING
  // -------------------------

  private render(collection: ParsedFeatureCollection, showTrajectory: boolean = false) {
    this.clearLayers();

    if (collection.features.length === 0) {
      console.log('[GpsLayer] No features to render');
      return;
    }

    // Group features by entity
    const entityGroups = this.geometryParser.groupByEntity(collection.features);
    
    let markersRendered = 0;
    let trajectoriesRendered = 0;

    for (const [entityId, features] of entityGroups) {
      const entityType = this.geometryParser.getEntityType(features[0]);
      const color = ENTITY_COLORS[entityType] || ENTITY_COLORS['unknown'];

      // Render trajectory line if showing trajectory or if entity is selected
      if ((showTrajectory || this.selectedEntity === entityId) && features.length > 1) {
        const coords = this.geometryParser.featuresToTrajectory(features);
        
        if (coords.length > 1) {
          const polyline = L.polyline(coords, {
            color: color,
            weight: 3,
            opacity: 0.8,
            smoothFactor: 1
          });
          
          polyline.bindPopup(`
            <strong>Entity:</strong> ${entityId}<br/>
            <strong>Type:</strong> ${entityType}<br/>
            <strong>Points:</strong> ${features.length}<br/>
            <strong>Start:</strong> ${new Date(features[0].properties.timestamp).toLocaleString()}<br/>
            <strong>End:</strong> ${new Date(features[features.length - 1].properties.timestamp).toLocaleString()}
          `);
          
          polyline.addTo(this.trajectoriesLayer);
          trajectoriesRendered++;
        }
      }

      // Render points
      for (const feature of features) {
        const props = feature.properties;
        const lat = props.latitude;
        const lng = props.longitude;

        if (typeof lat !== 'number' || typeof lng !== 'number') {
          continue;
        }

        // Smaller markers when showing trajectory, larger when showing all points
        const radius = showTrajectory ? 4 : 5;
        const isSelected = this.selectedEntity === entityId;

        const marker = L.circleMarker([lat, lng], {
          radius: isSelected ? 6 : radius,
          fillColor: color,
          color: isSelected ? '#000' : '#fff',
          weight: isSelected ? 2 : 1,
          fillOpacity: 0.8,
        });

        marker.bindPopup(`
          <strong>Entity:</strong> ${props.entity_id}<br/>
          <strong>Type:</strong> ${entityType}<br/>
          <strong>Speed:</strong> ${props.speed ?? 'n/a'} km/h<br/>
          <strong>Heading:</strong> ${props.heading ?? 'n/a'}°<br/>
          <strong>Time:</strong> ${
            props.timestamp
              ? new Date(props.timestamp).toLocaleString()
              : 'n/a'
          }
        `);

        marker.addTo(this.pointsLayer);
        markersRendered++;
      }
    }

    console.log('[GpsLayer] rendered:', markersRendered, 'markers,', trajectoriesRendered, 'trajectories');
  }

  // -------------------------
  // LIFECYCLE
  // -------------------------

  private clearLayers() {
    this.pointsLayer.clearLayers();
    this.trajectoriesLayer.clearLayers();
  }

  private detach() {
    if (this.moveListenerAttached) {
      this.map.off('moveend', this.onMoveEnd);
      this.moveListenerAttached = false;
    }
    this.clearLayers();
    this.pointsLayer.remove();
    this.trajectoriesLayer.remove();
  }

  ngOnDestroy(): void {
    this.detach();
  }
}