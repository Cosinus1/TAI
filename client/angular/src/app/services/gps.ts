// client/angular/src/app/services/gps.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

import { 
  Dataset, 
  GpsPoint, 
  Trajectory, 
  EntityStatistics, 
  DatasetStatistics, 
  PaginatedResponse } from '../interfaces/gps';

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

  getPoints(params?: any): Observable<PaginatedResponse<GpsPoint>> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<PaginatedResponse<GpsPoint>>(`${this.apiUrl}/points/`, { params: httpParams });
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

  getEntityTypes(datasetId: string): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/points/entity_types/`, {
      params: { dataset: datasetId }
    });
  }

  getDatasetStatistics(datasetId: string): Observable<DatasetStatistics> {
    return this.http.get<DatasetStatistics>(`${this.apiUrl}/datasets/${datasetId}/statistics/`);
  }
}