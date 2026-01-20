-- Database initialization script for Urban Mobility Analysis
-- Creates PostGIS extensions and initial database structure

-- Enable PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create spatial reference systems if needed
-- INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) VALUES (...);

-- Create initial tables for mobility data
-- This script will be extended as Django models are created
-- Create indexes for spatial queries
-- CREATE INDEX IF NOT EXISTS idx_gps_traces_geom ON gps_traces USING GIST(geom);
-- CREATE INDEX IF NOT EXISTS idx_gps_traces_timestamp ON gps_traces(timestamp);
-- CREATE INDEX IF NOT EXISTS idx_gps_traces_user_id ON gps_traces(user_id);
