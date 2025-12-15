import { Component, Input, AfterViewInit, OnChanges, SimpleChanges, ViewChild, ElementRef, OnDestroy, inject, effect } from '@angular/core';
import * as L from 'leaflet';
import { ODPair } from '../interfaces/od';
import { Mode } from '../services/mode';
import { Gps } from '../services/gps';
import { GpsFeature, Bbox } from '../interfaces/gps';
import { OdLayer } from "../od-layer/od-layer";

@Component({
  selector: 'app-map',
  imports: [OdLayer],
  templateUrl: './map.html',
  styleUrl: './map.scss',
})

export class Map implements AfterViewInit, OnDestroy{
  // Liste des paires OD fournie par le parent
  @Input() odPairs: ODPair[] = [];
  // Optionnel : un parent peut transmettre un index sélectionné pour n'afficher
  // qu'une seule paire. Si null ou undefined, on affiche toutes les paires.
  @Input() selectedIndex: number | null = null;
  
  
  @ViewChild('mapContainer', { static: true }) 
  private mapContainer!: ElementRef<HTMLDivElement>;


  map?: L.Map;
  // private odLayer?: L.LayerGroup;
  // injection du service Mode pour savoir si on est en mode 'od' ou 'default'
  private pointsLayer?: L.LayerGroup;
  private mode = inject(Mode);
  private gps = inject(Gps);
  private moveListenerAttached = false;


  private onMoveEnd = () => {
    if (!this.map) return;
    const b = this.map.getBounds();
    const bbox: Bbox = {
      minLon: b.getWest(),
      maxLon: b.getEast(),
      minLat: b.getSouth(),
      maxLat: b.getNorth(),
    };
    // limiter le nombre de points par requête pour éviter surcharge
    this.loadPointsInBbox(bbox, 1000);
  };

  constructor() {
    // Effet réactif : quand le mode change, on affiche ou masque les OD.
    // L'effet vérifie que la carte est initialisée avant d'agir.
    effect(() => {
      const m = this.mode.mode();
      if (!this.map) return;
      // if (m === 'od') {
      //   // this.updateOdLayers();
      // } else {
      //   this.odLayer.clearLayers();
      // }

      if (m === 'gps') {
        // si pas attaché, attach listener et charge initial
        if (!this.moveListenerAttached) {
          this.map.on('moveend', this.onMoveEnd);
          this.moveListenerAttached = true;
        }
        // premier chargement (par bbox current viewport)
        const b = this.map.getBounds();
        const bbox: Bbox = {
          minLon: b.getWest(),
          maxLon: b.getEast(),
          minLat: b.getSouth(),
          maxLat: b.getNorth(),
        };
        this.loadPointsInBbox(bbox, 1000);
      } else {
        // retirer listener et vider la couche points si on quitte le mode gps
        if (this.moveListenerAttached) {
          this.map.off('moveend', this.onMoveEnd);
          this.moveListenerAttached = false;
        }
        this.pointsLayer?.clearLayers();
      }
    });
  }
  
