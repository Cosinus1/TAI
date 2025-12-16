import { Component, Input, AfterViewInit, ViewChild, ElementRef, signal } from '@angular/core';
import * as L from 'leaflet';
import { ODPair } from '../interfaces/od';
import { OdLayer } from "../od-layer/od-layer";
import { GpsLayer } from '../gps-layer/gps-layer';

@Component({
  selector: 'app-map',
  imports: [OdLayer, GpsLayer],
  templateUrl: './map.html',
  styleUrl: './map.scss',
})

export class Map implements AfterViewInit{
  // Liste des paires OD fournie par le parent
  @Input() odPairs: ODPair[] = [];
  // Optionnel : un parent peut transmettre un index sélectionné pour n'afficher
  // qu'une seule paire. Si null ou undefined, on affiche toutes les paires.
  @Input() selectedIndex: number | null = null;
  @Input() selectedTaxi: string | null = null;
  
  @ViewChild('mapContainer', { static: true }) 
  private mapContainer!: ElementRef<HTMLDivElement>;


  readonly map = signal<L.Map | null>(null);

  // --- Initialisation de la carte ---
  ngAfterViewInit(): void {
    const m = L.map(this.mapContainer.nativeElement, {
      center: [39.9042, 116.4074], // Paris
      zoom: 11,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(m);

    setTimeout(() => {
      try {
        m.invalidateSize();
      } catch {
        // noop
      }
    }, 200);
    this.map.set(m);
  }
}

