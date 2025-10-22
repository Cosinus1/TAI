-- Database initialization script for Urban Mobility Analysis
-- Creates PostGIS extensions and initial database structure

-- Enable PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create spatial reference systems if needed
-- INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) VALUES (...);

-- Create initial tables for mobility data
-- This script will be extended as Django models are created

-- Example: Create a table for GPS traces (will be replaced by Django migrations)
-- CREATE TABLE IF NOT EXISTS gps_traces (
--     id SERIAL PRIMARY KEY,
--     user_id INTEGER,
--     timestamp TIMESTAMP WITH TIME ZONE,
--     latitude DECIMAL(10, 8),
--     longitude DECIMAL(11, 8),
--     altitude DECIMAL(8, 2),
--     speed DECIMAL(6, 2),
--     accuracy DECIMAL(6, 2),
--     geom GEOMETRY(Point, 4326)
-- );

-- Create indexes for spatial queries
-- CREATE INDEX IF NOT EXISTS idx_gps_traces_geom ON gps_traces USING GIST(geom);
-- CREATE INDEX IF NOT EXISTS idx_gps_traces_timestamp ON gps_traces(timestamp);
-- CREATE INDEX IF NOT EXISTS idx_gps_traces_user_id ON gps_traces(user_id);
