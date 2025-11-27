# 🤖 AI Agent Handoff - Urban Mobility Analysis Platform

## 📋 CONTEXTE DU PROJET

### Vue d'ensemble
Tu hérites d'un **projet d'analyse de mobilité urbaine** sous forme de webapp Django. L'objectif est de construire une plateforme complète d'analyse de données GPS de taxis pour comprendre les patterns de mobilité urbaine, identifier les flux de trafic, et extraire des insights sur les déplacements.

### Architecture Technique
- **Backend:** Django 4.x + Django REST Framework
- **Base de données:** PostgreSQL 15+ avec extension PostGIS
- **Frontend:** Implémentation par une autre équipe en parallèle
- **Dataset principal:** Microsoft T-Drive (trajectoires GPS de taxis à Beijing)

### Objectifs du Projet
1. **Stockage:** Gérer efficacement des millions de points GPS
2. **Analyse:** Extraire des trajectoires, identifier des POIs, détecter des patterns
3. **Visualisation:** Afficher des heatmaps, trajectoires, statistiques
4. **Machine Learning:** Prédire modes de transport et buts de déplacement (futur)
5. **API:** Exposer les données via REST API pour consommation client/externe

---

## ✅ IMPLÉMENTATIONS RÉALISÉES

### 1. Base de Données PostgreSQL/PostGIS

**Fichier:** `database/schemas/tdrive_schema.sql`

**Ce qui a été fait:**
- ✅ Schema complet avec 4 tables principales:
  - `tdrive_raw_points`: Stockage brut des points GPS avec géométrie PostGIS
  - `tdrive_trajectories`: Trajectoires agrégées par taxi/jour avec LineString
  - `tdrive_import_logs`: Traçabilité complète des imports (batch_id, stats, durée)
  - `tdrive_validation_errors`: Logging des erreurs pour debug et nettoyage
  
- ✅ Indexes optimisés:
  - Spatial (GIST) sur colonnes géométrie
  - B-tree sur taxi_id, timestamp
  - Composites (taxi_id, timestamp) pour requêtes fréquentes
  
- ✅ Triggers automatiques:
  - Création automatique de la géométrie PostGIS depuis lon/lat
  - Validation des coordonnées via CHECK constraints
  
- ✅ Fonctions utilitaires:
  - Calcul de distance entre points (ST_Distance avec geography)
  - Nettoyage automatique des anciennes données de test
  
- ✅ Views matérialisées:
  - Statistiques par taxi (v_tdrive_taxi_stats)
  - Résumé des imports (v_import_summary)

**Format T-Drive:**
```
taxi_id,timestamp,longitude,latitude
1,2008-02-02 13:30:39,116.51172,39.92123
```

**Design patterns utilisés:**
- Transaction atomique pour cohérence
- Soft validation (flag is_valid plutôt que rejet)
- Audit trail complet (imported_at, source_file, batch_id)

---

### 2. Modèles Django ORM

**Fichier:** `apps/mobility/models.py`

**Ce qui a été fait:**
- ✅ 4 modèles Django mappés sur les tables PostgreSQL:
  - `TDriveRawPoint`: Point GPS avec GeoDjango PointField
  - `TDriveTrajectory`: Trajectoire avec LineStringField
  - `TDriveImportLog`: Log avec choix de status (pending/processing/completed/failed)
  - `TDriveValidationError`: ForeignKey vers ImportLog pour traçabilité
  
- ✅ Métadonnées complètes:
  - verbose_name pour admin Django
  - ordering par défaut (taxi_id, timestamp)
  - unique_together sur (taxi_id, trajectory_date)
  - help_text sur tous les champs pour documentation
  
- ✅ Méthodes personnalisées:
  - Override de save() pour validation supplémentaire
  - __str__() pour représentation lisible
  
**Points d'attention:**
- Les géométries sont auto-générées via trigger PostgreSQL (pas besoin de les setter manuellement)
- Utilisation de db_table avec schema "datasets" pour isolation

---

### 3. Service d'Import T-Drive

