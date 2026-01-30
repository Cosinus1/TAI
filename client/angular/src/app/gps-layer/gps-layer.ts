import { Component, Input, OnChanges, SimpleChanges, effect, inject } from '@angular/core';
import * as L from 'leaflet';
import { Gps } from '../services/gps';
import { Mode } from '../services/mode';
import { GeometryParser } from '../services/geometry-parser';

@Component({
  selector: 'app-gps-layer',
  standalone: true,
  templateUrl: './gps-layer.html',
  styleUrl: './gps-layer.scss',
})
export class GpsLayer implements OnChanges {

  private gps = inject(Gps);
  private mode = inject(Mode);
  private geometryParser = inject(GeometryParser);

  // ===== Inputs =====

  @Input() map!: L.Map | null;
  @Input() datasetId: string | null = null;
  @Input() selectedEntity: string | null = null;
  @Input() entityTypeFilter?: string | null = null;

  // ===== Leaflet layers =====

  private markersLayer?: L.LayerGroup;
  private trajectoriesLayer?: L.LayerGroup;

  constructor() {
    effect(() => {
      const currentMode = this.mode.mode();
      this.refreshLayers();
    });
  }

  ngOnChanges(_: SimpleChanges) {

    if (!this.map) return;

    if (!this.markersLayer) {
      this.markersLayer = L.layerGroup().addTo(this.map);
      this.trajectoriesLayer = L.layerGroup().addTo(this.map);
    }

    this.refreshLayers();
  }

  private refreshLayers() {

    if (!this.datasetId || !this.markersLayer || !this.trajectoriesLayer) return;

    this.clearLayers();

    const mode = this.mode.mode();

    if (mode === 'gps') this.loadGPSPoints();
    if (mode === 'trajectory') this.loadTrajectories();
  }

  private loadGPSPoints() {

    const params: any = {
      dataset: this.datasetId,
      page_size: 1000,
      format: 'geojson'
    };

    if (this.selectedEntity) {
      params.entity_id = this.selectedEntity;
    }

    this.gps.getPoints(params).subscribe((response: any) => {

      response.features.forEach((feature: any) => {

        if (feature.geometry.type !== 'Point') return;

        const [lng, lat] = feature.geometry.coordinates;

        const marker = L.circleMarker([lat, lng], {
          radius: 6,
          fillColor: '#3b82f6',
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.8
        });

        marker.addTo(this.markersLayer!);
      });
    });
  }

  private loadTrajectories() {

    const params: any = {
      dataset: this.datasetId,
      page_size: 1000,
      format: 'geojson'
    };

    if (this.selectedEntity) {
      params.entity_id = this.selectedEntity;
    }

    this.gps.getTrajectories(params).subscribe((response: any) => {

      response.features.forEach((feature: any) => {

        if (feature.geometry.type !== 'LineString') return;

        const latLngs = feature.geometry.coordinates.map(
          (c: number[]) => [c[1], c[0]]
        );

        L.polyline(latLngs, {
          color: this.getEntityColor(feature.properties?.entity_id || 'x'),
          weight: 3
        }).addTo(this.trajectoriesLayer!);
      });
    });
  }

  private clearLayers() {
    this.markersLayer?.clearLayers();
    this.trajectoriesLayer?.clearLayers();
  }

  private getEntityColor(entityId: string): string {

    let hash = 0;

    for (let i = 0; i < entityId.length; i++) {
      hash = entityId.charCodeAt(i) + ((hash << 5) - hash);
    }

    return `hsl(${Math.abs(hash % 360)}, 70%, 50%)`;
  }
}
