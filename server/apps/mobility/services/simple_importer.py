"""
============================================================================
Simple Data Importer with Trajectory Calculation
============================================================================
"""

import csv
import logging
from datetime import datetime
from typing import Dict, Optional
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.db import transaction

logger = logging.getLogger(__name__)


class SimpleDataImporter:
    """
    Simplified importer for GPS data files.
    Automatically calculates trajectories after import.
    """
    
    def __init__(self, dataset, import_job):
        self.dataset = dataset
        self.import_job = import_job
        self.batch_size = 1000
    
    def import_file(
        self,
        file_path: str,
        field_mapping: Dict[str, str],
        delimiter: str = ',',
        skip_header: bool = True
    ) -> Dict:
        """
        Import GPS data from file and calculate trajectories.
        """
        from apps.mobility.models import GPSPoint
        
        stats = {
            'success': False,
            'total_lines': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'trajectories_calculated': 0
        }
        
        self.import_job.status = 'processing'
        self.import_job.started_at = timezone.now()
        self.import_job.save()
        
        points_batch = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=delimiter)
                
                if skip_header:
                    try:
                        next(reader)
                    except StopIteration:
                        pass
                
                for line_num, row in enumerate(reader, start=1):
                    stats['total_lines'] += 1
                    
                    point_data = self._parse_row(row, field_mapping, line_num)
                    
                    if point_data:
                        points_batch.append(point_data)
                        
                        if len(points_batch) >= self.batch_size:
                            saved = self._save_batch(points_batch)
                            stats['successful'] += saved
                            stats['failed'] += len(points_batch) - saved
                            points_batch = []
                
                if points_batch:
                    saved = self._save_batch(points_batch)
                    stats['successful'] += saved
                    stats['failed'] += len(points_batch) - saved
            
            logger.info(f"Calculating trajectories for dataset {self.dataset.id}")
            traj_stats = self._calculate_trajectories()
            stats['trajectories_calculated'] = traj_stats.get('total_trajectories', 0)
            logger.info(f"Created {stats['trajectories_calculated']} trajectories")
            
            stats['success'] = True
            self.import_job.status = 'completed'
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}", exc_info=True)
            stats['errors'].append(str(e))
            self.import_job.status = 'failed'
            self.import_job.error_message = str(e)
        
        finally:
            self.import_job.completed_at = timezone.now()
            if self.import_job.started_at:
                duration = (self.import_job.completed_at - self.import_job.started_at).total_seconds()
                self.import_job.duration_seconds = duration
            self.import_job.save()
        
        return stats
    
    def _calculate_trajectories(self) -> Dict:
        """Calculate trajectories after import."""
        try:
            from apps.mobility.services.trajectory_calculator import TrajectoryCalculator
            calculator = TrajectoryCalculator(self.dataset)
            return calculator.calculate_all_trajectories()
        except Exception as e:
            logger.error(f"Trajectory calculation failed: {e}")
            return {'total_trajectories': 0}
    
    def _parse_row(self, row: list, field_mapping: Dict[str, str], line_num: int) -> Optional[Dict]:
        """Parse a CSV row into point data."""
        try:
            if len(row) < 4:
                return None
            
            entity_id = row[0].strip()
            timestamp_str = row[1].strip()
            longitude_str = row[2].strip()
            latitude_str = row[3].strip()
            
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%d/%m/%Y %H:%M:%S']:
                    try:
                        timestamp = datetime.strptime(timestamp_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None
            
            longitude = float(longitude_str)
            latitude = float(latitude_str)
            
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                return None
            
            return {
                'entity_id': entity_id,
                'timestamp': timestamp,
                'longitude': longitude,
                'latitude': latitude
            }
            
        except (ValueError, IndexError) as e:
            logger.debug(f"Line {line_num} parse error: {e}")
            return None
    
    def _save_batch(self, points_data: list) -> int:
        """Save a batch of points to database."""
        from apps.mobility.models import GPSPoint
        
        saved_count = 0
        
        for point_data in points_data:
            try:
                point = GPSPoint(
                    dataset=self.dataset,
                    entity_id=point_data['entity_id'],
                    timestamp=point_data['timestamp'],
                    longitude=point_data['longitude'],
                    latitude=point_data['latitude'],
                    geom=Point(point_data['longitude'], point_data['latitude'], srid=4326),
                    is_valid=True
                )
                point.save()
                saved_count += 1
                
            except Exception as e:
                logger.debug(f"Failed to save point: {e}")
                continue
        
        return saved_count