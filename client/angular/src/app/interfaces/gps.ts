export interface GpsProperties {
  taxi_id?: string;
  timestamp?: string;
  is_valid?: boolean;
  [key: string]: any;
}

export interface GpsGeometry {
  type: 'Point';
  coordinates: [number, number]; // [lng, lat]
}

export interface GpsFeature {
  type: 'Feature';
  id?: number | string;
  geometry: GpsGeometry;
  properties: GpsProperties;
}

export interface FeatureCollection<T = GpsFeature> {
  type: 'FeatureCollection';
  features: T[];
  [key: string]: any;
}

export interface Bbox {
  minLon: number;
  maxLon: number;
  minLat: number;
  maxLat: number;
}