  // --- Initialisation de la carte ---
  ngAfterViewInit(): void {
    this.map = L.map(this.mapContainer.nativeElement, {
      center: [48.8566, 2.3522], // Paris
      zoom: 13,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.map);

    // this.odLayer = L.layerGroup().addTo(this.map);
    this.pointsLayer = L.layerGroup().addTo(this.map);

    setTimeout(() => {
      try {
        this.map?.invalidateSize();
      } catch {
        // noop
      }
    }, 200);

    // Premier dessin : n'affiche les OD que si le mode est 'od'.
    if (this.mode.mode() === 'od') {
      // this.updateOdLayers();
    } else {
      // s'assurer que la couche est vide en mode 'default'
      // this.odLayer.clearLayers();
    }
  }

    loadPoints(limit = 1000): void {
    this.gps.getPoints(limit).subscribe({
      next: (resp) => {
        const features = resp.features || [];
        this.renderPoints(features);
        console.log('[Gps] loaded points:', features.length);
      },
      error: (err) => {
        console.error('[Gps] getPoints error', err);
      }
    });
        // premier chargement générique
    this.loadPoints(1000);    
  }

  loadPointsInBbox(bbox: Bbox, limit = 1000): void {
    this.gps.getPointsInBbox(bbox, limit).subscribe({
      next: (resp) => {
        const features = resp.features || [];
        this.renderPoints(features);
        console.log('[Gps] loaded bbox points:', features.length);
      },
      error: (err) => {
        console.error('[Gps] getPointsInBbox error', err);
      },
    });
  }

  private renderPoints(features: GpsFeature[]): void {
    if (!this.map || !this.pointsLayer) return;

    // Clear previous markers
    this.pointsLayer.clearLayers();

    const createdMarkers: L.CircleMarker[] = [];

    for (const f of features) {
      // support GeoJSON geometry.coordinates OR fallback to properties.lng/lat
      const coords = f.geometry?.coordinates;
      let lng: number | undefined;
      let lat: number | undefined;

      if (Array.isArray(coords) && coords.length >= 2) {
        [lng, lat] = coords;
      } else {
        lng = (f as any).properties?.longitude ?? (f as any).properties?.lng;
        lat = (f as any).properties?.latitude ?? (f as any).properties?.lat;
      }

      if (lng == null || lat == null) continue;

      const marker = L.circleMarker([lat, lng], {
        radius: 5,
        fillColor: f.properties?.is_valid ? '#3388ff' : '#ff6b6b',
        color: '#fff',
        weight: 1,
        opacity: 0.9,
        fillOpacity: 0.8,
      });

      const taxi = f.properties?.taxi_id ?? '—';
      const ts = f.properties?.timestamp ? new Date(f.properties.timestamp).toLocaleString() : '';
      marker.bindPopup(`<strong>Taxi ${taxi}</strong><br/>${lat.toFixed(5)}, ${lng.toFixed(5)}<br/><small>${ts}</small>`);

      marker.addTo(this.pointsLayer);
      createdMarkers.push(marker);
    }

    // Fit bounds if markers exist
    if (createdMarkers.length > 0) {
      const bounds = L.latLngBounds(createdMarkers.map(m => m.getLatLng()));
      try {
        this.map.fitBounds(bounds, { padding: [50, 50] });
      } catch {
        // ignore
      }
    }
  }
  
  ngOnDestroy(): void {
    // cleanup
    if (this.map && this.moveListenerAttached) {
      this.map.off('moveend', this.onMoveEnd);
      this.moveListenerAttached = false;
    }
    if (this.map) {
      this.map.remove();
    }
    this.map = undefined;
    // this.odLayer = undefined;
    this.pointsLayer?.clearLayers();
  }

  // private updateOdLayers(): void {
  //   // Dessine les origines/destinations sur la couche `odLayer`.
  //   if (!this.map || !this.odLayer) return;
  //   this.odLayer.clearLayers();
  //   if (!this.odPairs || this.odPairs.length === 0) return;

  //   const pairsToDraw =
  //     this.selectedIndex != null && this.selectedIndex >= 0 && this.selectedIndex < this.odPairs.length
  //       ? [this.odPairs[this.selectedIndex]]
  //       : this.odPairs;

  //   for (const pair of pairsToDraw) {
  //     const origin: L.LatLngExpression = [pair.origin.lat, pair.origin.lng];
  //     const dest: L.LatLngExpression = [pair.destination.lat, pair.destination.lng];

  //     L.polyline([origin, dest], { color: 'blue', weight: 3 }).addTo(this.odLayer);
  //     L.marker(origin).addTo(this.odLayer);
  //     L.marker(dest).addTo(this.odLayer);
  //   }
  // }

  // // Réagir aux changes d'inputs (odPairs, selectedIndex)
  // ngOnChanges(changes: SimpleChanges): void {
  //   if (this.map && (changes['odPairs'] || changes['selectedIndex'])) {
  //     if (this.mode.mode() === 'od') {
  //       this.updateOdLayers();
  //     } else {
  //       this.odLayer?.clearLayers();
  //     }
  //   }
  // }
  
}

