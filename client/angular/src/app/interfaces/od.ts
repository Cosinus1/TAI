export interface GeoPoint {
  name: string;
  lat: number;
  lng: number;
}

export interface ODPair {
  origin: GeoPoint;
  destination: GeoPoint;
}
