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

  private gps = inject(Gps);
  private mode = inject(Mode);

  private layer = L.layerGroup();
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

      this.layer.addTo(this.map);

      if (!this.moveListenerAttached) {
        this.map.on('moveend', this.onMoveEnd);
        this.moveListenerAttached = true;
      }

      this.loadPointsInViewport();
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['datasetId'] || changes['entityTypeFilter']) {
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

    this.gps.getPointsInBbox(bbox, {
      dataset: this.currentDatasetId,
      entity_type: this.entityTypeFilter || undefined,
      limit,
      only_valid: true
    }).subscribe({
      next: resp => {
        console.log('[GpsLayer] raw response:', resp);
        const features = Array.isArray(resp?.features)
          ? resp.features
          : [];

        this.render(features);
      },
      error: err => {
        console.error('[GpsLayer] load error', err);
        this.layer.clearLayers();
      }
    });
  }

  // -------------------------
  // RENDERING (RAW DATA)
  // -------------------------

  private getEntityType(props: any): string {
    return (
      props?.extra_attributes?.entity_type ||
      props?.entity_id?.split('_')[0] ||
      'unknown'
    );
  }

  private render(features: any[]) {
    this.layer.clearLayers();

    let rendered = 0;

    for (const f of features) {
      const props = f.properties;
      if (!props) continue;

      const lat = props.latitude;
      const lng = props.longitude;

      if (
        typeof lat !== 'number' ||
        typeof lng !== 'number'
      ) {
        continue;
      }

      const entityType = this.getEntityType(props);
      const color = ENTITY_COLORS[entityType] || ENTITY_COLORS['unknown'];

      const marker = L.circleMarker([lat, lng], {
        radius: 5,
        fillColor: color,
        color: '#fff',
        weight: 1,
        fillOpacity: 0.8,
      });

      marker.bindPopup(`
        <strong>Entity:</strong> ${props.entity_id}<br/>
        <strong>Type:</strong> ${entityType}<br/>
        <strong>Speed:</strong> ${props.speed ?? 'n/a'}<br/>
        <strong>Time:</strong> ${
          props.timestamp
            ? new Date(props.timestamp).toLocaleString()
            : 'n/a'
        }
      `);

      marker.addTo(this.layer);
      rendered++;
    }

    console.log('[GpsLayer] markers rendered:', rendered);
  }

  // -------------------------
  // LIFECYCLE
  // -------------------------

  private detach() {
    if (this.moveListenerAttached) {
      this.map.off('moveend', this.onMoveEnd);
      this.moveListenerAttached = false;
    }
    this.layer.clearLayers();
    this.layer.remove();
  }

  ngOnDestroy(): void {
    this.detach();
  }
}
