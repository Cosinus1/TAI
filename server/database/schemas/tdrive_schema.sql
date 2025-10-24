-- ============================================================================
-- Schema PostgreSQL pour le stockage des données T-Drive (Microsoft)
-- ============================================================================
-- Description: Ce schéma permet de stocker les trajectoires GPS des taxis
-- de Beijing avec support pour les analyses spatiales et temporelles
-- ============================================================================

-- Extension PostGIS pour les données géospatiales
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Schema dédié pour les datasets
CREATE SCHEMA IF NOT EXISTS datasets;

-- ============================================================================
-- TABLE: datasets.tdrive_raw_points
-- Stockage brut des points GPS issus des fichiers T-Drive
-- ============================================================================
CREATE TABLE IF NOT EXISTS datasets.tdrive_raw_points (
    -- Identifiant unique du point
    id BIGSERIAL PRIMARY KEY,
    
    -- Identifiant du taxi (correspond au nom du fichier)
    taxi_id VARCHAR(50) NOT NULL,
    
    -- Timestamp du point GPS
    timestamp TIMESTAMP NOT NULL,
    
    -- Coordonnées géographiques (WGS84)
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    
    -- Géométrie PostGIS (SRID 4326 = WGS84)
    geom GEOMETRY(Point, 4326),
    
    -- Métadonnées d'import
    imported_at TIMESTAMP DEFAULT NOW(),
    source_file VARCHAR(255),
    
    -- Validation flags
    is_valid BOOLEAN DEFAULT TRUE,
    validation_notes TEXT,
    
    -- Contraintes de cohérence
    CONSTRAINT valid_longitude CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT valid_latitude CHECK (latitude BETWEEN -90 AND 90)
);

-- ============================================================================
-- TABLE: datasets.tdrive_trajectories
-- Trajectoires agrégées par taxi et par jour
-- ============================================================================
CREATE TABLE IF NOT EXISTS datasets.tdrive_trajectories (
    -- Identifiant unique de la trajectoire
    id BIGSERIAL PRIMARY KEY,
    
    -- Identifiant du taxi
    taxi_id VARCHAR(50) NOT NULL,
    
    -- Date de la trajectoire
    trajectory_date DATE NOT NULL,
    
    -- Timestamps de début et fin
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    
    -- Statistiques de la trajectoire
    point_count INTEGER NOT NULL,
    total_distance_meters DOUBLE PRECISION,
    duration_seconds INTEGER,
    avg_speed_kmh DOUBLE PRECISION,
    
    -- Géométrie de la trajectoire complète
    geom GEOMETRY(LineString, 4326),
    
    -- Bounding box de la trajectoire
    bbox_geom GEOMETRY(Polygon, 4326),
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Contrainte d'unicité: un taxi ne peut avoir qu'une trajectoire par jour
    CONSTRAINT unique_taxi_date UNIQUE (taxi_id, trajectory_date)
);

