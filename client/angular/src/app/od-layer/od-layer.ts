import { Component, Input, inject, effect, OnChanges, SimpleChanges, OnDestroy } from '@angular/core';
import { ODPair } from '../interfaces/od';
import { Mode } from '../services/mode';
import * as L from 'leaflet';


@Component({
  selector: 'app-od-layer',
  imports: [],
  templateUrl: './od-layer.html',
  styleUrl: './od-layer.scss',
})
export class OdLayer implements OnChanges, OnDestroy {
  @Input({ required: true }) map!: L.Map;
  @Input() odPairs: ODPair[] = [];
  @Input() selectedIndex: number | null = null;

  private odLayer?: L.LayerGroup;

  private mode = inject(Mode);

  constructor() {
    effect(() => {
      const m = this.mode.mode();
      if (!this.map || !this.odLayer) return;
      if (m === 'od') {
        this.updateOdLayers();
      } else {
        this.odLayer.clearLayers();
      }  
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.map) return;

    if (!this.odLayer) {
      this.odLayer = L.layerGroup().addTo(this.map);
    }

    if (changes['odPairs'] || changes['selectedIndex']) {
      if (this.mode.mode() === 'od') {
        this.updateOdLayers();
      } else {
        this.odLayer.clearLayers();
      }
    }
  }

  private updateOdLayers(): void {
    // Dessine les origines/destinations sur la couche `odLayer`.
    if (!this.map || !this.odLayer) return;
    this.odLayer.clearLayers();
    if (!this.odPairs || this.odPairs.length === 0) return;

    const pairsToDraw =
      this.selectedIndex != null && this.selectedIndex >= 0 && this.selectedIndex < this.odPairs.length
        ? [this.odPairs[this.selectedIndex]]
        : this.odPairs;

    for (const pair of pairsToDraw) {
      const origin: L.LatLngExpression = [pair.origin.lat, pair.origin.lng];
      const dest: L.LatLngExpression = [pair.destination.lat, pair.destination.lng];

      L.polyline([origin, dest], { color: 'blue', weight: 3 }).addTo(this.odLayer);
      L.marker(origin).addTo(this.odLayer);
      L.marker(dest).addTo(this.odLayer);
    }
  }  

  ngOnDestroy(): void {
    this.odLayer?.clearLayers();
    this.odLayer?.remove();
    this.odLayer = undefined;
  }
}
