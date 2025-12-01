import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import{ Observable } from 'rxjs';
import {GpsFeature, FeatureCollection, Bbox} from '../interfaces/gps';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root',
})

export class Gps {
  private readonly apiUrl = `${environment.backendPrefix}/api/tdrive`;

  constructor(private http: HttpClient) {}

  getPoints(limit = 1000): Observable<FeatureCollection<GpsFeature>> {
    const url = `${this.apiUrl}/points/?limit=${encodeURIComponent(limit)}`;
    return this.http.get<FeatureCollection<GpsFeature>>(url);
  }

  getPointsInBbox(bbox: Bbox, limit = 1000): Observable<FeatureCollection<GpsFeature>> {
    const url = `${this.apiUrl}/points/in_bbox/`;
    const body = {
      min_lon: bbox.minLon,
      max_lon: bbox.maxLon,
      min_lat: bbox.minLat,
      max_lat: bbox.maxLat,
      limit,
      only_valid: true,
    };
    return this.http.post<FeatureCollection<GpsFeature>>(url, body);
  }

  getPointsByTaxi(taxiId: string, limit = 1000): Observable<FeatureCollection<GpsFeature>> {
    const url = `${this.apiUrl}/points/by_taxi/?taxi_id=${encodeURIComponent(taxiId)}&limit=${encodeURIComponent(limit)}`;
    return this.http.get<FeatureCollection<GpsFeature>>(url);
  }
}