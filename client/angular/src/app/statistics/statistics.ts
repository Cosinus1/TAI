// client/angular/src/app/statistics/statistics.ts
import { Component, Input, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Gps } from '../services/gps';

@Component({
  selector: 'app-statistics',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="statistics-panel">
      <h3 class="panel-title">Dataset Statistics</h3>
      
      @if (loading) {
        <div class="loading">
          <div class="spinner"></div>
          <p>Loading statistics...</p>
        </div>
      } @else if (stats) {
        <div class="stats-grid">
          <!-- Total Points -->
          <div class="stat-card primary">
            <div class="stat-icon">📍</div>
            <div class="stat-content">
              <div class="stat-value">{{ formatNumber(stats.total_points) }}</div>
              <div class="stat-label">Total Points</div>
            </div>
          </div>

          <!-- Total Entities -->
          <div class="stat-card secondary">
            <div class="stat-icon">🚕</div>
            <div class="stat-content">
              <div class="stat-value">{{ formatNumber(stats.total_entities) }}</div>
              <div class="stat-label">Entities</div>
            </div>
          </div>

          <!-- Validity Rate -->
          <div class="stat-card success">
            <div class="stat-icon">✅</div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.validity_rate }}%</div>
              <div class="stat-label">Valid Data</div>
            </div>
          </div>

          <!-- Total Trajectories -->
          <div class="stat-card info">
            <div class="stat-icon">📈</div>
            <div class="stat-content">
              <div class="stat-value">{{ formatNumber(stats.total_trajectories) }}</div>
              <div class="stat-label">Trajectories</div>
            </div>
          </div>
        </div>

        <!-- Date Range -->
        @if (stats.date_range) {
          <div class="date-range">
            <h4>Temporal Coverage</h4>
            <div class="date-info">
              <span class="date-label">From:</span>
              <span class="date-value">{{ formatDate(stats.date_range.start) }}</span>
            </div>
            <div class="date-info">
              <span class="date-label">To:</span>
              <span class="date-value">{{ formatDate(stats.date_range.end) }}</span>
            </div>
          </div>
        }

        <!-- Geographic Bounds -->
        @if (stats.geographic_bounds) {
          <div class="geo-bounds">
            <h4>Geographic Bounds</h4>
            <div class="bounds-grid">
              <div class="bound-item">
                <span class="bound-label">Longitude:</span>
                <span class="bound-value">
                  {{ stats.geographic_bounds.min_lon.toFixed(4) }} → 
                  {{ stats.geographic_bounds.max_lon.toFixed(4) }}
                </span>
              </div>
              <div class="bound-item">
                <span class="bound-label">Latitude:</span>
                <span class="bound-value">
                  {{ stats.geographic_bounds.min_lat.toFixed(4) }} → 
                  {{ stats.geographic_bounds.max_lat.toFixed(4) }}
                </span>
              </div>
            </div>
          </div>
        }
      } @else {
        <div class="no-data">
          <p>No statistics available</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .statistics-panel {
      background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
      border-radius: 12px;
      padding: 20px;
      color: white;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .panel-title {
      margin: 0 0 20px 0;
      font-size: 20px;
      font-weight: 600;
      color: white;
    }

    .loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      padding: 40px 20px;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }

    .stat-card {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      align-items: center;
      gap: 12px;
      transition: transform 0.2s, background 0.2s;
    }

    .stat-card:hover {
      transform: translateY(-2px);
      background: rgba(255, 255, 255, 0.15);
    }

    .stat-card.primary { border-left: 4px solid #3b82f6; }
    .stat-card.secondary { border-left: 4px solid #8b5cf6; }
    .stat-card.success { border-left: 4px solid #10b981; }
    .stat-card.info { border-left: 4px solid #06b6d4; }

    .stat-icon {
      font-size: 28px;
    }

    .stat-content {
      flex: 1;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 700;
      line-height: 1.2;
    }

    .stat-label {
      font-size: 12px;
      opacity: 0.8;
      margin-top: 4px;
    }

    .date-range,
    .geo-bounds {
      background: rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 16px;
      margin-top: 12px;
    }

    .date-range h4,
    .geo-bounds h4 {
      margin: 0 0 12px 0;
      font-size: 14px;
      font-weight: 600;
      opacity: 0.9;
    }

    .date-info,
    .bound-item {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .date-info:last-child,
    .bound-item:last-child {
      border-bottom: none;
    }

    .date-label,
    .bound-label {
      font-size: 13px;
      opacity: 0.8;
    }

    .date-value,
    .bound-value {
      font-size: 13px;
      font-weight: 600;
    }

    .bounds-grid {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .no-data {
      text-align: center;
      padding: 40px 20px;
      opacity: 0.7;
    }
  `]
})
export class Statistics implements OnInit {
  @Input() datasetId?: string;
  
  private gps = inject(Gps);
  
  stats: any = null;
  loading = false;

  ngOnInit() {
    if (this.datasetId) {
      this.loadStatistics();
    }
  }

  loadStatistics() {
    this.loading = true;
    this.gps.getDatasetStatistics(this.datasetId!).subscribe({
      next: (data) => {
        this.stats = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load statistics:', err);
        this.loading = false;
      }
    });
  }

  formatNumber(num: number): string {
    return num.toLocaleString();
  }

  formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }
}