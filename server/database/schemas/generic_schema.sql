-- ============================================================================
-- Urban Mobility Analysis - Generalized Database Schema
-- ============================================================================
-- Purpose: Flexible schema for storing diverse mobility datasets
-- Supports: Multiple formats, entity types, and data sources
-- ============================================================================

-- Enable PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Dataset Registry
-- Stores metadata about each imported dataset
CREATE TABLE IF NOT EXISTS mobility_dataset (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    
    -- Dataset classification
    dataset_type VARCHAR(50) NOT NULL, -- 'gps_trace', 'od_matrix', 'trajectory', 'stop_event'
    data_format VARCHAR(50) NOT NULL,  -- 'csv', 'txt', 'json', 'geojson', 'shapefile'
    
    -- Field mapping (stores JSON mapping of source -> standard fields)
    field_mapping JSONB DEFAULT '{}',
    
    -- Metadata
    source_url TEXT,
    geographic_scope VARCHAR(255),
    temporal_range_start TIMESTAMPTZ,
    temporal_range_end TIMESTAMPTZ,
    
    -- Entity information
    entity_type VARCHAR(50), -- 'taxi', 'car', 'bike', 'person', 'bus', etc.
    entity_count INTEGER,
    
    -- System fields
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Storage statistics
    total_points BIGINT DEFAULT 0,
    total_trajectories INTEGER DEFAULT 0,
    storage_size_bytes BIGINT
);

CREATE INDEX idx_dataset_type ON mobility_dataset(dataset_type);
CREATE INDEX idx_dataset_active ON mobility_dataset(is_active);
CREATE INDEX idx_dataset_temporal ON mobility_dataset(temporal_range_start, temporal_range_end);

-- GPS Points - Core mobility data storage
CREATE TABLE IF NOT EXISTS mobility_gpspoint (
    id BIGSERIAL PRIMARY KEY,
    
    -- Dataset reference
    dataset_id UUID NOT NULL REFERENCES mobility_dataset(id) ON DELETE CASCADE,
    
    -- Entity identification
    entity_id VARCHAR(100) NOT NULL,
    
    -- Temporal data
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Spatial data (WGS84)
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    geom GEOMETRY(Point, 4326),
    
    -- Optional attributes
    altitude DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    heading DOUBLE PRECISION CHECK (heading IS NULL OR (heading >= 0 AND heading <= 360)),
    
    -- Flexible attributes (dataset-specific fields)
    extra_attributes JSONB DEFAULT '{}',
    
    -- Quality control
    is_valid BOOLEAN DEFAULT TRUE,
    validation_flags JSONB DEFAULT '{}',
    
    -- System fields
    imported_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicates within dataset
    CONSTRAINT unique_dataset_entity_timestamp UNIQUE (dataset_id, entity_id, timestamp)
);

-- Optimized indexes for common query patterns
CREATE INDEX idx_gps_dataset ON mobility_gpspoint(dataset_id);
CREATE INDEX idx_gps_entity ON mobility_gpspoint(entity_id);
CREATE INDEX idx_gps_timestamp ON mobility_gpspoint(timestamp);
CREATE INDEX idx_gps_dataset_entity_time ON mobility_gpspoint(dataset_id, entity_id, timestamp);
CREATE INDEX idx_gps_geom ON mobility_gpspoint USING GIST(geom);
CREATE INDEX idx_gps_valid ON mobility_gpspoint(is_valid) WHERE is_valid = TRUE;
CREATE INDEX idx_gps_extra_attrs ON mobility_gpspoint USING GIN(extra_attributes);

