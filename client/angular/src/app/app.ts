// client/angular/src/app/app.ts
import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Map } from './map/map';
import { Topbar } from './topbar/topbar';
import { Sidebar } from './sidebar/sidebar';
import { ODPair } from './interfaces/od';
import { Taxi, EntityStatistics } from './interfaces/gps';
import { Gps } from './services/gps';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Map, Topbar, Sidebar],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
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

  // Dataset ID for filtering (optional)
  currentDatasetId?: string;

  constructor(private gps: Gps) {}

  ngOnInit() {
    // Initialize with T-Drive dataset for backward compatibility
    this.initializeDataset();
    this.loadEntities();
  }

  /**
   * Initialize the dataset to use
   */
  private initializeDataset(): void {
    this.gps.getTDriveDataset().subscribe({
      next: dataset => {
        console.log('Using dataset:', dataset.name, dataset.id);
        this.currentDatasetId = dataset.id;
        
        // Reload entities with dataset filter
        this.loadEntities();
      },
      error: err => {
        console.warn('Could not load default dataset:', err);
        // Continue without dataset filter
      }
    });
  }

  /**
   * Load entities (taxis/vehicles) for the current dataset
   */
  private loadEntities(): void {
    this.gps.getEntities({ dataset: this.currentDatasetId, min_points: 100}).subscribe({
      next: entities => {
        console.log('Entities loaded:', entities.length);
        this.entities = entities;
      },
      error: err => console.error('Failed to load entities:', err)
    });

    /* Alternative: Use new getEntities() method directly
    this.gps.getEntities({ 
      dataset: this.currentDatasetId,
      min_points: 10 // Optional: only show entities with at least 10 points
    }).subscribe({
      next: entities => {
        console.log('Entities loaded:', entities.length);
        // Convert to Taxi format for compatibility
        this.taxis = entities.map(e => ({
          ...e,
          taxi_id: e.entity_id
        }));
      },
      error: err => console.error('Failed to load entities:', err)
    });
    */
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
  setSelectedEntity(taxiId: string | null) {
    this.selectedEntity = taxiId;
    console.log('Selected entity:', taxiId);
  }

  /**
   * Switch to a different dataset
   */
  switchDataset(datasetId: string): void {
    this.currentDatasetId = datasetId;
    this.selectedEntity = null;
    this.loadEntities();
  }
}