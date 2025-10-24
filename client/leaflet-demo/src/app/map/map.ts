import { Component, AfterViewInit, signal, Input } from '@angular/core';
import * as L from 'leaflet';
import { PoiFiltersComponent } from '../poi-filters/poi-filters.component';
import { OdToggleComponent } from '../od-toggle/od-toggle.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import type { ODPair } from '../models/od.model';

@Component({
  selector: 'app-map',
  templateUrl: './map.html',
  standalone: true,
  imports: [PoiFiltersComponent, OdToggleComponent, SidebarComponent],
  styleUrls: ['./map.scss']
})
export class MapComponent implements AfterViewInit {

  // --- Propriétés de la carte ---
  private map: L.Map | undefined;
  private odMarkers: L.Marker[] = [];
  private poiMarkers: L.Marker[] = [];
  // taxi marker (separate from POI markers)
  private taxiMarker: L.Marker | null = null;
  private _displayMode: 'od' | 'taxi' = 'od';

  // --- Données OD ---
  odPairs: ODPair[] = [
    { origin: { name: 'Paris', lat: 48.8566, lng: 2.3522 }, destination: { name: 'Lyon', lat: 45.7640, lng: 4.8357 } },
    { origin: { name: 'Marseille', lat: 43.2965, lng: 5.3698 }, destination: { name: 'Nice', lat: 43.7102, lng: 7.2620 } },
    { origin: { name: 'Toulouse', lat: 43.6045, lng: 1.4440 }, destination: { name: 'Bordeaux', lat: 44.8378, lng: -0.5792 } }
  ];


  // --- OD sélectionnée ---
  selectedOD = signal(this.odPairs[0]);
  
  // --- Options / filtres POI ---
  showRestaurant = signal(true);
  showCafe = signal(true);
  showCinema = signal(true);
  showODLine = signal(true);
  
  // store reference to last drawn polyline for removal
  private odLine: L.Polyline | null = null;

  // --- Lifecycle hook ---
  ngAfterViewInit(): void {
    setTimeout(() => {
      this.initMap();
      this.updateMap();
    });
  }

  @Input()
  set displayMode(m: 'od' | 'taxi') {
    this._displayMode = m;
    this.onDisplayModeChanged();
  }
  get displayMode() { return this._displayMode; }

  // Sidebar now renders odPairs directly with *ngFor; odOptionsHTML removed

  // --- Initialisation de la carte ---
  private initMap(): void {
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;

    this.map = L.map('map').setView([46.6, 2.5], 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.map);
  }

  // --- Mise à jour de la carte quand OD sélectionnée ---
  async updateMap(): Promise<void> {
    if (!this.map) return;

    // Supprime anciens marqueurs OD et POI
    this.odMarkers.forEach(m => this.map!.removeLayer(m));
    this.poiMarkers.forEach(m => this.map!.removeLayer(m));
    this.odMarkers = [];
    this.poiMarkers = [];

    const od = this.selectedOD();

    // --- Marqueurs OD ---
    const originMarker = L.marker([od.origin.lat, od.origin.lng])
      .addTo(this.map)
      .bindPopup(`<b>Origine:</b> ${od.origin.name}`);
    const destMarker = L.marker([od.destination.lat, od.destination.lng])
      .addTo(this.map)
      .bindPopup(`<b>Destination:</b> ${od.destination.name}`);
    this.odMarkers.push(originMarker, destMarker);

    // --- Ligne OD ---
    // Create or update the OD line according to current option
    this.updateODLine();

    // --- POI dynamiques ---
    // --- POI dynamiques (respect des filtres) ---
    await this.addPOIsAround(od.origin.lat, od.origin.lng, 500);
    await this.addPOIsAround(od.destination.lat, od.destination.lng, 500);

    // --- Ajuste la vue pour afficher origine et destination ---
    try {
      const bounds = L.latLngBounds([[od.origin.lat, od.origin.lng], [od.destination.lat, od.destination.lng]]);
      this.map.fitBounds(bounds, { padding: [50, 50] });
    } catch (e) {
      // fallback: center on mid point
      const centerLat = (od.origin.lat + od.destination.lat) / 2;
      const centerLng = (od.origin.lng + od.destination.lng) / 2;
      this.map.setView([centerLat, centerLng], 14);
    }
  }

