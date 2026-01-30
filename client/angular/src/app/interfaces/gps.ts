// client/angular/src/app/interfaces/gps.ts
/**
 * Updated interfaces for the refactored generic mobility API
 * Supports both proper GeoJSON and WKT geometry formats from the server
 */

// ============================================================================
// Dataset Interfaces
// ============================================================================

export interface Dataset {
  id: string; // UUID
  name: string;
  description?: string;
  dataset_type: 'gps_trace' | 'od_matrix' | 'trajectory' | 'stop_event' | 'custom';
  data_format: 'csv' | 'txt' | 'json' | 'geojson' | 'shapefile' | 'api';
  field_mapping: Record<string, string>;
  source_url?: string;
  geographic_scope?: string;
  temporal_range_start?: string;
  temporal_range_end?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  total_points?: number;
  total_entities?: number;
}

// ============================================================================
// GPS Point Interfaces
// ============================================================================

export interface GpsPoint {
  id: number;
  dataset: string; // UUID
  dataset_name?: string;
  entity_id: string;
  timestamp: string;
  longitude: number;
  latitude: number;
  altitude?: number;
  accuracy?: number;
  speed?: number;
  heading?: number;
  is_valid: boolean;
  extra_attributes?: Record<string, any>;
  imported_at?: string;
}

/**
 * Properly parsed GeoJSON feature
 */
export interface GeoJsonFeature {
  id: number;
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number]; // [longitude, latitude]
  } | null;
  properties: {
    dataset?: string;
    dataset_name?: string;
    entity_id: string;
    timestamp: string;
    longitude: number;
    latitude: number;
    altitude?: number;
    speed?: number;
    heading?: number;
    is_valid: boolean;
    extra_attributes?: Record<string, any>;
  };
}

// ============================================================================
// Trajectory Interfaces
// ============================================================================

export interface Trajectory {
  id: number;
  dataset: string; // UUID
  dataset_name?: string;
  entity_id: string;
  trajectory_date: string; // YYYY-MM-DD
  start_time: string;
  end_time: string;
  duration_seconds?: number;
  point_count: number;
  total_distance_meters?: number;
  avg_speed?: number;
  max_speed_kmh?: number;
  metrics?: Record<string, any>;
  created_at: string;
}

export interface TrajectoryGeoJson {
  id: number;
  type: 'Feature';
  geometry: {
    type: 'LineString';
    coordinates: [number, number][]; // Array of [lon, lat]
  } | null;
  properties: Omit<Trajectory, 'id'>;
}

// ============================================================================
// Import Job Interfaces
// ============================================================================

export interface ImportJob {
  id: string; // UUID
  dataset: string; // UUID
  dataset_name?: string;
  source_type: 'file' | 'directory' | 'url' | 'api';
  source_path: string;
  import_config: Record<string, any>;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  total_records?: number;
  processed_records: number;
  successful_records: number;
  failed_records: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  error_message?: string;
  success_rate: number;
  validation_errors?: ValidationError[];
}

export interface ValidationError {
  id: number;
  record_number?: number;
  error_type: string;
  error_message: string;
  field_name?: string;
  expected_value?: string;
  actual_value?: string;
  created_at: string;
}

export interface ImportJobCreate {
  dataset_id: string; // UUID
  source_type: 'file' | 'directory' | 'url' | 'api';
  source_path: string;
  field_mapping?: Record<string, string>;
  validation_config?: {
    strict_mode?: boolean;
    coordinate_bounds?: [number, number, number, number]; // [minLon, minLat, maxLon, maxLat]
    speed_threshold?: number;
  };
  file_format?: 'csv' | 'txt' | 'json' | 'geojson';
  delimiter?: string;
  skip_header?: boolean;
  max_files?: number;
}

// ============================================================================
// Entity Statistics Interfaces
// ============================================================================

export interface EntityStatistics {
  entity_id: string;
  entity_type?: string;
  total_points: number;
  first_timestamp: string;
  last_timestamp: string;
  active_days: number;
  avg_points_per_day: number;
  total_distance_meters?: number;
  avg_speed?: number;  // Server returns avg_speed (not avg_speed)
  max_speed?: number;  // Server returns max_speed (not max_speed_kmh)
  min_speed?: number;  // Server returns min_speed (not min_speed_kmh)
  total_trajectories?: number;
  avg_trajectory_distance?: number;
}

export interface DatasetStatistics {
  dataset_id: string;
  dataset_name: string;
  total_points: number;
  total_entities: number;
  total_trajectories: number;
  date_range: {
    start: string;
    end: string;
  };
  validity_rate: number;
  valid_points: number;
  invalid_points: number;
  avg_speed?: number;
  geographic_bounds?: {
    min_lon: number;
    max_lon: number;
    min_lat: number;
    max_lat: number;
  };
  entity_type_breakdown?: {
    [key: string]: {
      point_count: number;
      entity_count: number;
      avg_speed: number;
    };
  };
}

// ============================================================================
// Query Parameter Interfaces
// ============================================================================

export interface GpsPointQuery {
  dataset?: string; // UUID
  entity_id?: string;
  entity_type?: string;
  start_time?: string; // ISO 8601
  end_time?: string; // ISO 8601
  min_lon?: number;
  max_lon?: number;
  min_lat?: number;
  max_lat?: number;
  min_speed?: number;
  max_speed?: number;
  only_valid?: boolean;
  limit?: number;
}

export interface TrajectoryQuery {
  dataset?: string; // UUID
  entity_id?: string;
  date?: string; // YYYY-MM-DD
  start_date?: string; // YYYY-MM-DD
  end_date?: string; // YYYY-MM-DD
  min_distance?: number;
  max_distance?: number;
}

export interface Bbox {
  minLon: number;
  maxLon: number;
  minLat: number;
  maxLat: number;
}

// ============================================================================
// Pagination Interfaces
// ============================================================================

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
