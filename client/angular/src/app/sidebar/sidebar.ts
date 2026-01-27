// client/angular/src/app/sidebar/sidebar.ts
import { Component, Input, Output, EventEmitter, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Mode } from '../services/mode';
import { ODPair } from '../interfaces/od';
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
  @Input() odPairs: ODPair[] = [];
  @Input() entities: EntityStatistics[] = [];
  
  @Output() odChange = new EventEmitter<number | null>();
  @Output() taxiChange = new EventEmitter<string | null>();
  @Output() datasetChange = new EventEmitter<Dataset | null>();
  @Output() filterChange = new EventEmitter<FilterState>();
  @Output() apply = new EventEmitter<void>();
  @Output() reset = new EventEmitter<void>();
  @Output() showChange = new EventEmitter<boolean>();

  private Mode = inject(Mode);
  mode = this.Mode.mode;

  // Current selected dataset
  currentDataset = signal<Dataset | null>(null);
  
  // Current filters
  currentFilters = signal<FilterState | null>(null);
  
  // Show statistics panel
  showStats = signal<boolean>(true);

  emitOdChange(e: Event) {
    const select = e.target as HTMLSelectElement;
    const raw = select.value;
    if (raw === '') {
      this.odChange.emit(null);
      return;
    }
    const index = Number(raw);
    this.odChange.emit(Number.isNaN(index) ? null : index);
  }

  emitTaxiChange(e: Event) {
    const select = e.target as HTMLSelectElement;
    const taxiId = select.value || null;
    this.taxiChange.emit(taxiId);
  }

  onDatasetSelected(dataset: Dataset | null) {
    this.currentDataset.set(dataset);
    this.datasetChange.emit(dataset);
  }

  onFilterChange(filters: FilterState) {
    this.currentFilters.set(filters);
    this.filterChange.emit(filters);
  }

  /**
   * Handle entity selection from the filter panel
   * This triggers trajectory rendering for the selected entity
   */
  onEntitySelected(entityId: string | null) {
    console.log('Entity selected for trajectory:', entityId);
    this.taxiChange.emit(entityId);
  }

  onApplyFilters() {
    this.apply.emit();
  }

  onResetFilters() {
    this.reset.emit();
  }

  toggleStats() {
    this.showStats.update(v => !v);
  }

  onApply() {
    this.apply.emit();
  }

  onReset() {
    this.reset.emit();
  }

  onShowChange(v: boolean) {
    this.showChange.emit(v);
  }

  getFilteredEntities(): EntityStatistics[] {
    const filters = this.currentFilters();
    if (!filters || !filters.selectedEntityType) {
      return this.entities;
    }
    return this.entities.filter(e => 
      e.entity_id.startsWith(filters.selectedEntityType!)
    );
  }
}