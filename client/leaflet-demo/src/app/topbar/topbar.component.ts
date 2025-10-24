import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

export type DisplayMode = 'od' | 'taxi';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './topbar.component.html',
  styleUrls: ['./topbar.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TopbarComponent {
  @Input() mode: DisplayMode = 'od';
  @Output() modeChange = new EventEmitter<DisplayMode>();

  setMode(m: DisplayMode) {
    if (m === this.mode) return;
    this.mode = m;
    this.modeChange.emit(m);
  }
}