  private async onDisplayModeChanged() {
    if (!this.map) return;
    if (this._displayMode === 'taxi') {
      // remove OD markers, POIs and OD line
      this.odMarkers.forEach(m => this.map!.removeLayer(m));
      this.poiMarkers.forEach(m => this.map!.removeLayer(m));
      if (this.odLine) { this.map.removeLayer(this.odLine); this.odLine = null; }
      this.odMarkers = [];
      this.poiMarkers = [];
      // fetch and show taxi point
      await this.fetchTaxiPoint();
    } else {
      // clear taxi marker then redraw OD and POIs
      if (this.taxiMarker) { this.map.removeLayer(this.taxiMarker); this.taxiMarker = null; }
      // redraw current OD
      this.updateMap();
    }
  }

  // --- Ajouter les POI autour d’un point ---
  private async addPOIsAround(lat: number, lng: number, radiusMeters: number = 500): Promise<void> {
    if (!this.map) return;

    const pois = await this.fetchPOIs(lat, lng, radiusMeters);

    pois.forEach(poi => {
      // Respect filters: only add marker if corresponding signal is true
      if (poi.type === 'restaurant' && !this.showRestaurant()) return;
      if (poi.type === 'cafe' && !this.showCafe()) return;
      if (poi.type === 'cinema' && !this.showCinema()) return;

      const iconUrl = poi.type === 'restaurant'
        ? 'https://cdn-icons-png.flaticon.com/512/1046/1046784.png'
        : poi.type === 'cinema'
          ? 'https://cdn-icons-png.flaticon.com/512/190/190411.png'
          : 'https://cdn-icons-png.flaticon.com/512/252/252025.png';

      const icon = L.icon({
        iconUrl,
        iconSize: [30, 30],
        iconAnchor: [15, 30],
        popupAnchor: [0, -30]
      });

      const marker = L.marker([poi.lat, poi.lng], { icon })
        .addTo(this.map!)
        .bindPopup(`<b>${poi.type.toUpperCase()}</b>: ${poi.name}`);

      // store a small metadata so we can filter later if needed
      (marker as any).poiType = poi.type;

      this.poiMarkers.push(marker);
    });
  }
  
  // --- Toggle filter helper used from template ---
  toggleFilter(type: string, event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    if (type === 'restaurant') this.showRestaurant.set(checked);
    if (type === 'cafe') this.showCafe.set(checked);
    if (type === 'cinema') this.showCinema.set(checked);
  }
  
  toggleODLine(event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    this.showODLine.set(checked);
    // redraw to show/hide line
    this.updateODLine();
  }
  
  applyOptions() {
    // Clear POIs and redraw according to filters
    if (!this.map) return;
    this.poiMarkers.forEach(m => this.map!.removeLayer(m));
    this.poiMarkers = [];
    // Re-fetch POIs for the origin and destination
    const od = this.selectedOD();
    this.addPOIsAround(od.origin.lat, od.origin.lng, 500);
    this.addPOIsAround(od.destination.lat, od.destination.lng, 500);
    // OD line
    this.updateODLine();
  }
  
  resetOptions() {
    this.showRestaurant.set(true);
    this.showCafe.set(true);
    this.showCinema.set(true);
    this.showODLine.set(true);
    this.applyOptions();
  }
  
  private updateODLine() {
    if (!this.map) return;
    // remove previous line
    if (this.odLine) { this.map.removeLayer(this.odLine); this.odLine = null; }
    if (!this.showODLine()) return;
    const od = this.selectedOD();
    this.odLine = L.polyline([[od.origin.lat, od.origin.lng], [od.destination.lat, od.destination.lng]], { color: 'blue', weight: 3, opacity: 0.7 }).addTo(this.map);
  }


