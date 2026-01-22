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
 * Extended Dataset Statistics with entity type breakdown
 */
export interface ExtendedDatasetStatistics extends DatasetStatistics {
  avg_speed?: number;
  entity_type_breakdown?: {
    [key: string]: {
      point_count: number;
      entity_count: number;
      avg_speed: number;
    };
  };
}

/**
 * Extended Entity Statistics with entity type
 */
export interface ExtendedEntityStatistics extends EntityStatistics {
  entity_type?: string;
  max_speed?: number;
  min_speed?: number;
}

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
    
    return this.http.get<PaginatedResponse<Dataset> | Dataset[]>(
      `${this.apiUrl}/datasets/`, 
      { params: httpParams }
    ).pipe(
      map(response => {
        if (response && typeof response === 'object' && 'results' in response) {
          return (response as PaginatedResponse<Dataset>).results;
        }
        return response as Dataset[];
      })
    );
  }

  /**
   * Get a specific dataset by ID
   */
  getDataset(id: string): Observable<Dataset> {
    return this.http.get<Dataset>(`${this.apiUrl}/datasets/${id}/`);
  }

  /**
   * Get statistics for a specific dataset (extended with entity type breakdown)
   */
  getDatasetStatistics(id: string): Observable<ExtendedDatasetStatistics> {
    return this.http.get<ExtendedDatasetStatistics>(`${this.apiUrl}/datasets/${id}/statistics/`);
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
  // GPS Points with Filtering
  // ============================================================================

  /**
   * Get GPS points with pagination and filtering
   */
  getPoints(params?: {
    dataset?: string;
    entity_id?: string;
    entity_type?: string;
    start_time?: string;
    end_time?: string;
    min_speed?: number;
    max_speed?: number;
    only_valid?: boolean;
    page?: number;
    page_size?: number;
  }): Observable<PaginatedResponse<GpsPoint>> {
    let httpParams = new HttpParams();
    
    if (params?.dataset) httpParams = httpParams.set('dataset', params.dataset);
    if (params?.entity_id) httpParams = httpParams.set('entity_id', params.entity_id);
    if (params?.entity_type) httpParams = httpParams.set('entity_type', params.entity_type);
    if (params?.start_time) httpParams = httpParams.set('start_time', params.start_time);
    if (params?.end_time) httpParams = httpParams.set('end_time', params.end_time);
    if (params?.min_speed !== undefined) httpParams = httpParams.set('min_speed', params.min_speed.toString());
    if (params?.max_speed !== undefined) httpParams = httpParams.set('max_speed', params.max_speed.toString());
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
   * Advanced query for GPS points with spatial and entity type filtering
   */
  queryPoints(query: GpsPointQuery & { entity_type?: string }): Observable<GeoJsonFeatureCollection> {
    return this.http.post<GeoJsonFeatureCollection>(
      `${this.apiUrl}/points/query/`,
      query
    );
  }

  /**
   * Get points in a bounding box with optional entity type filter
   */
  getPointsInBbox(
    bbox: Bbox,
    options?: {
      dataset?: string;
      entity_id?: string;
      entity_type?: string;
      limit?: number;
      only_valid?: boolean;
    }
  ): Observable<GeoJsonFeatureCollection> {
    const query: GpsPointQuery & { entity_type?: string } = {
      min_lon: bbox.minLon,
      max_lon: bbox.maxLon,
      min_lat: bbox.minLat,
      max_lat: bbox.maxLat,
      limit: options?.limit || 1000,
      only_valid: options?.only_valid !== false,
      dataset: options?.dataset,
      entity_id: options?.entity_id,
    };
    
    if (options?.entity_type) {
      query.entity_type = options.entity_type;
    }

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
   * Get list of entity types in a dataset
   */
  getEntityTypes(datasetId?: string): Observable<string[]> {
    let httpParams = new HttpParams();
    if (datasetId) {
      httpParams = httpParams.set('dataset', datasetId);
    }
    return this.http.get<string[]>(
      `${this.apiUrl}/points/entity_types/`,
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
  // Entity Statistics with Entity Type Support
  // ============================================================================

  /**
   * Get all entities with statistics, optionally filtered by entity type
   */
  getEntities(params?: {
    dataset?: string;
    min_points?: number;
    entity_type?: string;
  }): Observable<ExtendedEntityStatistics[]> {
    let httpParams = new HttpParams();
    
    if (params?.dataset) httpParams = httpParams.set('dataset', params.dataset);
    if (params?.min_points) httpParams = httpParams.set('min_points', params.min_points.toString());
    if (params?.entity_type) httpParams = httpParams.set('entity_type', params.entity_type);

    return this.http.get<ExtendedEntityStatistics[]>(
      `${this.apiUrl}/entities/`,
      { params: httpParams }
    );
  }

  /**
   * Get statistics for a specific entity
   */
  getEntityStatistics(entityId: string, datasetId?: string): Observable<ExtendedEntityStatistics> {
    let httpParams = new HttpParams();
    if (datasetId) {
      httpParams = httpParams.set('dataset', datasetId);
    }

    return this.http.get<ExtendedEntityStatistics>(
      `${this.apiUrl}/entities/${entityId}/`,
      { params: httpParams }
    );
  }

  // ============================================================================
  // Legacy Compatibility Methods (for T-Drive migration)
  // ============================================================================

  /**
   * @deprecated Use getPointsByEntity() instead
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
        console.log('[Gps] Datasets received:', datasets);
        
        const tdriveDataset = datasets.find(d => 
          d.name.toLowerCase().includes('t-drive') || 
          d.name.toLowerCase().includes('tdrive')
        );
        
        if (!tdriveDataset && datasets.length > 0) {
          console.log('[Gps] T-Drive dataset not found, using first dataset');
          return datasets[0];
        }
        
        if (!tdriveDataset) {
          throw new Error('No T-Drive dataset found');
        }
        
        return tdriveDataset;
      })
    );
  }

  /**
   * Get the Paris test dataset
   */
  getParisTestDataset(): Observable<Dataset> {
    return this.getDatasets({ type: 'gps_trace' }).pipe(
      map(datasets => {
        const parisDataset = datasets.find(d => 
          d.name.toLowerCase().includes('paris')
        );
        
        if (!parisDataset) {
          throw new Error('Paris Test Dataset not found. Please run: python manage.py create_test_dataset');
        }
        
        return parisDataset;
      })
    );
  }
}