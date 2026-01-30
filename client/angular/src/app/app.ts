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

  // Entities (vehicles, taxis, bikes, etc.)
  entities: EntityStatistics[] = [];
  selectedEntity: string | null = null;

  // Current dataset
  currentDataset: Dataset | null = null;
  currentDatasetId?: string;

  // Filter state
  currentFilters: FilterState | null = null;
  entityTypeFilter: string | null = null;
  minSpeedFilter: number | null = null;
  maxSpeedFilter: number | null = null;

  constructor(private gps: Gps) {}

  ngOnInit() {
    // Load datasets on init
    this.loadDatasets();
  }

  /**
   * Load available datasets
   */
  private loadDatasets(): void {
    this.gps.getDatasets({ is_active: true }).subscribe({
      next: datasets => {
        console.log('Datasets loaded:', datasets.length);
        
        // Try to auto-select Paris test dataset first, then T-Drive
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

  /**
   * Load entities for the current dataset
   */
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

  /**
   * Handler called when user selects an entity
   * This triggers trajectory rendering in the map
   */
  setSelectedEntity(entityId: string | null) {
    this.selectedEntity = entityId;
    console.log('Selected entity for trajectory:', entityId);
  }

  /**
   * Handler for dataset change
   */
  onDatasetChange(dataset: Dataset | null): void {
    this.currentDataset = dataset;
    this.currentDatasetId = dataset?.id;
    this.selectedEntity = null;
    
    console.log('Dataset changed:', dataset?.name);

    // Reset filters when dataset changes
    this.entityTypeFilter = null;
    this.minSpeedFilter = null;
    this.maxSpeedFilter = null;
    
    // Load entities for new dataset
    this.loadEntities();
  }

  /**
   * Handler for dataset deletion
   */
  onDatasetDeleted(datasetId: string): void {
    console.log('Dataset deleted:', datasetId);
    
    // Clear current selection if deleted dataset was selected
    if (this.currentDatasetId === datasetId) {
      this.currentDataset = null;
      this.currentDatasetId = undefined;
      this.selectedEntity = null;
      this.entities = [];
    }
    
    // Reload datasets
    this.loadDatasets();
  }

  /**
   * Handler for filter changes from sidebar
   */
  onFilterChange(filters: FilterState): void {
    this.currentFilters = filters;
    this.entityTypeFilter = filters.selectedEntityType;
    this.minSpeedFilter = filters.minSpeed;
    this.maxSpeedFilter = filters.maxSpeed;
    
    // Update selected entity from filter panel
    if (filters.selectedEntityId !== undefined) {
      this.selectedEntity = filters.selectedEntityId;
    }
    
    console.log('Filters changed:', filters);
  }

  /**
   * Apply filters and reload data
   */
  onApplyFilters(): void {
    console.log('Applying filters...');
    this.loadEntities();
  }

  /**
   * Reset all filters
   */
  onResetFilters(): void {
    console.log('Resetting filters...');
    this.entityTypeFilter = null;
    this.minSpeedFilter = null;
    this.maxSpeedFilter = null;
    this.selectedEntity = null;
    this.loadEntities();
  }
}