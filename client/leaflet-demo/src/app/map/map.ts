import { Component, AfterViewInit, signal, Input, ChangeDetectorRef } from '@angular/core';
import * as L from 'leaflet';
import { PoiFiltersComponent } from '../poi-filters/poi-filters.component';
import { OdToggleComponent } from '../od-toggle/od-toggle.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import type { ODPair } from '../models/od.model';
import { TaxiService } from '../services/taxi.service';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-map',
  templateUrl: './map.html',
  standalone: true,
  imports: [SidebarComponent],
  styleUrls: ['./map.scss']
})
export class MapComponent implements AfterViewInit {
  // --- Composant Map ---
  // Ce composant initialise une carte Leaflet, affiche des paires OD (origine/destination),
  // des POI filtrables (restaurant/cafe/cinema) et un mode "taxi" qui montre
  // des points GPS groupés par `taxi_id`. Les commentaires ci-dessous expliquent
  // les principales structures de données et le rôle des méthodes.

  // --- Propriétés de la carte ---
  private map: L.Map | undefined;
  private odMarkers: L.Marker[] = [];
  private poiMarkers: L.Marker[] = [];
  // taxi markers (separate from POI markers) keyed by user_id
  private taxiMarkers: Map<string, L.Marker> = new Map();
  // markers for every taxi point: taxi_id -> array of markers
  private taxiPointMarkers: Map<string, L.Marker[]> = new Map();
  private _displayMode: 'od' | 'taxi' = 'od';

  constructor(private taxiService: TaxiService, private cdr: ChangeDetectorRef) {}
  // per-taxi trajectory storage: taxi_id -> array of raw points
  private taxiPointsMap: Map<string, any[]> = new Map();
  taxiList: string[] = [];
  selectedTaxiId: string | null = null;
  // time filtering & playback
  private currentStartTime: Date | null = null;
  private currentEndTime: Date | null = null;
  private playing = false;
  private playTimer: any = null;
  private playCursor: Date | null = null;
  // persisted filter strings (for binding to Sidebar)
  savedStartStr: string | null = null;
  savedEndStr: string | null = null;

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