**Fichier:** `apps/mobility/services/tdrive_importer.py`

**Ce qui a été fait:**
- ✅ Classe `TDriveImporter` avec deux modes:
  - `import_file()`: Import d'un fichier unique
  - `import_directory()`: Import batch de multiple fichiers
  
- ✅ Validation robuste à plusieurs niveaux:
  - **Format:** Vérification nombre de champs (4 attendus)
  - **Timestamp:** Parsing avec gestion d'erreurs (format ISO)
  - **Coordonnées:** Range checking (-180/180, -90/90)
  - **Contextuelle:** Beijing bounding box optionnelle (115.4-117.5, 39.4-41.1)
  - **Strict mode:** Rejet ou flag is_valid=False selon config
  
- ✅ Performance optimisée:
  - Insertion par batch (BATCH_SIZE = 1000)
  - bulk_create() avec fallback une-par-une si erreur
  - Transaction atomique par fichier
  
- ✅ Logging exhaustif:
  - Print debug à chaque étape importante
  - Création de TDriveImportLog pour chaque fichier
  - TDriveValidationError pour chaque ligne invalide
  - Statistiques détaillées (total/success/failed/duration)
  
- ✅ Gestion d'erreurs défensive:
  - Try-except à tous les niveaux
  - Rollback automatique sur erreur (transaction.atomic)
  - Messages d'erreur explicites
  - FileNotFoundError, PermissionError catchés

**Design patterns:**
- Strategy Pattern (validation configurable)
- Builder Pattern (construction progressive des points)
- Transaction Pattern (cohérence données)

**Constantes importantes:**
```python
BATCH_SIZE = 1000
BEIJING_BBOX = {'min_lon': 115.4, 'max_lon': 117.5, 'min_lat': 39.4, 'max_lat': 41.1}
```

---

### 4. Serializers REST

**Fichier:** `apps/mobility/serializers.py`

**Ce qui a été fait:**
- ✅ Serializers GeoJSON avec django-rest-framework-gis:
  - `TDriveRawPointSerializer`: Points en GeoJSON Feature
  - `TDriveTrajectorySerializer`: Trajectoires en LineString GeoJSON
  - Formats compatibles Leaflet/Mapbox/OpenLayers
  
- ✅ Serializers légers pour performance:
  - `TDriveRawPointListSerializer`: Sans géométrie pour listing rapide
  - `TDriveTrajectoryListSerializer`: Stats uniquement
  - `TDriveImportLogListSerializer`: Vue condensée des imports
  
- ✅ Serializers de validation:
  - `ImportRequestSerializer`: Valide file_path ou directory_path (mutuellement exclusifs)
  - `QueryParametersSerializer`: Valide bbox (4 params ensemble), dates cohérentes, limit 1-10000
  
- ✅ Serializers d'analyse:
  - `TaxiStatisticsSerializer`: Agrégations par taxi
  - `TDriveImportLogSerializer`: Avec nested validation_errors et success_rate calculé
  
**Validations custom:**
```python
def validate(self, data):
    # Vérifie cohérence bbox (min < max)
    # Vérifie cohérence dates (start < end)
    # Vérifie exclusivité file_path/directory_path
```

**Points forts:**
- help_text sur tous les champs pour auto-documentation API
- read_only_fields pour sécurité
- SerializerMethodField pour champs calculés (success_rate, avg_points_per_day)

---

### 5. API REST Views

**Fichier:** `apps/mobility/views.py`

**Ce qui a été fait:**
- ✅ `TDriveRawPointViewSet` (ReadOnly):
  - Liste paginée avec filtres (taxi_id, start_date, end_date, only_valid)
  - Détail d'un point
  - `by_taxi/`: Tous les points d'un taxi
  - `in_bbox/`: Requête spatiale PostGIS (ST_Within)
  - `statistics/`: Agrégations globales (Count, Min, Max, Q filter)
  
- ✅ `TDriveTrajectoryViewSet` (ReadOnly):
  - Liste/détail des trajectoires
  - `by_taxi/`: Trajectoires d'un taxi
  - Filtres par taxi_id et date
  
