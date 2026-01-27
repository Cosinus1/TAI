// client/angular/src/app/services/geometry-parser.ts
import { Injectable } from '@angular/core';

/**
 * Parsed coordinate from WKT
 */
export interface ParsedCoordinate {
  longitude: number;
  latitude: number;
}

/**
 * Parsed GeoJSON feature with proper geometry
 */
export interface ParsedFeature {
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
    accuracy?: number;
    is_valid: boolean;
    extra_attributes?: Record<string, any>;
  };
}

/**
 * Parsed feature collection
 */
export interface ParsedFeatureCollection {
  type: 'FeatureCollection';
  count: number;
  features: ParsedFeature[];
}

/**
 * Service for parsing WKT geometry strings and transforming raw server data
 */
@Injectable({
  providedIn: 'root',
})
export class GeometryParser {
  
  /**
   * Parse a WKT POINT string to coordinates
   * Format: "SRID=4326;POINT (lng lat)" or "POINT(lng lat)"
   */
  parseWktPoint(wkt: string | null | undefined): ParsedCoordinate | null {
    if (!wkt || typeof wkt !== 'string') {
      return null;
    }

    try {
      // Remove SRID prefix if present
      let pointStr = wkt;
      if (pointStr.includes(';')) {
        pointStr = pointStr.split(';')[1];
      }

      // Extract coordinates from POINT(...) or POINT (...)
      const match = pointStr.match(/POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)/i);
      if (match) {
        const longitude = parseFloat(match[1]);
        const latitude = parseFloat(match[2]);
        
        if (!isNaN(longitude) && !isNaN(latitude)) {
          return { longitude, latitude };
        }
      }
    } catch (e) {
      console.warn('[GeometryParser] Failed to parse WKT:', wkt, e);
    }