-- Trajectories - Aggregated movement data
CREATE TABLE IF NOT EXISTS mobility_trajectory (
    id BIGSERIAL PRIMARY KEY,
    
    -- Dataset reference
    dataset_id UUID NOT NULL REFERENCES mobility_dataset(id) ON DELETE CASCADE,
    
    -- Entity identification
    entity_id VARCHAR(100) NOT NULL,
    trajectory_date DATE NOT NULL,
    
    -- Temporal bounds
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_seconds INTEGER,
    
    -- Statistics
    point_count INTEGER NOT NULL,
    total_distance_meters DOUBLE PRECISION,
    avg_speed_kmh DOUBLE PRECISION,
    max_speed_kmh DOUBLE PRECISION,
    
    -- Geometry
    geom GEOMETRY(LineString, 4326),
    bbox GEOMETRY(Polygon, 4326),
    
    -- Computed metrics (flexible storage)
    metrics JSONB DEFAULT '{}',
    
    -- System fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_dataset_entity_date UNIQUE (dataset_id, entity_id, trajectory_date)
);

CREATE INDEX idx_traj_dataset ON mobility_trajectory(dataset_id);
CREATE INDEX idx_traj_entity ON mobility_trajectory(entity_id);
CREATE INDEX idx_traj_date ON mobility_trajectory(trajectory_date);
CREATE INDEX idx_traj_dataset_entity ON mobility_trajectory(dataset_id, entity_id);
CREATE INDEX idx_traj_geom ON mobility_trajectory USING GIST(geom);
CREATE INDEX idx_traj_bbox ON mobility_trajectory USING GIST(bbox);

-- ============================================================================
-- IMPORT MANAGEMENT TABLES
-- ============================================================================

-- Import Jobs - Track data ingestion operations
CREATE TABLE IF NOT EXISTS mobility_importjob (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Dataset reference
    dataset_id UUID NOT NULL REFERENCES mobility_dataset(id) ON DELETE CASCADE,
    
    -- Source information
    source_type VARCHAR(50) NOT NULL, -- 'file', 'directory', 'url', 'api'
    source_path TEXT NOT NULL,
    import_config JSONB DEFAULT '{}',
    
    -- Progress tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed', 'cancelled'
    total_records INTEGER,
    processed_records INTEGER DEFAULT 0,
    successful_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds DOUBLE PRECISION,
    
    -- Error tracking
    error_message TEXT
);

CREATE INDEX idx_import_dataset ON mobility_importjob(dataset_id);
CREATE INDEX idx_import_status ON mobility_importjob(status);
CREATE INDEX idx_import_created ON mobility_importjob(created_at DESC);

