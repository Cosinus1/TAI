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
  @Input() selectedTaxi: string | null = null;

  private gps = inject(Gps);
  private mode = inject(Mode);

  private layer = L.layerGroup();
  private moveListenerAttached = false;

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

  private loadPointsInViewport(limit = 1000) {
    if (this.selectedTaxi) {
      console.log('[GpsLayer] load points for taxi', this.selectedTaxi);
      this.gps.getPointsByTaxi(this.selectedTaxi, limit).subscribe({
        next: resp => {
          const features = resp.results?.features ?? [];
          console.log('[GpsLayer] features for taxi', features.length);
          this.render(features);
        },
        error: err => console.error('[GpsLayer]', err),
      });
      return;
    }

    const b = this.map.getBounds();
    const bbox: Bbox = {
      minLon: b.getWest(),
      maxLon: b.getEast(),
      minLat: b.getSouth(),
      maxLat: b.getNorth(),
    };

    console.log('[GpsLayer] request bbox', bbox);

    this.gps.getPointsInBbox(bbox, limit).subscribe({
      next: resp => {
        console.log('[GpsLayer] raw response', resp);

        const features = resp.features?.features ?? [];
        console.log('[GpsLayer] extracted features count:', features.length);
        
        this.render(features);
      },
      error: err => console.error('[GpsLayer]', err),
    });
  }

  private render(features: GeoJsonFeature[]) {
    console.log('[GpsLayer] render called');

    this.layer.clearLayers();

    let rendered = 0;

    for (const f of features) {
      const props = f.properties;

      if (!props) {
        console.warn('[GpsLayer] feature without properties', f);
        continue;
      }

      const lat = props.latitude;
      const lng = props.longitude;

      if (lat == null || lng == null){
        console.warn('[GpsLayer] invalid coords', props);
        continue;
      } 

      const marker = L.circleMarker([lat, lng], {
        radius: 5,
        fillColor: props.is_valid ? '#3388ff' : '#ff6b6b',
        color: '#fff',
        weight: 1,
        fillOpacity: 0.8,
      });

      marker.bindPopup(`
        <strong>Taxi ${props.taxi_id}</strong><br/>
        ${lat.toFixed(5)}, ${lng.toFixed(5)}<br/>
        <small>${new Date(props.timestamp).toLocaleString()}</small>
      `);

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
