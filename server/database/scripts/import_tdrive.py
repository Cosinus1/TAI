#!/usr/bin/env python3
"""
============================================================================
Script d'import des données T-Drive brutes
============================================================================
Description: Charge les fichiers .txt du dossier data dans PostgreSQL
Usage: python import_tdrive_data.py
============================================================================
"""
import os
import django
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION DJANGO 
# ============================================================================

# Chemins exacts basés sur votre structure
current_file = Path(__file__).resolve()
scripts_dir = current_file.parent          # /TAI/server/database/scripts/
database_dir = scripts_dir.parent          # /TAI/server/database/
server_dir = database_dir.parent           # /TAI/server/
project_root = server_dir.parent           # /TAI/

print(f"📁 Dossier du script: {scripts_dir}")
print(f"📁 Dossier server: {server_dir}")

# Ajoute les chemins nécessaires
sys.path.insert(0, str(server_dir))
sys.path.insert(0, str(project_root))

# Configuration Django avec le bon module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
    print("✅ Configuration Django chargée: config.settings")
except Exception as e:
    print(f"❌ Erreur configuration Django: {e}")
    sys.exit(1)

# ============================================================================
# IMPORT DES MODULES DJANGO
# ============================================================================

try:
    from apps.mobility.services.tdrive_importer import TDriveImporter
    from apps.mobility.models import TDriveRawPoint, TDriveImportLog
    print("✅ Modules Django importés avec succès")
except ImportError as e:
    print(f"❌ Erreur import modules: {e}")
    sys.exit(1)

from django.db import transaction
from django.utils import timezone
from apps.mobility.services.tdrive_importer import TDriveImporter

def import_tdrive_data():
    """
    Importe toutes les données T-Drive depuis le dossier data/tdrive/
    """
    print("🚀 Démarrage de l'import des données T-Drive...")
    
    # Chemin vers vos données
    data_directory = "data/tdrive"
    
    # Vérification que le dossier existe
    if not os.path.exists(data_directory):
        print(f"❌ Erreur: Le dossier {data_directory} n'existe pas")
        return False
    
    # Comptage des fichiers
    txt_files = list(Path(data_directory).glob("*.txt"))
    print(f"📁 Fichiers trouvés: {len(txt_files)}")
    
    if len(txt_files) == 0:
        print("❌ Aucun fichier .txt trouvé dans le dossier")
        return False
    
    # Configuration de l'import
    importer = TDriveImporter(
        strict_validation=False,      # Mode permissif pour premier import
        use_beijing_bbox=True         # Validation géographique Beijing
    )
    
    print("\n⚙️ Configuration de l'import:")
    print(f"  - Validation stricte: {importer.strict_validation}")
    print(f"  - Validation Beijing bbox: {importer.use_beijing_bbox}")
    print(f"  - Taille des batches: {importer.BATCH_SIZE}")
    
    try:
        # Lancement de l'import
        print(f"\n📤 Import en cours...")
        print(f"💡 Progress: affichage tous les 50 fichiers")
        result = importer.import_directory(
            directory_path=data_directory,
            max_files=None  # Tous les fichiers
        )
        
        # Affichage des résultats
        print(f"\n✅ Import terminé avec succès!")
        print(f"📊 Statistiques globales:")
        print(f"   - Fichiers traités: {result['total_files']}")
        print(f"   - Fichiers réussis: {result['successful_files']}")
        print(f"   - Fichiers échoués: {result['failed_files']}")
        print(f"   - Points importés: {result['total_points']}")
        print(f"   - Points échoués: {result.get('failed_points', 0)}")
        print(f"   - Durée totale: {result['duration']:.2f} secondes")
        print(f"   - Batch ID: {result['batch_id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'import: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_import():
    """
    Vérifie que les données ont bien été importées
    """
    print(f"\n🔍 Vérification de l'import...")
    
    from apps.mobility.models import TDriveRawPoint, TDriveImportLog
    
    # Statistiques des points
    total_points = TDriveRawPoint.objects.count()
    taxis_count = TDriveRawPoint.objects.values('taxi_id').distinct().count()
    
    print(f"📈 Données importées:")
    print(f"   - Points totaux: {total_points}")
    print(f"   - Taxis distincts: {taxis_count}")
    
    # Derniers imports
    last_imports = TDriveImportLog.objects.order_by('-start_time')[:5]
    print(f"   - Derniers imports: {last_imports.count()}")
    
    for imp in last_imports:
        print(f"     • {imp.file_name}: {imp.successful_imports} points")
    
    return total_points > 0

if __name__ == "__main__":
    print("=" * 60)
    print("IMPORT DONNÉES T-DRIVE")
    print("=" * 60)
    
    # Import des données
    success = import_tdrive_data()
    
    if success:
        # Vérification
        verify_import()
        print(f"\n🎉 Import terminé avec succès!")
    else:
        print(f"\n💥 Échec de l'import")
    
    print("=" * 60)