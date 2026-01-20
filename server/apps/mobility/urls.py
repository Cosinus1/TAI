"""
============================================================================
Django URLs Configuration
============================================================================
Description: API routes for generic mobility data management
Path: apps/mobility/urls.py
============================================================================
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.mobility.views import (
    DatasetViewSet,
    GPSPointViewSet,
    TrajectoryViewSet,
    ImportJobViewSet,
    EntityViewSet
)

# Configure REST router
router = DefaultRouter()

# Register viewsets
router.register(r'datasets', DatasetViewSet, basename='dataset')
router.register(r'points', GPSPointViewSet, basename='gpspoint')
router.register(r'trajectories', TrajectoryViewSet, basename='trajectory')
router.register(r'imports', ImportJobViewSet, basename='importjob')
router.register(r'entities', EntityViewSet, basename='entity')

# App name for URL namespacing
app_name = 'mobility'

urlpatterns = [
    # Main API routes
    path('', include(router.urls)),
]

"""
============================================================================
Available API Endpoints
============================================================================

DATASETS:
    GET    /api/datasets/                        - List all datasets
    POST   /api/datasets/                        - Create new dataset
    GET    /api/datasets/{id}/                   - Dataset details
    PUT    /api/datasets/{id}/                   - Update dataset
    DELETE /api/datasets/{id}/                   - Delete dataset
    GET    /api/datasets/{id}/statistics/        - Dataset statistics
    POST   /api/datasets/{id}/deactivate/        - Deactivate dataset
    POST   /api/datasets/{id}/activate/          - Activate dataset

GPS POINTS:
    GET    /api/points/                          - List points (paginated)
    POST   /api/points/                          - Create single point
    GET    /api/points/{id}/                     - Point details
    POST   /api/points/query/                    - Advanced spatial/temporal query
    GET    /api/points/by_entity/                - Get points for entity
    POST   /api/points/bulk_create/              - Bulk create points

TRAJECTORIES:
    GET    /api/trajectories/                    - List trajectories
    GET    /api/trajectories/{id}/               - Trajectory details
    POST   /api/trajectories/query/              - Advanced trajectory query
    GET    /api/trajectories/{id}/analyze/       - Analyze trajectory

IMPORTS:
    GET    /api/imports/                         - List import jobs
    GET    /api/imports/{id}/                    - Import job details
    POST   /api/imports/start_import/            - Start new import
    GET    /api/imports/{id}/progress/           - Check import progress

ENTITIES:
    GET    /api/entities/                        - List entities with stats
    GET    /api/entities/{entity_id}/            - Entity statistics

============================================================================
Query Parameters
============================================================================

Points listing (/api/points/):
    ?dataset={uuid}           - Filter by dataset
    ?entity_id={string}       - Filter by entity
    ?start_time={iso8601}     - Start of time range
    ?end_time={iso8601}       - End of time range
    ?only_valid={bool}        - Only validated points
    ?page={int}               - Page number
    ?page_size={int}          - Results per page

Trajectories listing (/api/trajectories/):
    ?dataset={uuid}           - Filter by dataset
    ?entity_id={string}       - Filter by entity
    ?date={YYYY-MM-DD}        - Specific date
    ?page={int}               - Page number
    ?page_size={int}          - Results per page

Import jobs (/api/imports/):
    ?dataset={uuid}           - Filter by dataset
    ?status={string}          - Filter by status

Entities (/api/entities/):
    ?dataset={uuid}           - Filter by dataset
    ?min_points={int}         - Minimum point count

============================================================================
Example Usage
============================================================================

1. Create a new dataset:
   POST /api/datasets/
   {
     "name": "My GPS Data",
     "dataset_type": "gps_trace",
     "data_format": "csv",
     "field_mapping": {
       "entity_id": "vehicle_id",
       "timestamp": "datetime",
       "longitude": "lon",
       "latitude": "lat"
     }
   }

2. Start an import:
   POST /api/imports/start_import/
   {
     "dataset_id": "uuid-here",
     "source_type": "file",
     "source_path": "/path/to/data.csv",
     "file_format": "csv",
     "field_mapping": {
       "entity_id": "vehicle_id",
       "timestamp": "datetime",
       "longitude": "lon",
       "latitude": "lat"
     }
   }

3. Query points in bounding box:
   POST /api/points/query/
   {
     "dataset": "uuid-here",
     "min_lon": 116.3,
     "max_lon": 116.5,
     "min_lat": 39.9,
     "max_lat": 40.0,
     "start_time": "2024-01-01T00:00:00Z",
     "end_time": "2024-01-02T00:00:00Z",
     "limit": 1000
   }

4. Get entity statistics:
   GET /api/entities/{entity_id}/?dataset={uuid}

============================================================================
"""