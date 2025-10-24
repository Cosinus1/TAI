import { Injectable } from '@angular/core';
import { of, Observable } from 'rxjs';
import { delay } from 'rxjs/operators';

/**
 * TaxiService provides a mock taxi point for development when backend is unavailable.
 * The mock data mirrors the sample in `server/database/sample_data/sample_gps_traces.json`.
 */
@Injectable({ providedIn: 'root' })
export class TaxiService {
  /**
   * Return a mocked response identical to the Django endpoint shape: { ok: true, point: {...} }
   * Delays the response a bit to simulate network latency.
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
   * Return multiple mocked taxi points (as the backend might eventually provide).
   * Shape: { ok: true, points: [ {...}, ... ] }
   */
  getSampleTaxiPointsMock(): Observable<{ ok: boolean; points: any[] }> {
    // return an array of records shaped like datasets.tdrive_raw_points
    const mock = {
      ok: true,
      points: [
        // taxi_1 trajectory (3 points)
        { id: 1001, taxi_id: 'taxi_1', timestamp: '2024-01-15T08:30:00Z', longitude: 2.3522, latitude: 48.8566 },
        { id: 1004, taxi_id: 'taxi_1', timestamp: '2024-01-15T08:31:10Z', longitude: 2.3530, latitude: 48.8569 },
        { id: 1005, taxi_id: 'taxi_1', timestamp: '2024-01-15T08:32:30Z', longitude: 2.3540, latitude: 48.8572 },
        // taxi_2 trajectory (4 points)
        { id: 1002, taxi_id: 'taxi_2', timestamp: '2024-01-15T09:15:00Z', longitude: 2.2945, latitude: 48.8584 },
        { id: 1006, taxi_id: 'taxi_2', timestamp: '2024-01-15T09:16:05Z', longitude: 2.2952, latitude: 48.8581 },
        { id: 1007, taxi_id: 'taxi_2', timestamp: '2024-01-15T09:17:30Z', longitude: 2.2960, latitude: 48.8578 },
        { id: 1008, taxi_id: 'taxi_2', timestamp: '2024-01-15T09:18:45Z', longitude: 2.2968, latitude: 48.8575 },
        // taxi_3 trajectory (2 points)
        { id: 1003, taxi_id: 'taxi_3', timestamp: '2024-01-15T08:31:00Z', longitude: 2.3530, latitude: 48.8570 },
        { id: 1009, taxi_id: 'taxi_3', timestamp: '2024-01-15T08:33:25Z', longitude: 2.3545, latitude: 48.8565 }
      ]
    };
    return of(mock).pipe(delay(500));
  }

  /**
   * Helper to convert a tdrive-style raw point to a normalized frontend point
   * { id, taxi_id, timestamp, lat, lon, is_valid }
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
