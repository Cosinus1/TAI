# server/apps/mobility/migrations/0003_migrate_tdrive_to_generic.py

from django.db import migrations
import uuid

def migrate_tdrive_data(apps, schema_editor):
    """Migrate T-Drive data to generic models"""
    
    # Get models
    TDriveRawPoint = apps.get_model('mobility', 'TDriveRawPoint')
    Dataset = apps.get_model('mobility', 'Dataset')
    GPSPoint = apps.get_model('mobility', 'GPSPoint')
    
    # Create T-Drive dataset if data exists
    if TDriveRawPoint.objects.exists():
        dataset_fields = {
            'description': 'Microsoft T-Drive taxi trajectory dataset from Beijing, China',
            'dataset_type': 'gps_trace',
            'data_format': 'txt',
            'geographic_scope': 'Beijing, China',
            'field_mapping': {
                'entity_id': 'taxi_id',
                'timestamp': 'timestamp',
                'longitude': 'longitude',
                'latitude': 'latitude'
            }
        }

        if hasattr(Dataset, 'entity_type'):
            dataset_fields['entity_type'] = 'taxi'

        tdrive_dataset, created = Dataset.objects.get_or_create(
            name='T-Drive Beijing Taxi Dataset',
            defaults=dataset_fields
        )
        
        # Migrate points in batches
        batch_size = 10000
        total_migrated = 0
        
        tdrive_points = TDriveRawPoint.objects.filter(is_valid=True).order_by('id')
        total_points = tdrive_points.count()
        
        for i in range(0, total_points, batch_size):
            batch = tdrive_points[i:i+batch_size]
            
            gps_points = []
            for point in batch:
                gps_points.append(GPSPoint(
                    dataset=tdrive_dataset,
                    entity_id=point.taxi_id,
                    timestamp=point.timestamp,
                    longitude=point.longitude,
                    latitude=point.latitude,
                    is_valid=point.is_valid,
                    validation_flags={'legacy_notes': point.validation_notes} if point.validation_notes else {},
                    extra_attributes={'source_file': point.source_file} if point.source_file else {},
                    imported_at=point.imported_at
                ))
            
            GPSPoint.objects.bulk_create(gps_points, batch_size=batch_size)
            total_migrated += len(gps_points)
            
            print(f"Migrated {total_migrated}/{total_points} points...")

def reverse_migration(apps, schema_editor):
    """Reverse migration - remove migrated data"""
    Dataset = apps.get_model('mobility', 'Dataset')
    try:
        tdrive_dataset = Dataset.objects.get(name='T-Drive Beijing Taxi Dataset')
        # This will cascade delete all associated GPS points
        tdrive_dataset.delete()
    except Dataset.DoesNotExist:
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('mobility', '0002_dataset_alter_tdriveimportlog_options_and_more'),
    ]
    
    operations = [
        migrations.RunPython(migrate_tdrive_data, reverse_migration),
    ]