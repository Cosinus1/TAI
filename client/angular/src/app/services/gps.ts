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

  getDatasets(params?: any): Observable<PaginatedResponse<Dataset>> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<PaginatedResponse<Dataset>>(`${this.apiUrl}/datasets/`, { params: httpParams });
  }

  getDataset(id: string): Observable<Dataset> {
    return this.http.get<Dataset>(`${this.apiUrl}/datasets/${id}/`);
  }

  deleteDataset(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/datasets/${id}/`);
  }

  getPoints(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<any>(`${this.apiUrl}/points/`, { params: httpParams });
  }

  getTrajectories(params?: any): Observable<any> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<any>(`${this.apiUrl}/trajectories/`, { params: httpParams });
  }

  getEnhancedTrajectoryAnalysis(trajectoryId: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/trajectories/${trajectoryId}/enhanced_analysis/`);
  }

  calculateEnhancedTrajectories(datasetId: string, entityId?: string): Observable<any> {
    const body: any = { dataset: datasetId };
    if (entityId) {
      body.entity_id = entityId;
    }
    return this.http.post<any>(`${this.apiUrl}/trajectories/calculate_enhanced/`, body);
  }

  calculateSpeedBetweenPoints(point1Id: number, point2Id: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/trajectories/calculate_speed_between_points/`, {
      point1_id: point1Id,
      point2_id: point2Id
    });
  }

  interpolateTrajectory(entityId: string, datasetId: string, date: string, intervalSeconds: number = 60): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/trajectories/interpolate_trajectory/`, {
      entity_id: entityId,
      dataset: datasetId,
      date: date,
      interval_seconds: intervalSeconds
    });
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
    const httpParams = new HttpParams().set('dataset', datasetId);
    return this.http.get<string[]>(`${this.apiUrl}/points/entity_types/`, { params: httpParams });
  }

  getDatasetStatistics(datasetId: string): Observable<DatasetStatistics> {
    return this.http.get<DatasetStatistics>(`${this.apiUrl}/datasets/${datasetId}/statistics/`);
  }
}