// client/angular/src/app/sidebar/sidebar.ts
import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EntityStatistics, Dataset } from '../interfaces/gps';
import { DatasetSelector } from '../dataset-selector/dataset-selector';
import { FilterPanel, FilterState } from '../filter-panel/filter-panel';
import { StatisticsPanel } from '../statistics-panel/statistics-panel';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, DatasetSelector, FilterPanel, StatisticsPanel],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
})
export class Sidebar {
  // Inputs
  @Input() entities: EntityStatistics[] = [];
  
  // Outputs - using consistent "entity" terminology
  @Output() entityChange = new EventEmitter<string | null>();
  @Output() datasetChange = new EventEmitter<Dataset | null>();
  @Output() datasetDeleted = new EventEmitter<string>();
  @Output() filterChange = new EventEmitter<FilterState>();
  @Output() apply = new EventEmitter<void>();
  @Output() reset = new EventEmitter<void>();

  // State signals
  currentDataset = signal<Dataset | null>(null);
  currentFilters = signal<FilterState | null>(null);
  selectedEntity = signal<string | null>(null);
  showStats = signal<boolean>(true);

  /**
   * Handle dataset selection
   */
  onDatasetSelected(dataset: Dataset | null) {
    this.currentDataset.set(dataset);
    this.datasetChange.emit(dataset);
    
    // Clear entity selection when dataset changes
    this.clearSelection();
  }

  /**
   * Handle dataset deletion
   */
  onDatasetDeleted(datasetId: string) {
    this.datasetDeleted.emit(datasetId);
    this.clearSelection();
  }

  /**
   * Handle filter changes from filter panel
   */
  onFilterChange(filters: FilterState) {
    this.currentFilters.set(filters);
    this.filterChange.emit(filters);
    
    // Update single entity selection if filter panel changed it
    if (filters.selectedEntityId !== undefined) {
      this.selectedEntity.set(filters.selectedEntityId);
      this.entityChange.emit(filters.selectedEntityId);
    }
  }

  /**
   * Handle entity selection from filter panel
   * This triggers trajectory rendering on the map
   */
  onEntitySelected(entityId: string | null) {
    console.log('Entity selected for trajectory visualization:', entityId);
    this.selectedEntity.set(entityId);
    this.entityChange.emit(entityId);
  }

  /**
   * Clear current entity selection
   */
  clearSelection() {
    this.selectedEntity.set(null);
    this.entityChange.emit(null);
    console.log('Entity selection cleared');
  }

  /**
   * Apply current filters
   */
  onApplyFilters() {
    this.apply.emit();
  }

  /**
   * Reset all filters
   */
  onResetFilters() {
    this.reset.emit();
    this.clearSelection();
  }

  /**
   * Toggle statistics panel visibility
   */
  toggleStats() {
    this.showStats.update(v => !v);
  }

  /**
   * Get filtered entities based on current filters
   * Handles undefined/null speed values properly
   */
  getFilteredEntities(): EntityStatistics[] {
    const filters = this.currentFilters();
    if (!filters) {
      return this.entities;
    }

    let filtered = this.entities;

    // Filter by entity type
    if (filters.selectedEntityType) {
      filtered = filtered.filter(e => 
        e.entity_id.startsWith(filters.selectedEntityType!)
      );
    }

    // Filter by speed range
    // IMPORTANT: Speed can be undefined, so we need proper null checks
    
    // Minimum speed filter
    if (this.isValidSpeed(filters.minSpeed)) {
      filtered = filtered.filter(e => {
        // Exclude entities without speed data
        const speed = e.avg_speed || e.avg_speed;
        if (!this.isValidSpeed(speed)) {
          return false;
        }
        return speed! >= filters.minSpeed!;
      });
    }
    
    // Maximum speed filter
    if (this.isValidSpeed(filters.maxSpeed)) {
      filtered = filtered.filter(e => {
        // Exclude entities without speed data
        const speed = e.avg_speed || e.avg_speed;
        if (!this.isValidSpeed(speed)) {
          return false;
        }
        return speed! <= filters.maxSpeed!;
      });
    }

    return filtered;
  }

  /**
   * Check if a speed value is valid (not null, undefined, NaN, or negative)
   */
  private isValidSpeed(speed: number | null | undefined): speed is number {
    return speed !== null && 
           speed !== undefined && 
           !isNaN(speed) && 
           speed >= 0;
  }

  /**
   * Get count of entities with speed data
   * Useful for displaying filter feedback
   */
  getEntitiesWithSpeedData(): number {
    return this.entities.filter(e => {
      const speed = e.avg_speed || e.avg_speed;
      return this.isValidSpeed(speed);
    }).length;
  }

  /**
   * Get count of entities without speed data
   * Useful for displaying filter warnings
   */
  getEntitiesWithoutSpeedData(): number {
    return this.entities.filter(e => {
      const speed = e.avg_speed || e.avg_speed;
      return !this.isValidSpeed(speed);
    }).length;
  }

  /**
   * Check if speed filtering is active
   */
  isSpeedFilterActive(): boolean {
    const filters = this.currentFilters();
    return filters !== null && (
      this.isValidSpeed(filters.minSpeed) || 
      this.isValidSpeed(filters.maxSpeed)
    );
  }
}