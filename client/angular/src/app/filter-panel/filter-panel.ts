// client/angular/src/app/filter-panel/filter-panel.ts
import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Gps, ExtendedEntityStatistics } from '../services/gps';
import { Dataset } from '../interfaces/gps';

export interface FilterState {
  entityTypes: string[];
  selectedEntityType: string | null;
  selectedEntityId: string | null;
  minSpeed: number | null;
  maxSpeed: number | null;
  startTime: string | null;
  endTime: string | null;
}

@Component({
  selector: 'app-filter-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './filter-panel.html',
  styleUrl: './filter-panel.scss',
})
export class FilterPanel implements OnInit, OnChanges {
  @Input() datasetId: string | null = null;
  @Output() filterChange = new EventEmitter<FilterState>();
  @Output() applyFilters = new EventEmitter<void>();
  @Output() resetFilters = new EventEmitter<void>();
  @Output() entitySelected = new EventEmitter<string | null>();

  private gps = inject(Gps);

  // Entity types
  entityTypes = signal<string[]>([]);
  selectedEntityType = signal<string | null>(null);
  
  // Entity selection
  allEntities = signal<ExtendedEntityStatistics[]>([]);
  selectedEntityId = signal<string | null>(null);
  entitiesLoading = signal<boolean>(false);
  
  // Computed: filtered entities based on selected entity type
  filteredEntities = computed(() => {
    const entities = this.allEntities();
    const selectedType = this.selectedEntityType();
    
    if (!selectedType) {
      return entities;
    }
    
    return entities.filter(e => {
      // Check entity_type property
      if (e.entity_type === selectedType) {
        return true;
      }
      // Fallback: check entity_id prefix
      return e.entity_id.startsWith(selectedType + '_');
    });
  });
  
  // Speed filters
  minSpeed = signal<number | null>(null);
  maxSpeed = signal<number | null>(null);
  
  // Time filters
  startTime = signal<string | null>(null);
  endTime = signal<string | null>(null);
  
  // Loading state
  loading = signal<boolean>(false);

  ngOnInit(): void {
    this.loadEntityTypes();
    this.loadEntities();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['datasetId'] && this.datasetId) {
      this.loadEntityTypes();
      this.loadEntities();
      this.resetAllFilters();
    }
  }

  loadEntityTypes(): void {
    if (!this.datasetId) return;

    this.loading.set(true);
    this.gps.getEntityTypes(this.datasetId).subscribe({
      next: (types) => {
        this.entityTypes.set(types);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load entity types:', err);
        // Fallback to default types
        this.entityTypes.set(['bus', 'bike', 'car', 'taxi']);
        this.loading.set(false);
      }
    });
  }

  loadEntities(): void {
    if (!this.datasetId) return;

    this.entitiesLoading.set(true);
    this.gps.getEntities({
      dataset: this.datasetId,
      min_points: 5
    }).subscribe({
      next: (entities) => {
        console.log('Entities loaded:', entities.length);
        this.allEntities.set(entities);
        this.entitiesLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load entities:', err);
        this.allEntities.set([]);
        this.entitiesLoading.set(false);
      }
    });
  }

  onEntityTypeChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const value = select.value || null;
    this.selectedEntityType.set(value);
    
    // Clear entity selection when type changes
    this.selectedEntityId.set(null);
    this.entitySelected.emit(null);
    
    this.emitFilterChange();
  }

  onEntityIdChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const value = select.value || null;
    this.selectedEntityId.set(value);
    
    // Emit entity selection for trajectory rendering
    this.entitySelected.emit(value);
    
    this.emitFilterChange();
  }

  onMinSpeedChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const value = input.value ? parseFloat(input.value) : null;
    this.minSpeed.set(value);
    this.emitFilterChange();
  }

  onMaxSpeedChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const value = input.value ? parseFloat(input.value) : null;
    this.maxSpeed.set(value);
    this.emitFilterChange();
  }

  onStartTimeChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.startTime.set(input.value || null);
    this.emitFilterChange();
  }

  onEndTimeChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.endTime.set(input.value || null);
    this.emitFilterChange();
  }

  emitFilterChange(): void {
    this.filterChange.emit(this.getCurrentFilters());
  }

  getCurrentFilters(): FilterState {
    return {
      entityTypes: this.entityTypes(),
      selectedEntityType: this.selectedEntityType(),
      selectedEntityId: this.selectedEntityId(),
      minSpeed: this.minSpeed(),
      maxSpeed: this.maxSpeed(),
      startTime: this.startTime(),
      endTime: this.endTime()
    };
  }

  onApply(): void {
    this.applyFilters.emit();
  }

  onReset(): void {
    this.resetAllFilters();
    this.resetFilters.emit();
  }

  resetAllFilters(): void {
    this.selectedEntityType.set(null);
    this.selectedEntityId.set(null);
    this.minSpeed.set(null);
    this.maxSpeed.set(null);
    this.startTime.set(null);
    this.endTime.set(null);
    this.entitySelected.emit(null);
    this.emitFilterChange();
  }

  getEntityTypeColor(type: string): string {
    const colors: { [key: string]: string } = {
      'bus': '#FF5722',
      'bike': '#4CAF50',
      'car': '#2196F3',
      'taxi': '#FFC107'
    };
    return colors[type] || '#9E9E9E';
  }

  getEntityTypeIcon(type: string): string {
    const icons: { [key: string]: string } = {
      'bus': '🚌',
      'bike': '🚲',
      'car': '🚗',
      'taxi': '🚕'
    };
    return icons[type] || '📍';
  }

  hasActiveFilters(): boolean {
    return !!(
      this.selectedEntityType() ||
      this.selectedEntityId() ||
      this.minSpeed() !== null ||
      this.maxSpeed() !== null ||
      this.startTime() ||
      this.endTime()
    );
  }

  /**
   * Get display label for an entity
   */
  getEntityLabel(entity: ExtendedEntityStatistics): string {
    const avgPoints = Math.round(entity.avg_points_per_day);
    const totalPoints = entity.total_points;
    return `${entity.entity_id} (${totalPoints} pts, ${avgPoints}/day)`;
  }
}