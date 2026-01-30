# Urban Mobility Analysis Platform

##  Présentation du Projet

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

---

##  Installation et Configuration de PostgreSQL

###  Installation sur Windows

#### Étape 1 : Téléchargement de PostgreSQL

- Visitez le site officiel : [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
- Téléchargez la version **PostgreSQL 14**

#### Étape 2 : Installation

1. Lancez le .exe
2. Suivez l'assistant d'installation :
   - **Installation Directory** : par défault
   - **Composants à installer** : Cochez TOUS les composants
     -  PostgreSQL Server
     -  pgAdmin 4 (interface graphique)
     -  Stack Builder (pour PostGIS)
     -  Command Line Tools
   
3. **Configuration du mot de passe** :
   - Définissez un mot de passe pour le superutilisateur `postgres`
   - **IMPORTANT** : Notez ce mot de passe, vous en aurez besoin !
   - Exemple : `postgres123`

4. **Port** : Laissez le port par défaut `5432`

5. Cliquez sur **"Next"** puis **"Finish"**

#### Étape 3 : Installation de PostGIS (Extension Spatiale)

1. **Lancer Stack Builder** :
   - Si l'option n'apparaît pas à la fin de l'installation, lancez Stack Builder depuis le menu Démarrer
   - Cherchez "Stack Builder" dans le menu Démarrer Windows

2. **Sélection du serveur** :
   - Choisissez votre installation PostgreSQL dans la liste déroulante
   - Cliquez sur **"Next"**

3. **Sélection des extensions** :
   - Développez la catégorie **"Spatial Extensions"**
   - Cochez **"PostGIS [version] Bundle for PostgreSQL [version]"**
   - Exemple : `PostGIS 3.4 Bundle for PostgreSQL 16`
   - Cliquez sur **"Next"**

4. **Téléchargement et installation** :
   - Stack Builder téléchargera les fichiers nécessaires
   - Suivez l'assistant d'installation de PostGIS
   - Acceptez les paramètres par défaut
   - Fermez Stack Builder une fois terminé

#### Étape 4 : Vérification de l'installation (Windows)

Ouvrez **PowerShell** ou **CMD** et testez la connexion :

```powershell
# Vérifier que PostgreSQL est installé
psql --version

# Se connecter à PostgreSQL
psql -U postgres

# Si la commande psql n'est pas reconnue, ajoutez-la au PATH :
# Panneau de configuration > Système > Paramètres système avancés > Variables d'environnement
# Ajoutez : C:\Program Files\PostgreSQL\[version]\bin
```

---

### Installation sur Linux (Ubuntu/Debian)

#### Étape 1 : Mise à jour du système

```bash
# Mettre à jour la liste des paquets
sudo apt update
sudo apt upgrade -y
```

#### Étape 2 : Installation de PostgreSQL

```bash
# Installer PostgreSQL et ses outils
sudo apt install postgresql postgresql-contrib -y

# Vérifier que le service est actif
sudo systemctl status postgresql

# Si le service n'est pas démarré
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Étape 3 : Installation de PostGIS

```bash
# Installer PostGIS pour PostgreSQL
sudo apt install postgis postgresql-14-postgis-3 -y
```

#### Étape 4 : Configuration de PostgreSQL (Linux)

1. **Accéder à PostgreSQL** :

```bash
# Basculer vers l'utilisateur postgres
sudo -i -u postgres

# Ouvrir le shell PostgreSQL
psql
```

2. **Définir un mot de passe pour l'utilisateur postgres** :

```sql
-- Dans le shell psql
ALTER USER postgres WITH PASSWORD 'votre_mot_de_passe';

-- Quitter psql
\q
```

3. **Redémarrer PostgreSQL** :

```bash
sudo systemctl restart postgresql
```

#### Étape 5 : Vérification de l'installation (Linux)

```bash
# Vérifier la version de PostgreSQL
psql --version

# Se connecter à PostgreSQL
psql -U postgres -h localhost

# Entrez le mot de passe défini précédemment
```

## Configuration de la Base de Données pour le Projet

### Méthode 1 : Utilisation de pgAdmin (Interface Graphique - Windows)

1. **Ouvrir pgAdmin 4** (installé avec PostgreSQL)
2. **Se connecter au serveur** :
   - Clic droit sur "Servers" > "Register" > "Server"
   - Onglet "General" : Nom = "Local Server"
   - Onglet "Connection" : 
     - Host : `localhost`
     - Port : `5432`
     - Username : `postgres`
     - Password : [votre mot de passe]
   - Cliquer sur "Save"

3. **Créer la base de données** :
   - Clic droit sur "Databases" > "Create" > "Database"
   - Nom : `mobility_db`
   - Owner : `postgres`
   - Cliquer sur "Save"

4. **Créer l'utilisateur** :
   - Développer votre serveur > Clic droit sur "Login/Group Roles" > "Create" > "Login/Group Role"
   - Onglet "General" : Name = `mobility_user`
   - Onglet "Definition" : Password = `password`
   - Onglet "Privileges" : Activez "Can login?"
   - Cliquer sur "Save"

5. **Activer PostGIS** :
   - Clic droit sur la base `mobility_db` > "Query Tool"
   - Exécuter : `CREATE EXTENSION postgis;`
   - Vérifier : `SELECT PostGIS_Version();`

### Méthode 2 : Utilisation du Terminal (Ligne de Commande)

#### Configuration Complète

```bash
# 1. Se connecter à PostgreSQL en tant que superutilisateur
psql -U postgres -h localhost

# Vous serez invité à entrer le mot de passe de postgres
```

```sql
-- 2. Créer la base de données
CREATE DATABASE mobility_db;

-- 3. Créer l'utilisateur de l'application
CREATE USER mobility_user WITH PASSWORD 'password';

-- 4. Accorder tous les privilèges sur la base de données
GRANT ALL PRIVILEGES ON DATABASE mobility_db TO mobility_user;

-- 5. Accorder les privilèges sur le schéma public
\c mobility_db
GRANT ALL ON SCHEMA public TO mobility_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mobility_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mobility_user;

-- 6. Activer l'extension PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 7. Vérifier l'installation de PostGIS
SELECT PostGIS_Version();

-- 8. Vérifier les extensions installées
\dx

-- 9. Quitter psql
\q
```

##  Installation du Backend (Django)

### 1. Configuration de l'environnement Conda

```bash
# Naviguer vers le dossier server
cd server

# Créer l'environnement à partir du fichier environment.yml
conda env create -f environment.yml

# Activer l'environnement
conda activate tai-env
```

### 2. Installation des dépendances Python

```bash
# Installer les dépendances principales
pip install -r requirements.txt

# Vérifier que psycopg2 est installé (driver PostgreSQL)
pip list | grep psycopg2
```

### 3. Vérification de la connexion à PostgreSQL

```bash
# Tester la connexion depuis Django
python manage.py dbshell

# Si la connexion réussit, vous verrez le prompt PostgreSQL :
# mobility_db=>

# Quitter avec \q
```

### 4. Application des migrations

```bash
# Créer les tables dans la base de données
python manage.py migrate
```

### 5. Lancement du serveur de développement

```bash
# Démarrer le serveur Django
python manage.py runserver
```

---

##  Installation du Frontend (Angular)

### 1. Installation des dépendances Node.js

```bash
# Naviguer vers le dossier Angular
cd client/angular

# Installer les dépendances avec npm
npm ci
```

### 3. Lancement du serveur Angular

```bash
# Démarrer le serveur de développement
ng serve

# L'application sera accessible à l'adresse :
# http://localhost:4200/
```

## Usage de l'application 

Utilisez les fichiers accessibles dans le dossier Tdrive
ou bien prenez des datasets de votre choix sur le web sur le web 