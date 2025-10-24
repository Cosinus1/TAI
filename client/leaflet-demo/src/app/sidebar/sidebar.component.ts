import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PoiFiltersComponent } from '../poi-filters/poi-filters.component';
import { OdToggleComponent } from '../od-toggle/od-toggle.component';
import type { ODPair } from '../models/od.model';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, PoiFiltersComponent, OdToggleComponent],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SidebarComponent {
  @Input() odPairs: ODPair[] = [];
  @Input() selectedIndex = 0;
  @Input() showRestaurant = true;
  @Input() showCafe = true;
  @Input() showCinema = true;
  @Input() showODLine = true;

  @Output() odChange = new EventEmitter<number>();
  @Output() filtersChange = new EventEmitter<{ restaurant: boolean; cafe: boolean; cinema: boolean }>();
  @Output() apply = new EventEmitter<void>();
  @Output() reset = new EventEmitter<void>();
  @Output() showChange = new EventEmitter<boolean>();
  @Output() taxiRequest = new EventEmitter<void>();

  emitOdChange(e: Event) { const select = e.target as HTMLSelectElement; this.odChange.emit(Number(select.value)); }
  onFiltersChange(f: { restaurant: boolean; cafe: boolean; cinema: boolean }) { this.filtersChange.emit(f); }
  onApply() { this.apply.emit(); }
  onReset() { this.reset.emit(); }
  onShowChange(v: boolean) { this.showChange.emit(v); }
  requestTaxi() { this.taxiRequest.emit(); }
}
