// client/angular/src/app/app.ts
import { Component, OnInit, ViewChild } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Map } from './map/map';
import { Topbar } from './topbar/topbar';
import { Sidebar } from './sidebar/sidebar';
import { EntityStatistics, Dataset } from './interfaces/gps';
import { Gps } from './services/gps';
import { FilterState } from './filter-panel/filter-panel';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, Map, Topbar, Sidebar],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  @ViewChild(Map) mapComponent!: Map;

  entities: EntityStatistics[] = [];
  selectedEntity: string | null = null;

  currentDataset: Dataset | null = null;
  currentDatasetId?: string;

  currentFilters: FilterState | null = null;
  entityTypeFilter: string | null = null;
  minSpeedFilter: number | null = null;
  maxSpeedFilter: number | null = null;

  constructor(private gps: Gps) {}

  ngOnInit() {
    this.loadDatasets();
  }

  private loadDatasets(): void {
    this.gps.getDatasets({ is_active: true }).subscribe({
      next: datasets => {
        console.log('Datasets loaded:', datasets.length);
        
        const parisDataset = datasets.find(d => 
          d.name.toLowerCase().includes('paris')
        );
        
        const tdriveDataset = datasets.find(d => 
          d.name.toLowerCase().includes('t-drive') || 
          d.name.toLowerCase().includes('tdrive')
        );
        
        if (parisDataset) {
          this.onDatasetChange(parisDataset);
        } else if (tdriveDataset) {
          this.onDatasetChange(tdriveDataset);
        } else if (datasets.length > 0) {
          this.onDatasetChange(datasets[0]);
        }
      },
      error: err => console.error('Failed to load datasets:', err)
    });
  }

  private loadEntities(): void {
    if (!this.currentDatasetId) {
      this.entities = [];
      return;
    }

    this.gps.getEntities({ 
      dataset: this.currentDatasetId, 
      min_points: 10,
      entity_type: this.entityTypeFilter || undefined
    }).subscribe({
      next: entities => {
        console.log('Entities loaded:', entities.length);
        this.entities = entities;
      },
      error: err => {
        console.error('Failed to load entities:', err);
        this.entities = [];
      }
    });
  }

  setSelectedEntity(entityId: string | null) {
    this.selectedEntity = entityId;
    console.log('Selected entity for trajectory:', entityId);
  }

  onDatasetChange(dataset: Dataset | null): void {
    this.currentDataset = dataset;
    this.currentDatasetId = dataset?.id;
    this.selectedEntity = null;
    
    console.log('Dataset changed:', dataset?.name);

    this.entityTypeFilter = null;
    this.minSpeedFilter = null;
    this.maxSpeedFilter = null;
    
    if (dataset?.id) {
      this.centerMapOnDataset(dataset.id);
    }
    
    this.loadEntities();
  }

  private centerMapOnDataset(datasetId: string): void {
    this.gps.getPoints({ dataset: datasetId, page_size: 1 }).subscribe({
      next: response => {
        if (response.results && response.results.length > 0) {
          const firstPoint = response.results[0];
          if (this.mapComponent && firstPoint.latitude && firstPoint.longitude) {
            this.mapComponent.centerOn(firstPoint.latitude, firstPoint.longitude, 12);
          }
        }
      },
      error: err => console.error('Failed to get first point for centering:', err)
    });
  }

  onDatasetDeleted(datasetId: string): void {
    console.log('Dataset deleted:', datasetId);
    
    if (this.currentDatasetId === datasetId) {
      this.currentDataset = null;
      this.currentDatasetId = undefined;
      this.selectedEntity = null;
      this.entities = [];
    }
    
    this.loadDatasets();
  }

  onFilterChange(filters: FilterState): void {
    this.currentFilters = filters;
    this.entityTypeFilter = filters.selectedEntityType;
    this.minSpeedFilter = filters.minSpeed;
    this.maxSpeedFilter = filters.maxSpeed;
    
    if (filters.selectedEntityId !== undefined) {
      this.selectedEntity = filters.selectedEntityId;
    }
    
    console.log('Filters changed:', filters);
  }

  onApplyFilters(): void {
    console.log('Applying filters...');
    this.loadEntities();
  }

  onResetFilters(): void {
    console.log('Resetting filters...');
    this.entityTypeFilter = null;
    this.minSpeedFilter = null;
    this.maxSpeedFilter = null;
    this.selectedEntity = null;
    this.loadEntities();
  }
}