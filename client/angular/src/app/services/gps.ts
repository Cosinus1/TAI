import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import{ Observable } from 'rxjs';
import {GpsPoint, PaginatedResponse, Bbox, GeoJsonFeatureCollection, Taxi, GeoJsonFeature, TaxiFeatureCollectionResponse} from '../interfaces/gps';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root',
})

export class Gps {
  private readonly apiUrl = `${environment.backendPrefix}/api/tdrive`;

  constructor(private http: HttpClient) {}

  getPoints(limit = 1000): Observable<PaginatedResponse<GpsPoint>> {
    const url = `${this.apiUrl}/points/?limit=${encodeURIComponent(limit)}`;
    return this.http.get<PaginatedResponse<GpsPoint>>(url);
  }

  getPointsInBbox(
    bbox: Bbox,
    limit = 1000
  ): Observable<{
    type: 'FeatureCollection';
    count: number;
    features: GeoJsonFeatureCollection;
  }> {
    return this.http.post<{
      type: 'FeatureCollection';
      count: number;
      features: GeoJsonFeatureCollection;
    }>(
      `${this.apiUrl}/points/in_bbox/`,
      {
        min_lon: bbox.minLon,
        max_lon: bbox.maxLon,
        min_lat: bbox.minLat,
        max_lat: bbox.maxLat,
        limit,
        only_valid: true,
      }
    );
  }

getPointsByTaxi(taxiId: string,limit = 1000): Observable<TaxiFeatureCollectionResponse> {
  return this.http.get<TaxiFeatureCollectionResponse>(
    `${this.apiUrl}/points/by_taxi/?taxi_id=${taxiId}&limit=${limit}`
  );
}

  getTaxis(): Observable<Taxi[]> {
    return this.http.get<Taxi[]>(`${this.apiUrl}/taxis/`);
  }
}