-- Validation Errors - Record data quality issues
CREATE TABLE IF NOT EXISTS mobility_validationerror (
    id BIGSERIAL PRIMARY KEY,
    
    -- Import reference
    import_job_id UUID NOT NULL REFERENCES mobility_importjob(id) ON DELETE CASCADE,
    
    -- Error details
    record_number INTEGER,
    raw_data TEXT,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    
    -- Context
    field_name VARCHAR(100),
    expected_value VARCHAR(255),
    actual_value VARCHAR(255),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_val_import ON mobility_validationerror(import_job_id);
CREATE INDEX idx_val_type ON mobility_validationerror(error_type);

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- Dataset Statistics (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dataset_statistics AS
SELECT 
    d.id AS dataset_id,
    d.name AS dataset_name,
    d.dataset_type,
    d.entity_type,
    
    -- Point statistics
    COUNT(DISTINCT g.entity_id) AS unique_entities,
    COUNT(g.id) AS total_points,
    COUNT(CASE WHEN g.is_valid THEN 1 END) AS valid_points,
    
    -- Temporal coverage
    MIN(g.timestamp) AS first_timestamp,
    MAX(g.timestamp) AS last_timestamp,
    EXTRACT(EPOCH FROM (MAX(g.timestamp) - MIN(g.timestamp)))/86400 AS coverage_days,
    
    -- Spatial coverage
    ST_Envelope(ST_Collect(g.geom)) AS coverage_bbox,
    
    -- Quality metrics
    ROUND(100.0 * COUNT(CASE WHEN g.is_valid THEN 1 END) / NULLIF(COUNT(g.id), 0), 2) AS validity_percentage,
    
    -- Trajectory statistics
    (SELECT COUNT(*) FROM mobility_trajectory t WHERE t.dataset_id = d.id) AS total_trajectories,
    (SELECT AVG(total_distance_meters) FROM mobility_trajectory t WHERE t.dataset_id = d.id) AS avg_trajectory_distance
    
FROM mobility_dataset d
LEFT JOIN mobility_gpspoint g ON d.id = g.dataset_id
GROUP BY d.id, d.name, d.dataset_type, d.entity_type;

CREATE UNIQUE INDEX idx_mv_dataset_stats ON mv_dataset_statistics(dataset_id);

-- Entity Statistics per Dataset
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_entity_statistics AS
SELECT 
    dataset_id,
    entity_id,
    COUNT(*) AS total_points,
    MIN(timestamp) AS first_seen,
    MAX(timestamp) AS last_seen,
    COUNT(DISTINCT DATE(timestamp)) AS active_days,
    AVG(speed) AS avg_speed_kmh,
    ST_Envelope(ST_Collect(geom)) AS movement_bbox
FROM mobility_gpspoint
WHERE is_valid = TRUE
GROUP BY dataset_id, entity_id;

CREATE INDEX idx_mv_entity_dataset ON mv_entity_statistics(dataset_id);
CREATE INDEX idx_mv_entity_id ON mv_entity_statistics(entity_id);

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Auto-generate geometry from coordinates
CREATE OR REPLACE FUNCTION update_point_geometry()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.geom IS NULL AND NEW.longitude IS NOT NULL AND NEW.latitude IS NOT NULL THEN
        NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_point_geometry
    BEFORE INSERT OR UPDATE ON mobility_gpspoint
    FOR EACH ROW
    EXECUTE FUNCTION update_point_geometry();

-- Update dataset statistics on point insert/delete
CREATE OR REPLACE FUNCTION update_dataset_statistics()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE mobility_dataset
        SET total_points = total_points + 1,
            temporal_range_start = LEAST(COALESCE(temporal_range_start, NEW.timestamp), NEW.timestamp),
            temporal_range_end = GREATEST(COALESCE(temporal_range_end, NEW.timestamp), NEW.timestamp)
        WHERE id = NEW.dataset_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE mobility_dataset
        SET total_points = GREATEST(0, total_points - 1)
        WHERE id = OLD.dataset_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_dataset_stats_on_point
    AFTER INSERT OR DELETE ON mobility_gpspoint
    FOR EACH ROW
    EXECUTE FUNCTION update_dataset_statistics();

-- Refresh materialized views (call periodically)
CREATE OR REPLACE FUNCTION refresh_dataset_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dataset_statistics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_entity_statistics;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PARTITIONING STRATEGY (for large datasets)
-- ============================================================================

-- Partition GPS points by dataset (enables efficient data isolation)
-- Note: Implemented at application level via Django, documented here

-- Example partition creation (manual):
-- CREATE TABLE mobility_gpspoint_dataset_xyz PARTITION OF mobility_gpspoint
-- FOR VALUES IN ('dataset-uuid-here');

-- ============================================================================
-- DATA RETENTION POLICIES
-- ============================================================================

-- Archive old import logs (keep last 90 days of completed imports)
CREATE OR REPLACE FUNCTION cleanup_old_import_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM mobility_importjob
    WHERE status = 'completed'
    AND completed_at < NOW() - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- USEFUL QUERIES
-- ============================================================================

-- Get dataset overview
COMMENT ON VIEW mv_dataset_statistics IS 
'Provides quick overview of dataset metrics including point counts, temporal/spatial coverage, and quality indicators';

-- Query examples:
-- SELECT * FROM mv_dataset_statistics WHERE dataset_name = 'my-dataset';
-- SELECT entity_id, total_points FROM mv_entity_statistics WHERE dataset_id = 'uuid' ORDER BY total_points DESC LIMIT 10;
-- SELECT * FROM mobility_gpspoint WHERE dataset_id = 'uuid' AND timestamp BETWEEN '2024-01-01' AND '2024-01-31';