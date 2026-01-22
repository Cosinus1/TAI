// client/angular/src/app/map/map.ts
import { Component, Input, AfterViewInit, ViewChild, ElementRef, signal } from '@angular/core';
import * as L from 'leaflet';
import { ODPair } from '../interfaces/od';
import { OdLayer } from "../od-layer/od-layer";
import { GpsLayer } from '../gps-layer/gps-layer';

@Component({
  selector: 'app-map',
  standalone: true,
  imports: [OdLayer, GpsLayer],
  templateUrl: './map.html',
  styleUrl: './map.scss',
})
export class Map implements AfterViewInit {
  // Liste des paires OD fournie par le parent
  @Input() odPairs: ODPair[] = [];
  
  // Optionnel : un parent peut transmettre un index sélectionné pour n'afficher
  // qu'une seule paire. Si null ou undefined, on affiche toutes les paires.
  @Input() selectedIndex: number | null = null;
  
  // Selected entity (taxi, vehicle, etc.)
  @Input() selectedEntity: string | null = null;
  
  // Optional: Dataset ID to filter data
  @Input() datasetId?: string;

  // Filter inputs
  @Input() entityTypeFilter?: string | null = null;

  // Map center configuration
  @Input() centerLat: number = 48.8566; // Paris by default
  @Input() centerLng: number = 2.3522;
  @Input() initialZoom: number = 12;
  
  @ViewChild('mapContainer', { static: true }) 
  private mapContainer!: ElementRef<HTMLDivElement>;

  readonly map = signal<L.Map | null>(null);

  // --- Initialisation de la carte ---
  ngAfterViewInit(): void {
    const m = L.map(this.mapContainer.nativeElement, {
      center: [this.centerLat, this.centerLng],
      zoom: this.initialZoom,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(m);

    // Fix for map sizing issues
    setTimeout(() => {
      try {
        m.invalidateSize();
      } catch {
        // noop
      }
    }, 200);
    
    this.map.set(m);
  }

  /**
   * Center the map on specific coordinates
   */
  centerOn(lat: number, lng: number, zoom?: number): void {
    const m = this.map();
    if (m) {
      if (zoom !== undefined) {
        m.setView([lat, lng], zoom);
      } else {
        m.setView([lat, lng]);
      }
    }
  }

  /**
   * Center on Paris
   */
  centerOnParis(): void {
    this.centerOn(48.8566, 2.3522, 12);
  }

  /**
   * Center on Beijing
   */
  centerOnBeijing(): void {
    this.centerOn(39.9042, 116.4074, 11);
  }
}