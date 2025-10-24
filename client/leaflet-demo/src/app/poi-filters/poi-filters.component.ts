import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'poi-filters',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './poi-filters.component.html',
  styleUrls: ['./poi-filters.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PoiFiltersComponent {
  @Input() showRestaurant = true;
  @Input() showCafe = true;
  @Input() showCinema = true;

  @Output() filtersChange = new EventEmitter<{ restaurant: boolean; cafe: boolean; cinema: boolean }>();
  @Output() apply = new EventEmitter<void>();
  @Output() reset = new EventEmitter<void>();

  onToggle(type: 'restaurant' | 'cafe' | 'cinema', checked: boolean) {
    if (type === 'restaurant') this.showRestaurant = checked;
    if (type === 'cafe') this.showCafe = checked;
    if (type === 'cinema') this.showCinema = checked;
    this.filtersChange.emit({ restaurant: this.showRestaurant, cafe: this.showCafe, cinema: this.showCinema });
  }

  onApply() { this.apply.emit(); }
  onReset() { this.reset.emit(); }
}