-- ============================================================================
-- TABLE: datasets.tdrive_import_logs
-- Logs des imports pour traçabilité et gestion des erreurs
-- ============================================================================
CREATE TABLE IF NOT EXISTS datasets.tdrive_import_logs (
    -- Identifiant unique du log
    id BIGSERIAL PRIMARY KEY,
    
    -- Informations sur l'import
    import_batch_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT,
    
    -- Statistiques de l'import
    total_lines INTEGER,
    successful_imports INTEGER,
    failed_imports INTEGER,
    
    -- Timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds DOUBLE PRECISION,
    
    -- Status de l'import
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- TABLE: datasets.tdrive_validation_errors
-- Stockage des erreurs de validation pour analyse et nettoyage
-- ============================================================================
CREATE TABLE IF NOT EXISTS datasets.tdrive_validation_errors (
    -- Identifiant unique de l'erreur
    id BIGSERIAL PRIMARY KEY,
    
    -- Référence à l'import
    import_log_id BIGINT REFERENCES datasets.tdrive_import_logs(id),
    
    -- Informations sur l'erreur
    line_number INTEGER,
    raw_line TEXT,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES pour optimiser les performances
-- ============================================================================

-- Index spatial sur les points GPS
CREATE INDEX IF NOT EXISTS idx_tdrive_raw_points_geom 
ON datasets.tdrive_raw_points USING GIST(geom);

-- Index sur taxi_id pour les requêtes par véhicule
CREATE INDEX IF NOT EXISTS idx_tdrive_raw_points_taxi_id 
ON datasets.tdrive_raw_points(taxi_id);

-- Index sur timestamp pour les requêtes temporelles
CREATE INDEX IF NOT EXISTS idx_tdrive_raw_points_timestamp 
ON datasets.tdrive_raw_points(timestamp);

-- Index composite pour les requêtes taxi + temps
CREATE INDEX IF NOT EXISTS idx_tdrive_raw_points_taxi_time 
ON datasets.tdrive_raw_points(taxi_id, timestamp);

-- Index spatial sur les trajectoires
CREATE INDEX IF NOT EXISTS idx_tdrive_trajectories_geom 
ON datasets.tdrive_trajectories USING GIST(geom);

-- Index sur les dates de trajectoires
CREATE INDEX IF NOT EXISTS idx_tdrive_trajectories_date 
ON datasets.tdrive_trajectories(trajectory_date);

-- Index sur le batch_id des imports
CREATE INDEX IF NOT EXISTS idx_tdrive_import_logs_batch 
ON datasets.tdrive_import_logs(import_batch_id);

-- ============================================================================
-- FUNCTIONS utilitaires
-- ============================================================================

-- Fonction pour calculer la distance entre deux points consécutifs
CREATE OR REPLACE FUNCTION datasets.calculate_point_distance(
    p1_lon DOUBLE PRECISION,
    p1_lat DOUBLE PRECISION,
    p2_lon DOUBLE PRECISION,
    p2_lat DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
BEGIN
    RETURN ST_Distance(
        ST_SetSRID(ST_MakePoint(p1_lon, p1_lat), 4326)::geography,
        ST_SetSRID(ST_MakePoint(p2_lon, p2_lat), 4326)::geography
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Fonction pour nettoyer les anciennes données de test
CREATE OR REPLACE FUNCTION datasets.cleanup_test_data() 
RETURNS void AS $$
BEGIN
    DELETE FROM datasets.tdrive_validation_errors 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    DELETE FROM datasets.tdrive_import_logs 
    WHERE created_at < NOW() - INTERVAL '90 days' AND status = 'completed';
    
    RAISE NOTICE 'Cleanup completed';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGER pour mettre à jour automatiquement la géométrie
-- ============================================================================

CREATE OR REPLACE FUNCTION datasets.update_point_geometry()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_point_geometry
    BEFORE INSERT OR UPDATE ON datasets.tdrive_raw_points
    FOR EACH ROW
    EXECUTE FUNCTION datasets.update_point_geometry();

-- ============================================================================
-- VIEWS pour faciliter les requêtes
-- ============================================================================

-- Vue des statistiques par taxi
CREATE OR REPLACE VIEW datasets.v_tdrive_taxi_stats AS
SELECT 
    taxi_id,
    COUNT(*) as total_points,
    MIN(timestamp) as first_record,
    MAX(timestamp) as last_record,
    COUNT(DISTINCT DATE(timestamp)) as active_days,
    ST_Envelope(ST_Collect(geom)) as coverage_bbox
FROM datasets.tdrive_raw_points
WHERE is_valid = TRUE
GROUP BY taxi_id;

-- Vue des statistiques d'import
CREATE OR REPLACE VIEW datasets.v_import_summary AS
SELECT 
    import_batch_id,
    COUNT(*) as file_count,
    SUM(successful_imports) as total_success,
    SUM(failed_imports) as total_failures,
    MIN(start_time) as batch_start,
    MAX(end_time) as batch_end,
    AVG(duration_seconds) as avg_duration
FROM datasets.tdrive_import_logs
GROUP BY import_batch_id;

-- ============================================================================
-- Commentaires pour documentation
-- ============================================================================

COMMENT ON TABLE datasets.tdrive_raw_points IS 
'Stockage brut des points GPS issus des fichiers T-Drive de Microsoft';

COMMENT ON TABLE datasets.tdrive_trajectories IS 
'Trajectoires agrégées par taxi et par jour pour analyses performantes';

COMMENT ON TABLE datasets.tdrive_import_logs IS 
'Logs des imports pour traçabilité et monitoring';