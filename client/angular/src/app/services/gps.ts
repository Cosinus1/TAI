// client/angular/src/app/services/gps.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface GPSPoint {
  id: string;
  dataset: string;
  entity_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  altitude?: number;
  speed?: number;
  heading?: number;
  accuracy?: number;
  geom?: any;
  is_valid: boolean;
  validation_errors?: any;
}

export interface Trajectory {
  id: string;
  dataset: string;
  entity_id: string;
  trajectory_date: string;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  point_count: number;
  total_distance_meters: number;
  avg_speed_kmh?: number;
  max_speed_kmh?: number;
  geom?: any;
  metrics?: any;
}

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  dataset_type: string;
  geographic_scope?: string;
  is_active: boolean;
  created_at: string;
}

export interface EntityStatistics {
  entity_id: string;
  entity_type?: string;
  point_count: number;
  trajectory_count?: number;
  first_timestamp?: string;
  last_timestamp?: string;
  avg_speed?: number;
}

export interface ExtendedDatasetStatistics {
  dataset_name: string;
  total_points: number;
  total_entities: number;
  total_trajectories: number;
  valid_points: number;
  invalid_points: number;
  validity_rate: number;
  avg_speed?: number;
  date_range?: {
    start: string;
    end: string;
  };
  entity_type_breakdown?: {
    [key: string]: {
      entity_count: number;
      point_count: number;
      avg_speed: number;
    };
  };
  geographic_bounds?: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  };
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

@Injectable({
  providedIn: 'root'
})
export class Gps {
  private http = inject(HttpClient);
  private readonly apiUrl = `${environment.backendPrefix}/api`;


  getDatasets(params?: any): Observable<Dataset[]> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<Dataset[]>(`${this.apiUrl}/datasets/`, { params: httpParams });
  }

  getDataset(id: string): Observable<Dataset> {
    return this.http.get<Dataset>(`${this.apiUrl}/datasets/${id}/`);
  }

  deleteDataset(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/datasets/${id}/`);
  }

  getPoints(params?: any): Observable<PaginatedResponse<GPSPoint>> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<PaginatedResponse<GPSPoint>>(`${this.apiUrl}/gps-points/`, { params: httpParams });
  }

  getTrajectories(params?: any): Observable<PaginatedResponse<Trajectory>> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<PaginatedResponse<Trajectory>>(`${this.apiUrl}/trajectories/`, { params: httpParams });
  }

  getEntities(params?: any): Observable<EntityStatistics[]> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<EntityStatistics[]>(`${this.apiUrl}/entities/`, { params: httpParams });
  }

  getDatasetStatistics(datasetId: string): Observable<ExtendedDatasetStatistics> {
    return this.http.get<ExtendedDatasetStatistics>(`${this.apiUrl}/datasets/${datasetId}/statistics/`);
  }
}