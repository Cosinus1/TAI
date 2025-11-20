"""
============================================================================
Django URLs pour l'API T-Drive
============================================================================
Description: Configuration des routes de l'API REST pour le dataset T-Drive
Path: apps/mobility/urls.py
============================================================================
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.mobility.views import (
    TDriveRawPointViewSet,
    TDriveTrajectoryViewSet,
    TDriveImportLogViewSet,
    TDriveTaxiViewSet
)

# Configuration du router REST
router = DefaultRouter()

# Enregistrement des ViewSets
router.register(r'points', TDriveRawPointViewSet, basename='tdrive-points')
router.register(r'trajectories', TDriveTrajectoryViewSet, basename='tdrive-trajectories')
router.register(r'imports', TDriveImportLogViewSet, basename='tdrive-imports')
router.register(r'taxis', TDriveTaxiViewSet, basename='tdrive-taxis')

# URLs de l'application
app_name = 'mobility'

urlpatterns = [
    # API REST
    path('tdrive/', include(router.urls)),
]

"""
============================================================================
Routes disponibles:
============================================================================

Points GPS:
    GET    /api/tdrive/points/                    - Liste des points
    GET    /api/tdrive/points/{id}/               - Détail d'un point
    GET    /api/tdrive/points/by_taxi/            - Points par taxi
    POST   /api/tdrive/points/in_bbox/            - Points dans bbox
    GET    /api/tdrive/points/statistics/         - Statistiques globales

Trajectoires:
    GET    /api/tdrive/trajectories/              - Liste des trajectoires
    GET    /api/tdrive/trajectories/{id}/         - Détail d'une trajectoire
    GET    /api/tdrive/trajectories/by_taxi/      - Trajectoires par taxi

Imports:
    GET    /api/tdrive/imports/                   - Liste des imports
    GET    /api/tdrive/imports/{id}/              - Détail d'un import
    POST   /api/tdrive/imports/start/             - Lancer un import
    GET    /api/tdrive/imports/batch/{batch_id}/  - Imports d'un batch

Taxis:
    GET    /api/tdrive/taxis/                     - Liste des taxis
    GET    /api/tdrive/taxis/{taxi_id}/           - Statistiques d'un taxi

============================================================================
"""