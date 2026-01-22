// client/angular/src/app/app.ts
import { Component, OnInit, ViewChild } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Map } from './map/map';
import { Topbar } from './topbar/topbar';
import { Sidebar } from './sidebar/sidebar';
import { ODPair } from './interfaces/od';
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

  odPairs: ODPair[] = [
    {
      origin: { name: 'Tour Eiffel', lat: 48.8584, lng: 2.2945 },
      destination: { name: 'Louvre', lat: 48.8606, lng: 2.3376 },
    },
    {
      origin: { name: 'Gare du Nord', lat: 48.8809, lng: 2.3553 },
      destination: { name: 'Montparnasse', lat: 48.8400, lng: 2.3200 },
    },
    {
      origin: { name: 'La Défense', lat: 48.8924, lng: 2.2369 },
      destination: { name: 'Champs-Élysées', lat: 48.8698, lng: 2.3073 },
    },
  ];

  // Index sélectionné (null = afficher toutes les paires)
  selectedIndex: number | null = null;
  
  // Entities (taxis, vehicles, etc.)
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
    this.gps.getEntities({ 
      dataset: this.currentDatasetId, 
      min_points: 10,
      entity_type: this.entityTypeFilter || undefined
    }).subscribe({
      next: entities => {
        console.log('Entities loaded:', entities.length);
        this.entities = entities;
      },
      error: err => console.error('Failed to load entities:', err)
    });
  }

  /**
   * Handler called by Sidebar when user selects an OD pair
   */
  setSelectedIndex(index: number | null) {
    this.selectedIndex = index;
  }

  /**
   * Handler called by Sidebar when user selects an entity (taxi)
   */
  setSelectedEntity(entityId: string | null) {
    this.selectedEntity = entityId;
    console.log('Selected entity:', entityId);
  }

  /**
   * Handler for dataset change
   */
  onDatasetChange(dataset: Dataset | null): void {
    this.currentDataset = dataset;
    this.currentDatasetId = dataset?.id;
    this.selectedEntity = null;
    
    console.log('Dataset changed:', dataset?.name);

    // Center map based on dataset geographic scope
    if (dataset && this.mapComponent) {
      if (dataset.geographic_scope?.toLowerCase().includes('paris')) {
        this.mapComponent.centerOnParis();
      } else if (dataset.geographic_scope?.toLowerCase().includes('beijing')) {
        this.mapComponent.centerOnBeijing();
      }
    }

    // Reset filters when dataset changes
    this.entityTypeFilter = null;
    this.minSpeedFilter = null;
    this.maxSpeedFilter = null;
    
    // Load entities for new dataset
    this.loadEntities();
  }

  /**
   * Handler for filter changes from sidebar
   */
  onFilterChange(filters: FilterState): void {
    this.currentFilters = filters;
    this.entityTypeFilter = filters.selectedEntityType;
    this.minSpeedFilter = filters.minSpeed;
    this.maxSpeedFilter = filters.maxSpeed;
    
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
    this.loadEntities();
  }
}