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
    const mock = {
      ok: true,
      point: {
        user_id: 1,
        timestamp: '2024-01-15T08:30:00Z',
        latitude: 48.8566,
        longitude: 2.3522,
        altitude: 35.0,
        speed: 5.2,
        accuracy: 10.0
      }
    };
    // simulate 300-800ms latency
    return of(mock).pipe(delay(400));
  }

  /**
   * Return multiple mocked taxi points (as the backend might eventually provide).
   * Shape: { ok: true, points: [ {...}, ... ] }
   */
  getSampleTaxiPointsMock(): Observable<{ ok: boolean; points: any[] }> {
    const mock = {
      ok: true,
      points: [
        {
          user_id: 1,
          timestamp: '2024-01-15T08:30:00Z',
          latitude: 48.8566,
          longitude: 2.3522,
          altitude: 35.0,
          speed: 5.2,
          accuracy: 10.0
        },
        {
          user_id: 2,
          timestamp: '2024-01-15T09:15:00Z',
          latitude: 48.8584,
          longitude: 2.2945,
          altitude: 40.0,
          speed: 15.5,
          accuracy: 8.0
        },
        {
          user_id: 3,
          timestamp: '2024-01-15T08:31:00Z',
          latitude: 48.8570,
          longitude: 2.3530,
          altitude: 36.0,
          speed: 6.1,
          accuracy: 12.0
        }
      ]
    };
    return of(mock).pipe(delay(500));
  }

  // In future we can add a real method using HttpClient to call the backend.
}