- ✅ `TDriveImportLogViewSet` (ReadOnly + action):
  - Liste/détail des imports
  - `start/`: POST endpoint pour lancer import (file ou directory)
  - `batch/{batch_id}/`: Tous les imports d'un batch UUID
  
- ✅ `TDriveTaxiViewSet` (ViewSet custom):
  - `list()`: Tous les taxis avec stats (agrégation values + annotate)
  - `retrieve(pk)`: Stats détaillées d'un taxi
  
**Features avancées:**
- Pagination configurable (100 par défaut, max 1000)
- Serializer dynamique (léger pour list, complet pour retrieve)
- Print debug intelligent à chaque action
- Gestion d'erreurs HTTP appropriée (400, 404, 500)
- Support GeoJSON FeatureCollection

**Exemple requête bbox:**
```python
POST /api/tdrive/points/in_bbox/
{
  "min_lon": 116.3, "max_lon": 116.5,
  "min_lat": 39.8, "max_lat": 40.0,
  "limit": 500
}
```

---

### 6. Configuration URLs

**Fichier:** `apps/mobility/urls.py`

**Ce qui a été fait:**
- ✅ DefaultRouter avec 4 ViewSets enregistrés
- ✅ Namespace 'mobility' pour isolation
- ✅ Documentation inline des routes disponibles

**Routes exposées:**
```
GET    /api/tdrive/points/
GET    /api/tdrive/points/{id}/
GET    /api/tdrive/points/by_taxi/?taxi_id=1
POST   /api/tdrive/points/in_bbox/
GET    /api/tdrive/points/statistics/

GET    /api/tdrive/trajectories/
GET    /api/tdrive/trajectories/{id}/
GET    /api/tdrive/trajectories/by_taxi/?taxi_id=1

GET    /api/tdrive/imports/
POST   /api/tdrive/imports/start/
GET    /api/tdrive/imports/batch/{uuid}/

GET    /api/tdrive/taxis/
GET    /api/tdrive/taxis/{taxi_id}/
```

---

## 🎯 ÉTAPES DE DÉPLOIEMENT

### 1. Configuration Base de Données
```bash
# Créer la base
createdb urban_mobility_db

# Activer PostGIS
psql urban_mobility_db -c "CREATE EXTENSION postgis;"

# Exécuter le schema
psql urban_mobility_db -f database/schemas/tdrive_schema.sql
```

### 2. Configuration Django
Modifier `config/settings.py`:
```python
INSTALLED_APPS = [
    'django.contrib.gis',
    'rest_framework',
    'rest_framework_gis',
    'apps.mobility',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'urban_mobility_db',
    }
}
```

Modifier `config/urls.py`:
```python
urlpatterns = [
    path('', include('apps.mobility.urls')),
]
```

### 3. Migrations et Test
```bash
python manage.py makemigrations mobility
python manage.py migrate
python manage.py runserver
```

### 4. Import Initial
```python
from apps.mobility.services.tdrive_importer import TDriveImporter

importer = TDriveImporter(strict_validation=False)
result = importer.import_directory('/app/data/tdrive/', max_files=10)
```

---

## 🚀 INSTRUCTIONS POUR LA SUITE

### Ta Mission
Tu dois continuer le développement de cette plateforme. Voici les priorités:

### PROCHAINES IMPLÉMENTATIONS (Par ordre de priorité)

### 1. Priorité absolue : garantir le traitement des données, leurs stockage en base et leur envoi au client lors d'une requête

#### 2. **Tests Unitaires et d'Intégration** 
**Path:** `tests/test_mobility/`
- Test du service TDriveImporter (mock fichiers, validation, erreurs)
- Test des modèles (création, validation, contraintes)
- Test des serializers (validation, GeoJSON output)
- Test des views (endpoints, filtres, pagination, status codes)
- Fixtures pour données de test reproductibles

