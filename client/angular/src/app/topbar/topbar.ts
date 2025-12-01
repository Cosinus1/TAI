import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { Mode } from '../services/mode';

@Component({
  selector: 'app-topbar',
  imports: [],
  templateUrl: './topbar.html',
  styleUrl: './topbar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class Topbar {
  private Mode = inject(Mode);

  // on réutilise directement le signal du service
  mode = this.Mode.mode;

  setMode(mode: 'default' | 'od' | 'gps') {
    this.Mode.setMode(mode);
  }
}
