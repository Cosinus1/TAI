// client/angular/src/app/statistics-panel/statistics-panel.ts
import { Component, Input, OnChanges, SimpleChanges, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Gps, ExtendedDatasetStatistics } from '../services/gps';

@Component({
  selector: 'app-statistics-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './statistics-panel.html',
  styleUrl: './statistics-panel.scss',
})
export class StatisticsPanel implements OnChanges {
  @Input() datasetId: string | null = null;
  
  private gps = inject(Gps);
  
  statistics = signal<ExtendedDatasetStatistics | null>(null);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['datasetId'] && this.datasetId) {
      this.loadStatistics();
    }
  }

  loadStatistics(): void {
    if (!this.datasetId) return;
    
    this.loading.set(true);
    this.error.set(null);
    
    this.gps.getDatasetStatistics(this.datasetId).subscribe({
      next: (stats) => {
        this.statistics.set(stats);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load statistics:', err);
        this.error.set('Failed to load statistics');
        this.loading.set(false);
      }
    });
  }

  getEntityTypeKeys(): string[] {
    const stats = this.statistics();
    if (!stats?.entity_type_breakdown) return [];
    return Object.keys(stats.entity_type_breakdown);
  }

  getEntityTypeColor(type: string): string {
    const colors: { [key: string]: string } = {
      'bus': '#FF5722',
      'bike': '#4CAF50',
      'car': '#2196F3',
      'taxi': '#FFC107',
      'unknown': '#9E9E9E'
    };
    return colors[type] || colors['unknown'];
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  }

  formatNumber(value: number | null | undefined): string {
    if (value === null || value === undefined) return 'N/A';
    return value.toLocaleString();
  }
}