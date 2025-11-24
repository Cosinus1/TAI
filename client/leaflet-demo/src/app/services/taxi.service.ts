import { Injectable } from '@angular/core';
import { of, Observable } from 'rxjs';
import { delay } from 'rxjs/operators';

/**
 * TaxiService (mock)
 * Service utilitaire utilisé en développement lorsque le backend n'est pas disponible.
 * Il expose des méthodes qui retournent des objets de la même forme que l'API Django
 * afin que le front puisse être développé et testé sans serveur réel.
 */
@Injectable({ providedIn: 'root' })
export class TaxiService {
  /**
   * Retourne un objet mock similaire à l'endpoint Django attendu : { ok: true, point: {...} }
   * On ajoute un petit délai pour simuler la latence réseau.
   */
  getSampleTaxiPointMock(): Observable<{ ok: boolean; point: any }> {
    // keep a simple compatibility wrapper which returns a single point in tdrive shape
    const mock = {
      ok: true,
      point: {
        id: 1001,
        taxi_id: 'taxi_1',
        timestamp: '2024-01-15T08:30:00Z',
        longitude: 2.3522,
        latitude: 48.8566,
        imported_at: '2024-01-15T09:00:00Z',
        source_file: 'TAXI_1.txt',
        is_valid: true
      }
    };
    return of(mock).pipe(delay(400));
  }

  /**
   * Retourne plusieurs points taxi simulés (forme: { ok: true, points: [...] }).
   * Utile pour tester l'affichage de trajectoires et le filtrage temporel.
   */
  getSampleTaxiPointsMock(): Observable<{ ok: boolean; points: any[] }> {
    // return an array of records shaped like datasets.tdrive_raw_points
    const mock = {
      ok: true,
      points: [
        // taxi_1 trajectory (morning short trip)
        { id: 1001, taxi_id: 'taxi_1', timestamp: '2024-01-15T08:00:00Z', longitude: 2.3522, latitude: 48.8566 },
        { id: 1004, taxi_id: 'taxi_1', timestamp: '2024-01-15T08:05:00Z', longitude: 2.3530, latitude: 48.8569 },
        { id: 1005, taxi_id: 'taxi_1', timestamp: '2024-01-15T08:10:00Z', longitude: 2.3540, latitude: 48.8572 },
        // taxi_2 trajectory (later morning trip)
        { id: 1002, taxi_id: 'taxi_2', timestamp: '2024-01-15T09:30:00Z', longitude: 2.2945, latitude: 48.8584 },
        { id: 1006, taxi_id: 'taxi_2', timestamp: '2024-01-15T09:35:00Z', longitude: 2.2952, latitude: 48.8581 },
        { id: 1007, taxi_id: 'taxi_2', timestamp: '2024-01-15T09:40:00Z', longitude: 2.2960, latitude: 48.8578 },
        { id: 1008, taxi_id: 'taxi_2', timestamp: '2024-01-15T09:45:00Z', longitude: 2.2968, latitude: 48.8575 },
        // taxi_3 trajectory (early/overlapping times)
        { id: 1003, taxi_id: 'taxi_3', timestamp: '2024-01-15T07:50:00Z', longitude: 2.3530, latitude: 48.8570 },
        { id: 1009, taxi_id: 'taxi_3', timestamp: '2024-01-15T08:20:00Z', longitude: 2.3545, latitude: 48.8565 }
      ]
    };
    return of(mock).pipe(delay(500));
  }

  /**
   * Normalise un point au format T-Drive vers une forme plus simple attendue
   * par le frontend : { id, taxi_id, timestamp, lat, lon, is_valid }
   * Supporte plusieurs variantes de stockage des coordonnées (latitude/longitude,
   * GeoJSON dans `geom` ou WKT dans `geom`).
   */
  normalizeTdrivePoint(raw: any) {
    // raw may contain latitude/longitude or a geom field (GeoJSON or WKT)
    let lat: number | null = null;
    let lon: number | null = null;
    if (typeof raw.latitude === 'number' && typeof raw.longitude === 'number') {
      lat = raw.latitude;
      lon = raw.longitude;
    } else if (raw.geom) {
      // if geom is an object (GeoJSON)
      if (raw.geom.type === 'Point' && Array.isArray(raw.geom.coordinates)) {
        lon = raw.geom.coordinates[0];
        lat = raw.geom.coordinates[1];
      } else if (typeof raw.geom === 'string') {
        // try to parse WKT: POINT(lon lat)
        const m = raw.geom.match(/POINT\s*\(\s*([\d.\-]+)\s+([\d.\-]+)\s*\)/i);
        if (m) {
          lon = parseFloat(m[1]);
          lat = parseFloat(m[2]);
        }
      }
    }

    return {
      id: raw.id ?? null,
      taxi_id: raw.taxi_id ?? raw.taxiId ?? raw.user_id ?? String(raw.taxi_id ?? raw.user_id ?? raw.id ?? ''),
      timestamp: raw.timestamp ?? raw.time ?? null,
      lat,
      lon,
      is_valid: raw.is_valid ?? true,
      raw
    };
  }

  // In future we can add a real method using HttpClient to call the backend.
}