  // --- Hook de cycle de vie ---
  // ngAfterViewInit est utilisé pour initialiser la carte après que le DOM
  // (élément #map) soit disponible. On restaure aussi ici les filtres temporels
  // éventuellement sauvegardés dans localStorage.
  ngAfterViewInit(): void {
    setTimeout(() => {
      this.initMap();
      this.updateMap();
      // restore persisted time range from localStorage (if any)
      try {
        const s = localStorage.getItem('taxi_time_filter_start');
        const e = localStorage.getItem('taxi_time_filter_end');
        if (s) this.savedStartStr = s;
        if (e) this.savedEndStr = e;
        // if values exist, apply them (this will parse and call applyTimeFilter)
        if (s || e) this.onTimeRangeChange({ start: s ?? null, end: e ?? null });
      } catch (err) {
        // ignore localStorage errors
      }
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
      // fetch and show taxi points
      await this.fetchTaxiPoints();
    } else {
      // clear taxi point markers then redraw OD and POIs
      this.taxiPointMarkers.forEach(arr => arr.forEach(m => { if (this.map && this.map.hasLayer(m)) this.map.removeLayer(m); }));
      this.taxiPointMarkers.clear();
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

  // handle taxi selection from sidebar: null => show all latest positions, otherwise show selected taxi trajectory
  onTaxiSelect(taxiId: string | null) {
    this.selectedTaxiId = taxiId;
    // redraw visualization according to selection
    if (this._displayMode !== 'taxi' || !this.map) return;
    // remove any previous trajectory layer we might have drawn
    if (this.odLine) { this.map.removeLayer(this.odLine); this.odLine = null; }

    if (taxiId === null) {
      // show all points for all taxis: add every marker to map
      const bounds: L.LatLngExpression[] = [];
      this.taxiPointMarkers.forEach((arr, tid) => {
        arr.forEach(m => {
          if (!this.map) return;
          if (!this.map.hasLayer(m)) this.map.addLayer(m);
          bounds.push(m.getLatLng());
        });
      });
      if (bounds.length) this.map.fitBounds(L.latLngBounds(bounds), { padding: [40, 40] });
    } else {
      // show the full trajectory for the selected taxi
      // First, ensure only markers for selected taxi are visible
      const bounds: L.LatLngExpression[] = [];
      this.taxiPointMarkers.forEach((arr, tid) => {
        arr.forEach(m => {
          if (!this.map) return;
          if (tid === taxiId) {
            if (!this.map.hasLayer(m)) this.map.addLayer(m);
            bounds.push(m.getLatLng());
          } else {
            if (this.map.hasLayer(m)) this.map.removeLayer(m);
          }
        });
      });

      const points = this.taxiPointsMap.get(taxiId) ?? [];
      if (points.length === 0) return;
      // convert to latlng and sort by timestamp
      const latlngs = points
        .slice()
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
        .map(p => [p.latitude ?? p.lat ?? null, p.longitude ?? p.lon ?? p.lng ?? null]);
      const validLatlngs = (latlngs as any[]).filter(arr => typeof arr[0] === 'number' && typeof arr[1] === 'number');

      // draw polyline
      if (this.odLine) { this.map.removeLayer(this.odLine); this.odLine = null; }
      this.odLine = L.polyline(validLatlngs as any, { color: 'orange', weight: 4, opacity: 0.8 }).addTo(this.map);
      // fit bounds to trajectory
      const b = L.latLngBounds(validLatlngs as any);
      this.map.fitBounds(b, { padding: [40, 40] });
    }
  }

  // Time controls from sidebar
  onTimeRangeChange(range: { start: string | null; end: string | null }) {
    // parse datetime-local reliably: if the string has a timezone (Z or +/-) use Date, else construct local Date
    const parseLocalInput = (s: string | null): Date | null => {
      if (!s) return null;
      // if contains timezone info (Z or +/-HH:mm) let Date parse it
      if (/([zZ]|[+\-]\d{2}:?\d{2})$/.test(s)) return new Date(s);
      // expected format: YYYY-MM-DDTHH:mm[:ss]
      const m = s.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/);
      if (!m) return new Date(s);
      const year = Number(m[1]);
      const month = Number(m[2]) - 1;
      const day = Number(m[3]);
      const hour = Number(m[4]);
      const minute = Number(m[5]);
      const second = m[6] ? Number(m[6]) : 0;
      // Important: interpret datetime-local input as UTC to match backend timestamps that use Z (UTC).
      return new Date(Date.UTC(year, month, day, hour, minute, second));
    };

    this.currentStartTime = parseLocalInput(range.start);
    this.currentEndTime = parseLocalInput(range.end);
    // Auto-clamp: if user selected an end date far after start (more than 24h),
    // assume they meant the same day and clamp end to start's date keeping the end's time.
    if (this.currentStartTime && this.currentEndTime) {
      const msDiff = Math.abs(this.currentEndTime.getTime() - this.currentStartTime.getTime());
      const oneDay = 24 * 3600 * 1000;
      if (msDiff > oneDay) {
        // build a new Date using start's YMD and end's HH:MM:SS
        const e = this.currentEndTime;
        const s = this.currentStartTime;
        const clamped = new Date(s.getFullYear(), s.getMonth(), s.getDate(), e.getHours(), e.getMinutes(), e.getSeconds());
        // only replace if clamped is within reasonable range around start (e.g., within 2 days)
        if (Math.abs(clamped.getTime() - s.getTime()) <= 7 * oneDay) {
          this.currentEndTime = clamped;
          console.debug('Auto-clamped end time to same day as start:', this.currentEndTime.toISOString());
        }
      }
    }
    // stop playback if running
    if (this.playing) this.stopPlayback();

    // ensure marker timestamp cache exists (ms) for fast comparisons
    this.taxiPointMarkers.forEach(markers => markers.forEach(m => {
      const meta = (m as any);
      if (meta._ts_ms == null) {
        if (meta._ts) {
          const parsed = Date.parse(meta._ts);
          meta._ts_ms = Number.isNaN(parsed) ? null : parsed;
        } else {
          meta._ts_ms = null;
        }
      }
    }));

    this.applyTimeFilter();
  }

  onPlayToggle(start: boolean) {
    this.playing = start;
    if (this.playing) this.startPlayback(); else this.stopPlayback();
  }

  private applyTimeFilter() {
    if (!this.map) return;
    // if no range set show as usual (respect selectedTaxiId filtering)
    this.taxiPointMarkers.forEach((markers, tid) => {
      markers.forEach(m => {
        const tsMs = (m as any)._ts_ms ?? null;
        let visible = true;
        if (this.currentStartTime && (tsMs == null || tsMs < this.currentStartTime.getTime())) visible = false;
        if (this.currentEndTime && (tsMs == null || tsMs > this.currentEndTime.getTime())) visible = false;
        // also respect selected taxi: if selectedTaxiId is set, hide others
        if (this.selectedTaxiId && tid !== this.selectedTaxiId) visible = false;
        if (visible) {
          if (!this.map!.hasLayer(m)) this.map!.addLayer(m);
        } else {
          if (this.map!.hasLayer(m)) this.map!.removeLayer(m);
        }
      });
    });
  }

  private startPlayback() {
    if (!this.currentStartTime || !this.currentEndTime || !this.map) return;
    // initialize cursor at start
    this.playCursor = new Date(this.currentStartTime);
    // ensure selectedTaxiId doesn't hide points (we keep selection behavior: if a taxi is selected play only that taxi)
    const stepMs = 1000; // advance 1 second of real time per tick (feel free to adjust)
    this.playTimer = setInterval(() => {
      if (!this.playCursor) return;
      // show points with timestamp <= playCursor
      this.taxiPointMarkers.forEach((markers, tid) => {
        markers.forEach(m => {
          const tsMs = (m as any)._ts_ms ?? null;
          const shouldShow = tsMs !== null && tsMs <= this.playCursor!.getTime()
            && (!this.selectedTaxiId || tid === this.selectedTaxiId)
            && (!this.currentStartTime || tsMs >= this.currentStartTime!.getTime());
          if (shouldShow) { if (!this.map!.hasLayer(m)) this.map!.addLayer(m); }
          else { if (this.map!.hasLayer(m)) this.map!.removeLayer(m); }
        });
      });
      // advance cursor
      this.playCursor = new Date(this.playCursor.getTime() + stepMs);
      if (this.playCursor.getTime() > this.currentEndTime!.getTime()) {
        this.stopPlayback();
      }
    }, 200); // ticks every 200ms to feel smooth (advancing 1s per tick)
  }

  private stopPlayback() {
    if (this.playTimer) { clearInterval(this.playTimer); this.playTimer = null; }
    this.playing = false;
    this.playCursor = null;
  }

  // --- Récupérer un point de taxi (mock) depuis le front et l'afficher ---
  async fetchTaxiPoints(): Promise<void> {
    if (!this.map) return;
    try {
      const res = await firstValueFrom(this.taxiService.getSampleTaxiPointsMock());
      if (!res?.ok || !Array.isArray(res.points)) { console.error('Erreur serveur (mock points):', res); return; }
      const points = res.points;

      // prepare taxi icon
      const taxiIcon = L.icon({
        iconUrl: 'https://cdn-icons-png.flaticon.com/512/743/743007.png',
        iconSize: [36, 36],
        iconAnchor: [18, 36],
        popupAnchor: [0, -30]
      });
      // Group points by taxi_id and store trajectories
      this.taxiPointsMap.clear();
      const byTaxi = new Map<string, any[]>();
      points.forEach((raw: any, idx: number) => {
        const norm = typeof this.taxiService.normalizeTdrivePoint === 'function'
          ? this.taxiService.normalizeTdrivePoint(raw)
          : { id: raw.id ?? null, taxi_id: raw.user_id ?? raw.taxi_id ?? String(idx), timestamp: raw.timestamp, lat: raw.latitude ?? raw.lat ?? null, lon: raw.longitude ?? raw.lon ?? raw.lng ?? null, raw };
        const tid = String(norm.taxi_id ?? idx);
        if (!byTaxi.has(tid)) byTaxi.set(tid, []);
        byTaxi.get(tid)!.push({ ...raw, _norm: norm });
      });

  // update taxiPointsMap and taxiList (assign new array reference so OnPush children detect change)
  this.taxiPointsMap.clear();
  byTaxi.forEach((arr, tid) => this.taxiPointsMap.set(tid, arr));
  this.taxiList = Array.from(byTaxi.keys());
  // notify Angular change detection (Sidebar is OnPush)
  try { this.cdr.markForCheck(); } catch (e) { /* ignore in case not available */ }

      // remove previous per-point markers
      this.taxiPointMarkers.forEach(arr => arr.forEach(m => { if (this.map && this.map.hasLayer(m)) this.map.removeLayer(m); }));
      this.taxiPointMarkers.clear();

      // create a small red-dot SVG icon for point markers
      const redDotSvg = encodeURIComponent("<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12'><circle cx='6' cy='6' r='4' fill='red'/></svg>");
      const redDotUrl = `data:image/svg+xml;charset=UTF-8,${redDotSvg}`;
      const redDotIcon = L.icon({ iconUrl: redDotUrl, iconSize: [12, 12], iconAnchor: [6, 6], popupAnchor: [0, -6] });

      // Display every point as a small red dot; store markers per taxi
      const visibleBounds: L.LatLngExpression[] = [];
      byTaxi.forEach((arr, tid) => {
        const markers: L.Marker[] = [];
        // iterate all points for this taxi
        arr.forEach((raw: any) => {
          const norm = raw._norm;
          const lat = norm.lat;
          const lng = norm.lon;
          if (typeof lat !== 'number' || typeof lng !== 'number') return;
          const latlng: L.LatLngExpression = [lat, lng];

          // create marker (small red dot)
          const m = L.marker(latlng, { icon: redDotIcon }).bindPopup(`<b>Taxi point</b><br/>taxi_id: ${tid}<br/>time: ${norm.timestamp || ''}`);
          // attach timestamp metadata for filtering/playback
          (m as any)._ts = norm.timestamp ?? null;
          // decide whether to add to map now depending on selection
          if (this.selectedTaxiId === null || this.selectedTaxiId === tid) {
            m.addTo(this.map!);
            visibleBounds.push(latlng);
          }
          markers.push(m);
        });
        this.taxiPointMarkers.set(tid, markers);
      });

      // Fit map to show visible points (if any)
      if (visibleBounds.length > 0) {
        const b = L.latLngBounds(visibleBounds as any);
        this.map.fitBounds(b, { padding: [40, 40] });
      }
    } catch (err) {
      console.error('Erreur en récupérant les points taxi (mock):', err);
    }
  }

  // --- Requête Overpass API pour récupérer les POI ---
  // Construis une requête Overpass pour obtenir les nœuds `amenity` près d'un point
  // et transforme la réponse en un tableau { name, type, lat, lng } utilisé par addPOIsAround
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
  // Calcul de la distance (approx. haversine) entre deux coordonnées
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