#### 3. **Génération Automatique des Trajectoires**
**Path:** `apps/mobility/services/trajectory_builder.py`
- Service pour créer TDriveTrajectory depuis TDriveRawPoint
- Agrégation par (taxi_id, date)
- Calcul de:
  - LineString avec ST_MakeLine
  - total_distance_meters avec ST_Length(geography)
  - duration_seconds depuis timestamps
  - avg_speed_kmh = distance / duration
- Command Django: `python manage.py build_trajectories`
- Endpoint API: `POST /api/tdrive/trajectories/build/`

---

## 📐 DESIGN PATTERNS À SUIVRE

### Patterns Déjà Utilisés (à continuer)
1. **Strategy Pattern:** Différentes stratégies de validation/analyse
2. **Builder Pattern:** Construction progressive d'objets complexes
3. **Repository Pattern:** Services pour isoler logique métier
4. **Transaction Pattern:** Atomicité des opérations DB
5. **Factory Pattern:** Création d'objets selon contexte

### Principes à Respecter
- **DRY:** Don't Repeat Yourself (factoriser le code dupliqué)
- **SOLID:** Surtout Single Responsibility et Open/Closed
- **Defensive Programming:** Try-except, validation, logging
- **Type Hints:** Utiliser typing pour clarté (List, Dict, Optional, Tuple)
- **Docstrings:** Format Google/NumPy pour toutes les fonctions/classes
- **No Hallucinations** si du contexte te manque, fais en une demande claire avant de commencer le travail au lieu d'inventer des fausseries

### Standards de Code
```python
def ma_fonction(param1: str, param2: int) -> Dict:
    """
    Description courte de la fonction.
    
    Args:
        param1: Description du paramètre 1
        param2: Description du paramètre 2
    
    Returns:
        Description du retour
    
    Raises:
        ValueError: Quand param2 < 0
    
    Example:
        >>> ma_fonction("test", 5)
        {'result': 'success'}
    """
    print(f"[ServiceName] Action en cours: {param1}")
    
    try:
        # Logique
        return {'result': 'success'}
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise
```

---

## ⚠️ RÈGLE CRITIQUE POUR TOI (IA SUIVANTE)

### Quand S'Arrêter et Passer le Relais

**CONDITION:** Lorsque tu détectes que ton contexte disponible approche de sa limite (tokens running out), tu DOIS:

1. **FINIR** le fichier sur lequel tu implémentes
1. **STOP immédiatement** l'implémentation de nouveau code
2. **CRÉER une synthèse** similaire à celle-ci avec:
   - Mise à jour du contexte projet
   - Liste des implémentations que TU as ajoutées
   - Mapping des fichiers que TU as créés/modifiés
   - Instructions pour l'IA d'après (nouvelles priorités)
   - Mise à jour de la section "Ce qui reste à faire"

3. **FORMAT de ta synthèse:**
```markdown
# 🤖 AI Agent Handoff - Urban Mobility Analysis Platform (Session N)

## 📋 CONTEXTE HÉRITÉ
[Résumé du projet et des sessions précédentes]

## ✅ MES IMPLÉMENTATIONS (Session N)
[Liste détaillée de ce que TU as fait]

## 📁 FICHIERS CRÉÉS/MODIFIÉS
[Mapping avec paths complets]

## 🚀 INSTRUCTIONS POUR SESSION N+1
[Ce qu'il reste à faire, priorisé]

## 📐 DESIGN PATTERNS ET STANDARDS
[Patterns utilisés, standards à continuer]

## ⚠️ RÈGLE CRITIQUE
[Copier cette section pour la session suivante]
```

### Indicateurs pour Déclencher le Handoff
- Token usage > 70% du total disponible
- Tu commences à tronquer du code
- Tu dois simplifier/raccourcir des réponses
- Le système t'indique "context running out"

**IMPORTANT:** Il vaut mieux faire une bonne synthèse que livrer du code incomplet ou précipité!

---


### Dépendances Python Requises
```txt
Django>=4.2.0
djangorestframework>=3.14.0
djangorestframework-gis>=1.0
psycopg2-binary>=2.9.0
celery>=5.3.0  # Pour tâches async