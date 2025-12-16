export interface GpsPoint {
  id: number;
  taxi_id: string;
  timestamp: string;
  longitude: number;
  latitude: number;
  is_valid: boolean;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface GeoJsonFeature {
  id: number;
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  } | null;
  properties: {
    taxi_id: string;
    timestamp: string;
    longitude: number;
    latitude: number;
    is_valid: boolean;
  };
}


export interface GeoJsonFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJsonFeature[];
}

export interface Bbox {
  minLon: number;
  maxLon: number;
  minLat: number;
  maxLat: number;
}
