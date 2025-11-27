import { Component, Input, AfterViewInit, OnChanges, SimpleChanges, ViewChild, ElementRef, OnDestroy, inject, effect } from '@angular/core';
import * as L from 'leaflet';
import { ODPair } from '../interfaces/od';
import { Mode } from '../services/mode';

@Component({
  selector: 'app-map',
  imports: [],
  templateUrl: './map.html',
  styleUrl: './map.scss',
})

export class Map implements AfterViewInit, OnChanges, OnDestroy{
  // Liste des paires OD fournie par le parent
  @Input() odPairs: ODPair[] = [];
  // Optionnel : un parent peut transmettre un index sélectionné pour n'afficher
  // qu'une seule paire. Si null ou undefined, on affiche toutes les paires.
  @Input() selectedIndex: number | null = null;
  
  
  @ViewChild('map', { static: true }) private mapContainer!: ElementRef<HTMLDivElement>;


  private map?: L.Map;
  private odLayer?: L.LayerGroup;
  // injection du service Mode pour savoir si on est en mode 'od' ou 'default'
  private mode = inject(Mode);

  constructor() {
    // Effet réactif : quand le mode change, on affiche ou masque les OD.
    // L'effet vérifie que la carte est initialisée avant d'agir.
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

    this.odLayer = L.layerGroup().addTo(this.map);

    setTimeout(() => {
      try {
        this.map?.invalidateSize();
      } catch {
        // noop
      }
    }, 200);

    // Premier dessin : n'affiche les OD que si le mode est 'od'.
    if (this.mode.mode() === 'od') {
      this.updateOdLayers();
    } else {
      // s'assurer que la couche est vide en mode 'default'
      this.odLayer.clearLayers();
    }
  }
  

  ngOnDestroy(): void {
    // Bonne pratique : cleanup pour éviter les fuites mémoire
    this.map?.remove();
    this.map = undefined;
    this.odLayer = undefined;
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

  // Réagir aux changes d'inputs (odPairs, selectedIndex)
  ngOnChanges(changes: SimpleChanges): void {
    if (this.map && (changes['odPairs'] || changes['selectedIndex'])) {
      if (this.mode.mode() === 'od') {
        this.updateOdLayers();
      } else {
        this.odLayer?.clearLayers();
      }
    }
  }
  
}

