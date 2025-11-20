"""
============================================================================
Django Models pour le dataset T-Drive
============================================================================
Description: Modèles Django pour interagir avec les données T-Drive stockées
            en PostgreSQL/PostGIS. Chaque modèle correspond à une table.
============================================================================
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone
import uuid


class TDriveRawPoint(gis_models.Model):
    """
    Modèle pour les points GPS bruts issus des fichiers T-Drive.
    
    Attributs:
        taxi_id: Identifiant du taxi (nom du fichier source)
        timestamp: Date et heure du relevé GPS
        longitude/latitude: Coordonnées géographiques
        geom: Géométrie PostGIS (auto-générée via trigger)
        is_valid: Flag de validation du point
    
    Note: La géométrie est automatiquement créée par un trigger PostgreSQL
    """
    
    # Identifiants et temporalité
    taxi_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Identifiant du taxi (correspond au nom du fichier)"
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="Timestamp du relevé GPS"
    )
    
    # Coordonnées géographiques
    longitude = models.FloatField(
        help_text="Longitude (WGS84, -180 à 180)"
    )
    latitude = models.FloatField(
        help_text="Latitude (WGS84, -90 à 90)"
    )
    
    # Géométrie PostGIS
    geom = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Géométrie PostGIS du point (auto-générée)"
    )
    
    # Métadonnées d'import
    imported_at = models.DateTimeField(
        default=timezone.now,
        help_text="Date d'import dans la base"
    )
    source_file = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Nom du fichier source"
    )
    
    # Validation
    is_valid = models.BooleanField(
        default=True,
        help_text="Indique si le point a passé la validation"
    )
    validation_notes = models.TextField(
        null=True,
        blank=True,
        help_text="Notes de validation (erreurs, avertissements)"
    )
    
    class Meta:
        db_table = 'mobility_tdriverawpoint'  # FIXED: Simple table name
        verbose_name = "Point GPS T-Drive"
        verbose_name_plural = "Points GPS T-Drive"
        ordering = ['taxi_id', 'timestamp']
        indexes = [
            models.Index(fields=['taxi_id', 'timestamp'], name='idx_taxi_time'),
        ]
    
    def __str__(self):
        return f"{self.taxi_id} @ {self.timestamp}"
    
    def save(self, *args, **kwargs):
        """
        Override de save pour validation supplémentaire.
        La géométrie est gérée par le trigger PostgreSQL.
        """
        # Validation des coordonnées
        if not (-180 <= self.longitude <= 180):
            self.is_valid = False
            self.validation_notes = "Longitude invalide"
        if not (-90 <= self.latitude <= 90):
            self.is_valid = False
            self.validation_notes = "Latitude invalide"
        
        super().save(*args, **kwargs)


class TDriveTrajectory(gis_models.Model):
    """
    Modèle pour les trajectoires agrégées par taxi et par jour.
    
    Attributs:
        taxi_id: Identifiant du taxi
        trajectory_date: Date de la trajectoire
        start_time/end_time: Début et fin de la trajectoire
        point_count: Nombre de points GPS dans la trajectoire
        total_distance_meters: Distance totale parcourue
        geom: Géométrie LineString de la trajectoire complète
    
    Note: Utilisé pour les analyses et visualisations performantes
    """
    
    # Identifiants
    taxi_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Identifiant du taxi"
    )
    trajectory_date = models.DateField(
        db_index=True,
        help_text="Date de la trajectoire"
    )
    
    # Temporalité
    start_time = models.DateTimeField(
        help_text="Début de la trajectoire"
    )
    end_time = models.DateTimeField(
        help_text="Fin de la trajectoire"
    )
    
    # Statistiques
    point_count = models.IntegerField(
        help_text="Nombre de points GPS"
    )
    total_distance_meters = models.FloatField(
        null=True,
        blank=True,
        help_text="Distance totale en mètres"
    )
    duration_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Durée en secondes"
    )
    avg_speed_kmh = models.FloatField(
        null=True,
        blank=True,
        help_text="Vitesse moyenne en km/h"
    )
    
    # Géométries
    geom = gis_models.LineStringField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Géométrie LineString de la trajectoire"
    )
    bbox_geom = gis_models.PolygonField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Bounding box de la trajectoire"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date de dernière mise à jour"
    )
    
    class Meta:
        db_table = 'mobility_tdrivetrajectory'  # FIXED
        verbose_name = "Trajectoire T-Drive"
        verbose_name_plural = "Trajectoires T-Drive"
        unique_together = [['taxi_id', 'trajectory_date']]
        ordering = ['taxi_id', 'trajectory_date']
    
    def __str__(self):
        return f"{self.taxi_id} - {self.trajectory_date}"


class TDriveImportLog(models.Model):
    """
    Modèle pour les logs d'import des fichiers T-Drive.
    
    Attributs:
        import_batch_id: UUID unique pour regrouper les imports
        file_name: Nom du fichier importé
        status: État de l'import (pending, processing, completed, failed)
        successful_imports: Nombre de lignes importées avec succès
        failed_imports: Nombre de lignes échouées
    
    Note: Permet le monitoring et le debug des imports
    """
    
    # Statuts possibles
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_PROCESSING, 'En cours'),
        (STATUS_COMPLETED, 'Terminé'),
        (STATUS_FAILED, 'Échoué'),
    ]
    
    # Identifiants
    import_batch_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
        help_text="UUID du batch d'import"
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Nom du fichier importé"
    )
    file_path = models.TextField(
        null=True,
        blank=True,
        help_text="Chemin complet du fichier"
    )
    
    # Statistiques
    total_lines = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nombre total de lignes dans le fichier"
    )
    successful_imports = models.IntegerField(
        default=0,
        help_text="Nombre de lignes importées avec succès"
    )
    failed_imports = models.IntegerField(
        default=0,
        help_text="Nombre de lignes échouées"
    )
    
    # Timing
    start_time = models.DateTimeField(
        help_text="Début de l'import"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fin de l'import"
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Durée de l'import en secondes"
    )
    
    # Status et erreurs
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Statut de l'import"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Message d'erreur si échec"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Date de création du log"
    )
    
    class Meta:
        db_table = 'mobility_tdriveimportlog'  # FIXED
        verbose_name = "Log d'import T-Drive"
        verbose_name_plural = "Logs d'import T-Drive"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status}"


class TDriveValidationError(models.Model):
    """
    Modèle pour stocker les erreurs de validation lors des imports.
    
    Attributs:
        import_log: Référence au log d'import parent
        line_number: Numéro de ligne dans le fichier source
        raw_line: Contenu brut de la ligne
        error_type: Type d'erreur (parsing, validation, etc.)
        error_message: Message d'erreur détaillé
    
    Note: Permet l'analyse et le nettoyage des données problématiques
    """
    
    # Référence à l'import
    import_log = models.ForeignKey(
        TDriveImportLog,
        on_delete=models.CASCADE,
        related_name='validation_errors',
        help_text="Log d'import associé"
    )
    
    # Informations sur l'erreur
    line_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Numéro de ligne dans le fichier"
    )
    raw_line = models.TextField(
        null=True,
        blank=True,
        help_text="Contenu brut de la ligne"
    )
    error_type = models.CharField(
        max_length=100,
        help_text="Type d'erreur"
    )
    error_message = models.TextField(
        help_text="Message d'erreur détaillé"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Date de création"
    )
    
    class Meta:
        db_table = 'mobility_tdrivevalidationerror'  # FIXED
        verbose_name = "Erreur de validation T-Drive"
        verbose_name_plural = "Erreurs de validation T-Drive"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.error_type} - Line {self.line_number}"