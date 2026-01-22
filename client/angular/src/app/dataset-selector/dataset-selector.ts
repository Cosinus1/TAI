// client/angular/src/app/dataset-selector/dataset-selector.ts
import { Component, Output, EventEmitter, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Gps } from '../services/gps';
import { Dataset } from '../interfaces/gps';

@Component({
  selector: 'app-dataset-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dataset-selector.html',
  styleUrl: './dataset-selector.scss',
})
export class DatasetSelector implements OnInit {
  @Output() datasetSelected = new EventEmitter<Dataset | null>();

  private gps = inject(Gps);

  datasets = signal<Dataset[]>([]);
  selectedDataset = signal<Dataset | null>(null);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.loadDatasets();
  }

  loadDatasets(): void {
    this.loading.set(true);
    this.error.set(null);

    this.gps.getDatasets({ is_active: true }).subscribe({
      next: (datasets) => {
        this.datasets.set(datasets);
        this.loading.set(false);
        
        // Auto-select first dataset if available
        if (datasets.length > 0 && !this.selectedDataset()) {
          this.selectDataset(datasets[0]);
        }
      },
      error: (err) => {
        console.error('Failed to load datasets:', err);
        this.error.set('Failed to load datasets');
        this.loading.set(false);
      }
    });
  }

  selectDataset(dataset: Dataset | null): void {
    this.selectedDataset.set(dataset);
    this.datasetSelected.emit(dataset);
  }

  onDatasetChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const datasetId = select.value;
    
    if (!datasetId) {
      this.selectDataset(null);
      return;
    }

    const dataset = this.datasets().find(d => d.id === datasetId);
    this.selectDataset(dataset || null);
  }

  refresh(): void {
    this.loadDatasets();
  }

  getDatasetIcon(dataset: Dataset): string {
    if (dataset.name.toLowerCase().includes('paris')) return '🗼';
    if (dataset.name.toLowerCase().includes('beijing') || dataset.name.toLowerCase().includes('t-drive')) return '🏯';
    if (dataset.name.toLowerCase().includes('bike')) return '🚲';
    if (dataset.name.toLowerCase().includes('taxi')) return '🚕';
    return '📍';
  }
}