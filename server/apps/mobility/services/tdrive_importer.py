"""
============================================================================
Service d'import des données T-Drive
============================================================================
Description: Gère l'extraction, validation et importation des fichiers
            T-Drive (.txt) dans la base PostgreSQL/PostGIS
            
Format T-Drive: taxi_id, timestamp, longitude, latitude
Exemple: 1,2008-02-02 13:30:39,116.51172,39.92123
============================================================================
"""

import os
import csv
import uuid
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from decimal import Decimal, InvalidOperation

import pandas as pd
import numpy as np
from tqdm import tqdm

from django.db import transaction, connection
from django.utils import timezone
from django.contrib.gis.geos import Point

from apps.mobility.models import (
    TDriveRawPoint,
    TDriveImportLog,
    TDriveValidationError
)


class TDriveImporter:
    """
    Service principal pour l'import des données T-Drive.
    
    Design patterns utilisés:
        - Strategy Pattern: Pour différentes stratégies de validation
        - Builder Pattern: Pour construire les objets point par point
        - Transaction Pattern: Pour garantir la cohérence des données
    
    Méthodes principales:
        - import_file: Importe un fichier unique
        - import_directory: Importe tous les fichiers d'un répertoire
        - validate_line: Valide une ligne de données
    """
    
    # Constantes de validation
    MIN_LONGITUDE = -180.0
    MAX_LONGITUDE = 180.0
    MIN_LATITUDE = -90.0
    MAX_LATITUDE = 90.0
    
    # Beijing bounding box (pour validation contextuelle)
    BEIJING_BBOX = {
        'min_lon': 115.4,
        'max_lon': 117.5,
        'min_lat': 39.4,
        'max_lat': 41.1
    }
    
    # Taille du batch pour insertion massive
    BATCH_SIZE = 1000
    
    def __init__(self, strict_validation: bool = False, use_beijing_bbox: bool = True, verbose: bool = False):
        """
        Initialise l'importeur.
        
        Args:
            strict_validation: Si True, applique des validations strictes
            use_beijing_bbox: Si True, vérifie que les points sont dans Beijing
            verbose: Si True, affiche tous les messages de debug
        """
        self.strict_validation = strict_validation
        self.use_beijing_bbox = use_beijing_bbox
        self.batch_id = uuid.uuid4()
        self.verbose = verbose
        
        if self.verbose:
            print(f"[TDriveImporter] Initialized with batch_id={self.batch_id}")
            print(f"[TDriveImporter] Strict validation: {strict_validation}")
            print(f"[TDriveImporter] Beijing bbox validation: {use_beijing_bbox}")
    
    def import_file(self, file_path: str, use_pandas: bool = True) -> Dict:
        """
        Importe un fichier T-Drive unique dans la base de données.
        
        Args:
            file_path: Chemin vers le fichier .txt à importer
            use_pandas: Si True, utilise pandas pour un traitement plus rapide
        
        Returns:
            Dict contenant les statistiques d'import
        """
        if self.verbose:
            print(f"\n[TDriveImporter] Starting import of file: {file_path}")
        
        # Vérification de l'existence du fichier
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            if self.verbose:
                print(f"[ERROR] {error_msg}")
            raise FileNotFoundError(error_msg)
        
        file_name = os.path.basename(file_path)
        taxi_id = os.path.splitext(file_name)[0]  # Ex: "1.txt" -> "1"
        
        # Création du log d'import
        import_log = self._create_import_log(file_name, file_path)
        start_time = timezone.now()
        
        try:
            # Import des données
            with transaction.atomic():
                if use_pandas:
                    stats = self._process_file_pandas(file_path, taxi_id, import_log)
                else:
                    stats = self._process_file(file_path, taxi_id, import_log)
            
            # Mise à jour du log
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self._update_import_log(
                import_log,
                stats,
                start_time,
                end_time,
                duration,
                TDriveImportLog.STATUS_COMPLETED
            )
            
            if self.verbose:
                print(f"[TDriveImporter] Import completed: {stats['successful']} points in {duration:.2f}s")
            
            return {
                'success': True,
                'log_id': import_log.id,
                'total_lines': stats['total'],
                'successful': stats['successful'],
                'failed': stats['failed'],
                'duration': duration,
                'method': 'pandas' if use_pandas else 'csv'
            }
        
        except Exception as e:
            # Gestion des erreurs globales
            error_msg = f"Import failed: {str(e)}"
            if self.verbose:
                print(f"[ERROR] {error_msg}")
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            import_log.status = TDriveImportLog.STATUS_FAILED
            import_log.error_message = error_msg
            import_log.end_time = end_time
            import_log.duration_seconds = duration
            import_log.save()
            
            return {
                'success': False,
                'log_id': import_log.id,
                'error': error_msg,
                'duration': duration
            }
    
    def import_directory(self, directory_path: str, max_files: Optional[int] = None) -> Dict:
        """
        Importe tous les fichiers .txt d'un répertoire.
        
        Args:
            directory_path: Chemin vers le répertoire contenant les fichiers
            max_files: Nombre maximum de fichiers à importer (None = tous)
        
        Returns:
            Dict contenant les statistiques globales
        """
        start_time = timezone.now()
        
        # Récupération des fichiers .txt
        txt_files = sorted(list(Path(directory_path).glob("*.txt")))
        
        if max_files:
            txt_files = txt_files[:max_files]
        
        print(f"📦 Processing {len(txt_files)} files...")
        
        # Statistiques globales
        stats = {
            'total_files': len(txt_files),
            'successful_files': 0,
            'failed_files': 0,
            'total_points': 0,
            'failed_points': 0
        }
        
        # Import de chaque fichier avec affichage de progression
        for idx, file_path in enumerate(txt_files, 1):
            # Affichage tous les 50 fichiers
            if idx % 50 == 0 or idx == 1 or idx == len(txt_files):
                print(f"   Progress: {idx}/{len(txt_files)} files ({idx*100//len(txt_files)}%)")
            
            try:
                result = self.import_file(str(file_path))
                
                if result['success']:
                    stats['successful_files'] += 1
                    stats['total_points'] += result['successful']
                    stats['failed_points'] += result['failed']
                else:
                    stats['failed_files'] += 1
            
            except Exception as e:
                if self.verbose:
                    print(f"[ERROR] Failed to import {file_path.name}: {str(e)}")
                stats['failed_files'] += 1
        
        # Calcul de la durée totale
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Batch import completed in {duration:.2f}s")
        
        return {
            'success': stats['failed_files'] == 0,
            'batch_id': self.batch_id,
            'duration': duration,
            **stats
        }
    
    def _create_import_log(self, file_name: str, file_path: str) -> TDriveImportLog:
        """Crée un log d'import dans la base de données."""
        import_log = TDriveImportLog.objects.create(
            import_batch_id=self.batch_id,
            file_name=file_name,
            file_path=file_path,
            start_time=timezone.now(),
            status=TDriveImportLog.STATUS_PROCESSING
        )
        return import_log
    
    def _update_import_log(
        self,
        import_log: TDriveImportLog,
        stats: Dict,
        start_time,
        end_time,
        duration: float,
        status: str
    ):
        """Met à jour le log d'import avec les statistiques finales."""
        import_log.total_lines = stats['total']
        import_log.successful_imports = stats['successful']
        import_log.failed_imports = stats['failed']
        import_log.end_time = end_time
        import_log.duration_seconds = duration
        import_log.status = status
        import_log.save()
    
    def _process_file(
        self,
        file_path: str,
        taxi_id: str,
        import_log: TDriveImportLog
    ) -> Dict:
        """Traite un fichier ligne par ligne avec validation."""
        stats = {'total': 0, 'successful': 0, 'failed': 0}
        batch = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            for line_num, row in enumerate(reader, 1):
                stats['total'] += 1
                
                # Validation et parsing de la ligne
                validation_result = self._validate_and_parse_line(
                    row, 
                    line_num, 
                    taxi_id,
                    import_log
                )
                
                if validation_result['valid']:
                    batch.append(validation_result['point'])
                    
                    # Insertion par batch pour performance
                    if len(batch) >= self.BATCH_SIZE:
                        self._bulk_insert_points(batch)
                        stats['successful'] += len(batch)
                        batch = []
                else:
                    stats['failed'] += 1
            
            # Insertion du dernier batch
            if batch:
                self._bulk_insert_points(batch)
                stats['successful'] += len(batch)
        
        return stats
    
    def _validate_and_parse_line(
        self,
        row: List[str],
        line_num: int,
        taxi_id: str,
        import_log: TDriveImportLog
    ) -> Dict:
        """
        Valide et parse une ligne du fichier T-Drive.
        
        Format attendu: taxi_id,timestamp,longitude,latitude
        """
        try:
            # Vérification du nombre de champs
            if len(row) < 4:
                error_msg = f"Invalid format: expected 4 fields, got {len(row)}"
                self._log_validation_error(
                    import_log, line_num, ','.join(row),
                    'FORMAT_ERROR', error_msg
                )
                return {'valid': False, 'point': None, 'error': error_msg}
            
            # Extraction des champs
            file_taxi_id = row[0].strip()
            timestamp_str = row[1].strip()
            longitude_str = row[2].strip()
            latitude_str = row[3].strip()
            
            # Parsing de la date
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError as e:
                error_msg = f"Invalid timestamp format: {timestamp_str}"
                self._log_validation_error(
                    import_log, line_num, ','.join(row),
                    'TIMESTAMP_ERROR', error_msg
                )
                return {'valid': False, 'point': None, 'error': error_msg}
            
            # Parsing des coordonnées
            try:
                longitude = float(longitude_str)
                latitude = float(latitude_str)
            except (ValueError, InvalidOperation) as e:
                error_msg = f"Invalid coordinates: lon={longitude_str}, lat={latitude_str}"
                self._log_validation_error(
                    import_log, line_num, ','.join(row),
                    'COORDINATE_ERROR', error_msg
                )
                return {'valid': False, 'point': None, 'error': error_msg}
            
            # Validation des coordonnées
            validation_errors = []
            
            # Validation globale
            if not (self.MIN_LONGITUDE <= longitude <= self.MAX_LONGITUDE):
                validation_errors.append(f"Longitude {longitude} out of range")
            
            if not (self.MIN_LATITUDE <= latitude <= self.MAX_LATITUDE):
                validation_errors.append(f"Latitude {latitude} out of range")
            
            # Validation contextuelle (Beijing)
            if self.use_beijing_bbox:
                if not (self.BEIJING_BBOX['min_lon'] <= longitude <= self.BEIJING_BBOX['max_lon']):
                    validation_errors.append(f"Longitude {longitude} outside Beijing bbox")
                
                if not (self.BEIJING_BBOX['min_lat'] <= latitude <= self.BEIJING_BBOX['max_lat']):
                    validation_errors.append(f"Latitude {latitude} outside Beijing bbox")
            
            # Gestion des erreurs de validation
            if validation_errors:
                error_msg = '; '.join(validation_errors)
                
                if self.strict_validation:
                    # Mode strict: rejeter le point
                    self._log_validation_error(
                        import_log, line_num, ','.join(row),
                        'VALIDATION_ERROR', error_msg
                    )
                    return {'valid': False, 'point': None, 'error': error_msg}
                else:
                    # Mode permissif: accepter mais marquer comme invalide
                    point = TDriveRawPoint(
                        taxi_id=taxi_id,
                        timestamp=timestamp,
                        longitude=longitude,
                        latitude=latitude,
                        source_file=import_log.file_name,
                        is_valid=False,
                        validation_notes=error_msg
                    )
                    return {'valid': True, 'point': point, 'error': None}
            
            # Création du point valide
            point = TDriveRawPoint(
                taxi_id=taxi_id,
                timestamp=timestamp,
                longitude=longitude,
                latitude=latitude,
                source_file=import_log.file_name,
                is_valid=True
            )
            
            return {'valid': True, 'point': point, 'error': None}
        
        except Exception as e:
            # Capture des erreurs inattendues
            error_msg = f"Unexpected error: {str(e)}"
            if self.verbose:
                print(f"[ERROR] Line {line_num}: {error_msg}")
            self._log_validation_error(
                import_log, line_num, ','.join(row) if row else '',
                'UNKNOWN_ERROR', error_msg
            )
            return {'valid': False, 'point': None, 'error': error_msg}
    
    def _process_file_pandas(
        self,
        file_path: str,
        taxi_id: str,
        import_log: TDriveImportLog
    ) -> Dict:
        """
        Process file using pandas for better performance.
        
        Args:
            file_path: Path to the file
            taxi_id: Taxi identifier
            import_log: Import log object
        
        Returns:
            Processing statistics
        """
        stats = {'total': 0, 'successful': 0, 'failed': 0}
        
        try:
            # Read file with pandas
            df = pd.read_csv(
                file_path,
                header=None,
                names=['taxi_id_file', 'timestamp', 'longitude', 'latitude'],
                dtype={
                    'taxi_id_file': str,
                    'timestamp': str,
                    'longitude': float,
                    'latitude': float
                },
                na_values=['', 'null', 'NULL', 'None'],
                keep_default_na=False
            )
            
            stats['total'] = len(df)
            
            # Parse timestamps
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            
            # Apply validation
            df['is_valid'] = True
            df['validation_notes'] = ''
            
            # Coordinate validation
            coord_mask = (
                (df['longitude'] >= self.MIN_LONGITUDE) & 
                (df['longitude'] <= self.MAX_LONGITUDE) &
                (df['latitude'] >= self.MIN_LATITUDE) & 
                (df['latitude'] <= self.MAX_LATITUDE)
            )
            
            # Beijing bbox validation
            if self.use_beijing_bbox:
                beijing_mask = (
                    (df['longitude'] >= self.BEIJING_BBOX['min_lon']) & 
                    (df['longitude'] <= self.BEIJING_BBOX['max_lon']) &
                    (df['latitude'] >= self.BEIJING_BBOX['min_lat']) & 
                    (df['latitude'] <= self.BEIJING_BBOX['max_lat'])
                )
                coord_mask = coord_mask & beijing_mask
            
            # Timestamp validation
            time_mask = df['timestamp'].notna()
            
            # Combined validation
            valid_mask = coord_mask & time_mask
            
            if self.strict_validation:
                # In strict mode, only keep valid points
                df_valid = df[valid_mask].copy()
                df_invalid = df[~valid_mask].copy()
            else:
                # In permissive mode, keep all points but mark invalid ones
                df_valid = df.copy()
                df_valid.loc[~valid_mask, 'is_valid'] = False
                df_valid.loc[~valid_mask, 'validation_notes'] = 'Failed coordinate or timestamp validation'
                df_invalid = pd.DataFrame()
            
            # Create TDriveRawPoint objects
            points = []
            for _, row in df_valid.iterrows():
                point = TDriveRawPoint(
                    taxi_id=taxi_id,
                    timestamp=row['timestamp'],
                    longitude=row['longitude'],
                    latitude=row['latitude'],
                    source_file=import_log.file_name,
                    is_valid=row['is_valid'],
                    validation_notes=row['validation_notes']
                )
                points.append(point)
            
            # Bulk insert in batches
            for i in range(0, len(points), self.BATCH_SIZE):
                batch = points[i:i + self.BATCH_SIZE]
                self._bulk_insert_points(batch)
            
            stats['successful'] = len(points)
            stats['failed'] = len(df_invalid)
            
            # Log validation errors for invalid points
            if not df_invalid.empty:
                for idx, row in df_invalid.iterrows():
                    self._log_validation_error(
                        import_log,
                        idx + 1,  # line number
                        f"{row['taxi_id_file']},{row['timestamp']},{row['longitude']},{row['latitude']}",
                        'VALIDATION_ERROR',
                        'Failed coordinate or timestamp validation'
                    )
            
            return stats
        
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] Pandas processing failed: {str(e)}")
            # Fallback to CSV processing
            return self._process_file(file_path, taxi_id, import_log)
    
    def _bulk_insert_points(self, points: List[TDriveRawPoint]):
        """Insertion massive de points en base de données."""
        try:
            TDriveRawPoint.objects.bulk_create(points, batch_size=self.BATCH_SIZE)
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] Bulk insert failed: {str(e)}")
            # Fallback: insertion une par une
            for point in points:
                try:
                    point.save()
                except Exception as point_error:
                    if self.verbose:
                        print(f"[ERROR] Failed to save point: {point_error}")
    
    def _log_validation_error(
        self,
        import_log: TDriveImportLog,
        line_number: int,
        raw_line: str,
        error_type: str,
        error_message: str
    ):
        """Enregistre une erreur de validation dans la base."""
        try:
            TDriveValidationError.objects.create(
                import_log=import_log,
                line_number=line_number,
                raw_line=raw_line[:500],  # Limitation pour éviter les textes trop longs
                error_type=error_type,
                error_message=error_message
            )
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] Failed to log validation error: {str(e)}")