    return null;
  }

  /**
   * Parse a WKT LINESTRING to coordinates array
   * Format: "SRID=4326;LINESTRING (lng1 lat1, lng2 lat2, ...)"
   */
  parseWktLineString(wkt: string | null | undefined): ParsedCoordinate[] {
    if (!wkt || typeof wkt !== 'string') {
      return [];
    }

    try {
      // Remove SRID prefix if present
      let lineStr = wkt;
      if (lineStr.includes(';')) {
        lineStr = lineStr.split(';')[1];
      }

      // Extract coordinates from LINESTRING(...)
      const match = lineStr.match(/LINESTRING\s*\(\s*(.+)\s*\)/i);
      if (match) {
        const coordsStr = match[1];
        const pairs = coordsStr.split(',');
        
        return pairs
          .map(pair => {
            const [lng, lat] = pair.trim().split(/\s+/).map(parseFloat);
            if (!isNaN(lng) && !isNaN(lat)) {
              return { longitude: lng, latitude: lat };
            }
            return null;
          })
          .filter((c): c is ParsedCoordinate => c !== null);
      }
    } catch (e) {
      console.warn('[GeometryParser] Failed to parse WKT LineString:', wkt, e);
    }

    return [];
  }

  /**
   * Transform a raw feature from the server into a properly parsed feature
   */
  parseFeature(rawFeature: any): ParsedFeature | null {
    if (!rawFeature) return null;

    const props = rawFeature.properties || {};
    
    // Try to get coordinates from multiple sources
    let longitude: number | null = null;
    let latitude: number | null = null;

    // 1. Try from properties (most reliable)
    if (typeof props.longitude === 'number' && typeof props.latitude === 'number') {
      longitude = props.longitude;
      latitude = props.latitude;
    }

    // 2. Try parsing WKT geometry string
    if (longitude === null || latitude === null) {
      const geom = rawFeature.geometry;
      if (typeof geom === 'string') {
        const parsed = this.parseWktPoint(geom);
        if (parsed) {
          longitude = parsed.longitude;
          latitude = parsed.latitude;
        }
      } else if (geom && geom.type === 'Point' && Array.isArray(geom.coordinates)) {
        longitude = geom.coordinates[0];
        latitude = geom.coordinates[1];
      }
    }

    // If we still don't have coordinates, skip this feature
    if (longitude === null || latitude === null) {
      return null;
    }

    return {
      id: rawFeature.id,
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [longitude, latitude]
      },
      properties: {
        ...props,
        longitude,
        latitude
      }
    };
  }

  /**
   * Transform a raw feature collection from the server
   * Handles multiple nested structures:
   * - Direct array
   * - { features: [...] }
   * - { features: { features: [...] } } (nested FeatureCollection)
   * - { results: { features: [...] } }
   */
  parseFeatureCollection(rawResponse: any): ParsedFeatureCollection {
    const features: ParsedFeature[] = [];

    // Handle different response structures
    let rawFeatures: any[] = [];
    
    if (Array.isArray(rawResponse)) {
      // Direct array of features
      rawFeatures = rawResponse;
    } else if (rawResponse?.features) {
      // Check if features is another FeatureCollection (nested structure)
      if (rawResponse.features?.features && Array.isArray(rawResponse.features.features)) {
        // Nested: { features: { type: 'FeatureCollection', features: [...] } }
        rawFeatures = rawResponse.features.features;
        console.log('[GeometryParser] Detected nested FeatureCollection structure');
      } else if (Array.isArray(rawResponse.features)) {
        // Standard: { features: [...] }
        rawFeatures = rawResponse.features;
      }
    } else if (rawResponse?.results?.features) {
      // Paginated: { results: { features: [...] } }
      if (Array.isArray(rawResponse.results.features)) {
        rawFeatures = rawResponse.results.features;
      } else if (rawResponse.results.features?.features) {
        // Nested paginated
        rawFeatures = rawResponse.results.features.features;
      }
    }

    console.log('[GeometryParser] Raw features to parse:', rawFeatures.length);

    for (const raw of rawFeatures) {
      const parsed = this.parseFeature(raw);
      if (parsed) {
        features.push(parsed);
      }
    }

    console.log('[GeometryParser] Successfully parsed features:', features.length);

    return {
      type: 'FeatureCollection',
      count: features.length,
      features
    };
  }

  /**
   * Extract entity type from a feature
   */
  getEntityType(feature: ParsedFeature | any): string {
    const props = feature?.properties || feature;
    
    // Try extra_attributes first
    if (props?.extra_attributes?.entity_type) {
      return props.extra_attributes.entity_type;
    }
    
    // Try to infer from entity_id
    if (props?.entity_id) {
      const prefix = props.entity_id.split('_')[0];
      if (['bike', 'bus', 'car', 'taxi'].includes(prefix)) {
        return prefix;
      }
    }
    
    return 'unknown';
  }

  /**
   * Group features by entity_id for trajectory rendering
   */
  groupByEntity(features: ParsedFeature[]): Map<string, ParsedFeature[]> {
    const groups = new Map<string, ParsedFeature[]>();
    
    for (const feature of features) {
      const entityId = feature.properties.entity_id;
      if (!entityId) continue;
      
      if (!groups.has(entityId)) {
        groups.set(entityId, []);
      }
      groups.get(entityId)!.push(feature);
    }
    
    // Sort each group by timestamp
    for (const [entityId, entityFeatures] of groups) {
      entityFeatures.sort((a, b) => {
        const timeA = new Date(a.properties.timestamp).getTime();
        const timeB = new Date(b.properties.timestamp).getTime();
        return timeA - timeB;
      });
    }
    
    return groups;
  }

  /**
   * Convert grouped features to trajectory lines
   */
  featuresToTrajectory(features: ParsedFeature[]): [number, number][] {
    return features
      .filter(f => f.geometry)
      .map(f => [f.geometry!.coordinates[1], f.geometry!.coordinates[0]] as [number, number]);
  }
}