  // --- Changement OD ---
  // new signature: receive index number emitted by SidebarComponent
  onODChange(indexOrEvent: number | Event) {
    const index = typeof indexOrEvent === 'number' ? indexOrEvent : (indexOrEvent.target as HTMLSelectElement).selectedIndex;
    if (index < 0 || index >= this.odPairs.length) return;
    this.selectedOD.set(this.odPairs[index]);
    this.updateMap();
  }

  getSelectedIndex(): number {
    return this.odPairs.findIndex(od => od === this.selectedOD());
  }

  // --- Handlers for child components ---
  onFiltersChange(filters: { restaurant: boolean; cafe: boolean; cinema: boolean }) {
    this.showRestaurant.set(filters.restaurant);
    this.showCafe.set(filters.cafe);
    this.showCinema.set(filters.cinema);
    // Update POIs immediately
    this.applyOptions();
  }

  onODToggle(show: boolean) {
    this.showODLine.set(show);
    this.updateODLine();
  }

  // --- Récupérer un point de taxi depuis le serveur et l'afficher ---
  async fetchTaxiPoint(): Promise<void> {
    if (!this.map) return;
    try {
      const res = await fetch('/api/mobility/sample_taxi/');
      const data = await res.json();
      if (!data.ok) { console.error('Erreur serveur:', data.error); return; }
      const p = data.point;
      if (!p || !p.latitude || !p.longitude) { console.warn('Point taxi invalide', p); return; }

      // Create a taxi icon
      const taxiIcon = L.icon({
        iconUrl: 'https://cdn-icons-png.flaticon.com/512/743/743007.png',
        iconSize: [36, 36],
        iconAnchor: [18, 36],
        popupAnchor: [0, -30]
      });

      // place/update taxi marker separately
      if (this.taxiMarker) { this.map.removeLayer(this.taxiMarker); this.taxiMarker = null; }
      this.taxiMarker = L.marker([p.latitude, p.longitude], { icon: taxiIcon })
        .addTo(this.map)
        .bindPopup(`<b>Taxi</b><br/>user_id: ${p.user_id || ''}<br/>time: ${p.timestamp || ''}`)
        .openPopup();
      // center map so the taxi point is visible
      const latlng = L.latLng(p.latitude, p.longitude);
      this.map.setView(latlng, 16);
    } catch (err) {
      console.error('Erreur en récupérant le point taxi:', err);
    }
  }

  // --- Requête Overpass API pour récupérer les POI ---
  private async fetchPOIs(lat: number, lng: number, radius: number = 500): Promise<any[]> {
    const query = `
      [out:json];
      (
        node["amenity"~"restaurant|cafe|cinema"](around:${radius},${lat},${lng});
      );
      out center;
    `;

    const url = 'https://overpass-api.de/api/interpreter?data=' + encodeURIComponent(query);
    try {
      const response = await fetch(url);
      const data = await response.json();
      return data.elements.map((el: any) => ({
        name: el.tags.name || el.tags.amenity,
        type: el.tags.amenity,
        lat: el.lat,
        lng: el.lon
      }));
    } catch (err) {
      console.error('Erreur lors de la récupération des POI:', err);
      return [];
    }
  }

  // --- Fonctions utilitaires ---
  private getDistance(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const R = 6371;
    const dLat = this.deg2rad(lat2 - lat1);
    const dLng = this.deg2rad(lng2 - lng1);
    const a = Math.sin(dLat/2)**2 +
      Math.cos(this.deg2rad(lat1)) * Math.cos(this.deg2rad(lat2)) * Math.sin(dLng/2)**2;
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  private deg2rad(deg: number): number {
    return deg * (Math.PI/180);
  }

}
