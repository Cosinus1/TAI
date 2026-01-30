# Urban Mobility Analysis Platform

##  Présentation du Projet

**Urban Mobility Analysis Platform** est une application web complète permettant de visualiser et d'analyser des données de mobilité urbaine sur une carte interactive. Le système permet de traiter différents types de données de mobilité pour l'analyse des déplacements urbains.

###  Objectifs
- Visualisation interactive des données GPS sur carte
- Analyse des trajectoires et des déplacements
- Filtrage avancé par type d'entité et vitesse moyenne
- Calcul automatique des statistiques de mobilité
- Gestion de multiples jeux de données

###  Architecture Technique
- **Frontend** : Angular 18 (TypeScript) avec Leaflet pour les cartes
- **Backend** : Django 5.2 avec Django REST Framework
- **Base de données** : PostgreSQL avec extensions spatiales (PostGIS)
- **Types de données supportés** :
  - Traces GPS (points de localisation)
  - Trajectoires (séquences de points)

##  Installation et Lancement

### Prérequis Système
- **Python 3.10+** avec Conda/Anaconda
- **Node.js 18+** et npm
- **PostgreSQL 14+** avec PostGIS

###  Installation du Backend (Django)

#### 1. Configuration de l'environnement Conda
```bash
# Créer l'environnement à partir du fichier environment.yml
cd server
conda env create -f environment.yml

# Activer l'environnement
conda activate tai-env
```

#### 2. Installation des dépendances Python
```bash
# Installer les dépendances principales
pip install -r requirements.txt

```

#### 3. Configuration de la base de données
```sql
-- Créer la base de données PostgreSQL
CREATE DATABASE mobility_db;
CREATE USER mobility_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE mobility_db TO mobility_user;

-- Activer l'extension PostGIS
\c mobility_db
CREATE EXTENSION postgis;
```

#### 4. Configuration Django
```bash
# Appliquer les migrations
python manage.py migrate
```

#### 5. Lancement du serveur de développement
```bash
# Démarrer le serveur Django
python manage.py runserver
```

###  Installation du Frontend (Angular)

#### 1. Installation des dépendances Node.js
```bash
cd client/angular

# Installer les dépendances avec npm
npm ci
```

#### 2. Lancement du serveur de développement Angular
```bash
# Démarrer le serveur de développement
ng serve

# L'application sera accessible à l'adresse :
# http://localhost:4200/
```

## Fonctionnalités Principales

### 1. Gestion des Jeux de Données
- Import de fichiers CSV, JSON, GeoJSON
- Validation automatique des données
- Gestion de multiples sources de données
- Métadonnées et statistiques par jeu de données

### 2. Visualisation sur Carte
- Points GPS avec informations détaillées
- Trajectoires avec calcul automatique
- Filtrage spatial et temporel
- Couches thématiques (vitesse, type d'entité)

### 3. Analyse des Entités

### 4. API REST Complète
- Points GPS : `GET /api/points/`
- Trajectories : `GET /api/trajectories/`
- Statistiques d'entités : `GET /api/entities/`
- Jeux de données : `GET /api/datasets/`
- Import de données : `POST /api/import/start_import/`

##  Structure du Projet

```
TAI/
├── server/                    # Backend Django
│   ├── apps/
│   │   └── mobility/         # Application principale
│   │       ├── models.py     # Modèles de données
│   │       ├── views.py      # Vues API
│   │       ├── serializers.py # Sérialiseurs
│   │       └── services/     # Services métier
│   ├── config/               # Configuration Django
│   ├── database/             # Scripts et schémas DB
│   └── utils/                # Utilitaires
├── client/                   # Frontend Angular
│   └── angular/
│       ├── src/app/
│       │   ├── map/          # Composant carte
│       │   ├── sidebar/      # Panneau latéral
│       │   ├── services/     # Services API
│       │   └── interfaces/   # Types TypeScript
│       └── src/environments/ # Configurations
└── README.md                 # Ce fichier
```