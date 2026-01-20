// client/angular/src/app/services/gps.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import {
  Dataset,
  GpsPoint,
  GeoJsonFeatureCollection,
  Trajectory,
  ImportJob,
  ImportJobCreate,
  EntityStatistics,
  DatasetStatistics,
  GpsPointQuery,
  TrajectoryQuery,
  PaginatedResponse,
  Bbox,
  entityToTaxi,
  Taxi
} from '../interfaces/gps';
import { environment } from '../../environments/environment';

/**
 * Service for interacting with the refactored mobility API
 */
@Injectable({
  providedIn: 'root',
})
export class Gps {
  private readonly apiUrl = `${environment.backendPrefix}/api`;

  constructor(private http: HttpClient) {}

  // ============================================================================
  // Dataset Management
  // ============================================================================

  /**
   * Get all datasets
   */
  getDatasets(params?: { is_active?: boolean; type?: string }): Observable<Dataset[]> {
    let httpParams = new HttpParams();
    if (params?.is_active !== undefined) {
      httpParams = httpParams.set('is_active', params.is_active.toString());
    }
    if (params?.type) {
      httpParams = httpParams.set('type', params.type);
    }
    return this.http.get<Dataset[]>(`${this.apiUrl}/datasets/`, { params: httpParams });
  }

  /**
   * Get a specific dataset by ID
   */
  getDataset(id: string): Observable<Dataset> {
    return this.http.get<Dataset>(`${this.apiUrl}/datasets/${id}/`);
  }

  /**
   * Get statistics for a specific dataset
   */
  getDatasetStatistics(id: string): Observable<DatasetStatistics> {
    return this.http.get<DatasetStatistics>(`${this.apiUrl}/datasets/${id}/statistics/`);
  }

  /**
   * Create a new dataset
   */
  createDataset(dataset: Partial<Dataset>): Observable<Dataset> {
    return this.http.post<Dataset>(`${this.apiUrl}/datasets/`, dataset);
  }

  /**
   * Update a dataset
   */
  updateDataset(id: string, dataset: Partial<Dataset>): Observable<Dataset> {
    return this.http.put<Dataset>(`${this.apiUrl}/datasets/${id}/`, dataset);
  }

  // ============================================================================
  // GPS Points
  // ============================================================================

  /**
   * Get GPS points with pagination
   */
  getPoints(params?: {
    dataset?: string;
    entity_id?: string;
    start_time?: string;
    end_time?: string;
    only_valid?: boolean;
    page?: number;
    page_size?: number;
  }): Observable<PaginatedResponse<GpsPoint>> {
    let httpParams = new HttpParams();
    
    if (params?.dataset) httpParams = httpParams.set('dataset', params.dataset);
    if (params?.entity_id) httpParams = httpParams.set('entity_id', params.entity_id);
    if (params?.start_time) httpParams = httpParams.set('start_time', params.start_time);
    if (params?.end_time) httpParams = httpParams.set('end_time', params.end_time);
    if (params?.only_valid !== undefined) {
      httpParams = httpParams.set('only_valid', params.only_valid.toString());
    }
    if (params?.page) httpParams = httpParams.set('page', params.page.toString());
    if (params?.page_size) httpParams = httpParams.set('page_size', params.page_size.toString());

    return this.http.get<PaginatedResponse<GpsPoint>>(
      `${this.apiUrl}/points/`,
      { params: httpParams }
    );
  }

  /**
   * Advanced query for GPS points with spatial filtering
   */
  queryPoints(query: GpsPointQuery): Observable<GeoJsonFeatureCollection> {
    return this.http.post<GeoJsonFeatureCollection>(
      `${this.apiUrl}/points/query/`,
      query
    );
  }

  /**
   * Get points in a bounding box
   */
  getPointsInBbox(
    bbox: Bbox,
    options?: {
      dataset?: string;
      entity_id?: string;
      limit?: number;
      only_valid?: boolean;
    }
  ): Observable<GeoJsonFeatureCollection> {
    const query: GpsPointQuery = {
      min_lon: bbox.minLon,
      max_lon: bbox.maxLon,
      min_lat: bbox.minLat,
      max_lat: bbox.maxLat,
      limit: options?.limit || 1000,
      only_valid: options?.only_valid !== false,
      dataset: options?.dataset,
      entity_id: options?.entity_id,
    };

    return this.queryPoints(query);
  }

  /**
   * Get points for a specific entity (taxi, vehicle, etc.)
   */
  getPointsByEntity(
    entityId: string,
    options?: {
      dataset?: string;
      start_time?: string;
      end_time?: string;
      limit?: number;
    }
  ): Observable<PaginatedResponse<GpsPoint>> {
    let httpParams = new HttpParams()
      .set('entity_id', entityId);

    if (options?.dataset) httpParams = httpParams.set('dataset', options.dataset);
    if (options?.start_time) httpParams = httpParams.set('start_time', options.start_time);
    if (options?.end_time) httpParams = httpParams.set('end_time', options.end_time);
    if (options?.limit) httpParams = httpParams.set('page_size', options.limit.toString());

    return this.http.get<PaginatedResponse<GpsPoint>>(
      `${this.apiUrl}/points/by_entity/`,
      { params: httpParams }
    );
  }

  /**
   * Get a single GPS point by ID
   */
  getPoint(id: number): Observable<GpsPoint> {
    return this.http.get<GpsPoint>(`${this.apiUrl}/points/${id}/`);
  }

