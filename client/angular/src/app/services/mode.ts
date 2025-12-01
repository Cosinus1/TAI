import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class Mode {
    // le mode vaut soit 'default' soit 'od'
  readonly mode = signal<'default' | 'od' | 'gps'>('default');

  setMode(mode: 'default' | 'od' | 'gps') {
    this.mode.set(mode);
  }

  toggleOd() {
    this.mode.update(current =>
      current === 'od' ? 'default' : 'od'
    );
  }

  toggleGps() {
    this.mode.update(current =>
      current === 'gps' ? 'default' : 'gps'
    );
  }
}
