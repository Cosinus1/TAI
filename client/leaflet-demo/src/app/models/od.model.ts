export interface GeoPoint {
  name: string;
  lat: number;
  lng: number;
}

export interface ODPair {
  origin: GeoPoint;
  destination: GeoPoint;
}

export interface POI {
  name: string;
  type: 'restaurant' | 'cafe' | 'cinema' | string;
  lat: number;
  lng: number;
}