  // ============================================================================
  // Trajectories
  // ============================================================================

  /**
   * Get trajectories with pagination
   */
  getTrajectories(params?: {
    dataset?: string;
    entity_id?: string;
    date?: string;
    page?: number;
    page_size?: number;
  }): Observable<PaginatedResponse<Trajectory>> {
    let httpParams = new HttpParams();
    
    if (params?.dataset) httpParams = httpParams.set('dataset', params.dataset);
    if (params?.entity_id) httpParams = httpParams.set('entity_id', params.entity_id);
    if (params?.date) httpParams = httpParams.set('date', params.date);
    if (params?.page) httpParams = httpParams.set('page', params.page.toString());
    if (params?.page_size) httpParams = httpParams.set('page_size', params.page_size.toString());

    return this.http.get<PaginatedResponse<Trajectory>>(
      `${this.apiUrl}/trajectories/`,
      { params: httpParams }
    );
  }

  /**
   * Advanced query for trajectories
   */
  queryTrajectories(query: TrajectoryQuery): Observable<PaginatedResponse<Trajectory>> {
    return this.http.post<PaginatedResponse<Trajectory>>(
      `${this.apiUrl}/trajectories/query/`,
      query
    );
  }

  /**
   * Get a single trajectory by ID
   */
  getTrajectory(id: number): Observable<Trajectory> {
    return this.http.get<Trajectory>(`${this.apiUrl}/trajectories/${id}/`);
  }

  /**
   * Analyze a trajectory
   */
  analyzeTrajectory(id: number): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/trajectories/${id}/analyze/`);
  }

  // ============================================================================
  // Import Jobs
  // ============================================================================

  /**
   * Get all import jobs
   */
  getImportJobs(params?: {
    dataset?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Observable<PaginatedResponse<ImportJob>> {
    let httpParams = new HttpParams();
    
    if (params?.dataset) httpParams = httpParams.set('dataset', params.dataset);
    if (params?.status) httpParams = httpParams.set('status', params.status);
    if (params?.page) httpParams = httpParams.set('page', params.page.toString());
    if (params?.page_size) httpParams = httpParams.set('page_size', params.page_size.toString());

    return this.http.get<PaginatedResponse<ImportJob>>(
      `${this.apiUrl}/imports/`,
      { params: httpParams }
    );
  }

  /**
   * Get a specific import job
   */
  getImportJob(id: string): Observable<ImportJob> {
    return this.http.get<ImportJob>(`${this.apiUrl}/imports/${id}/`);
  }

  /**
   * Start a new import job
   */
  startImport(importConfig: ImportJobCreate): Observable<ImportJob> {
    return this.http.post<ImportJob>(
      `${this.apiUrl}/imports/start_import/`,
      importConfig
    );
  }

  /**
   * Get import job progress
   */
  getImportProgress(id: string): Observable<{
    id: string;
    status: string;
    progress_percentage: number;
    processed_records: number;
    successful_records: number;
    failed_records: number;
    total_records?: number;
    started_at?: string;
    duration_seconds?: number;
  }> {
    return this.http.get<any>(`${this.apiUrl}/imports/${id}/progress/`);
  }

  // ============================================================================
  // Entity Statistics
  // ============================================================================

  /**
   * Get all entities with statistics
   */
  getEntities(params?: {
    dataset?: string;
    min_points?: number;
  }): Observable<EntityStatistics[]> {
    let httpParams = new HttpParams();
    
    if (params?.dataset) httpParams = httpParams.set('dataset', params.dataset);
    if (params?.min_points) httpParams = httpParams.set('min_points', params.min_points.toString());

    return this.http.get<EntityStatistics[]>(
      `${this.apiUrl}/entities/`,
      { params: httpParams }
    );
  }

  /**
   * Get statistics for a specific entity
   */
  getEntityStatistics(entityId: string, datasetId?: string): Observable<EntityStatistics> {
    let httpParams = new HttpParams();
    if (datasetId) {
      httpParams = httpParams.set('dataset', datasetId);
    }

    return this.http.get<EntityStatistics>(
      `${this.apiUrl}/entities/${entityId}/`,
      { params: httpParams }
    );
  }

  // ============================================================================
  // Legacy Compatibility Methods (for T-Drive migration)
  // ============================================================================

  /**
   * @deprecated Use getPointsByEntity() instead
   * Get points by taxi ID for backward compatibility
   */
  getPointsByTaxi(
    taxiId: string,
    limit: number = 1000,
    datasetId?: string
  ): Observable<PaginatedResponse<GpsPoint>> {
    return this.getPointsByEntity(taxiId, {
      dataset: datasetId,
      limit: limit
    });
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  /**
   * Get the default T-Drive dataset (for migration)
   */
  getTDriveDataset(): Observable<Dataset> {
    return this.getDatasets({ type: 'gps_trace' }).pipe(
      map(datasets => {
        const tdriveDataset = datasets.find(d => 
          d.name.toLowerCase().includes('t-drive') || 
          d.name.toLowerCase().includes('tdrive')
        );
        if (!tdriveDataset && datasets.length > 0) {
          return datasets[0]; // Fallback to first dataset
        }
        if (!tdriveDataset) {
          throw new Error('No T-Drive dataset found');
        }
        return tdriveDataset;
      })
    );
  }
}