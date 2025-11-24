import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class Mode {
    // le mode vaut soit 'default' soit 'od'
  readonly mode = signal<'default' | 'od'>('default');

  setMode(mode: 'default' | 'od') {
    this.mode.set(mode);
  }

  toggleOd() {
    this.mode.update(current =>
      current === 'od' ? 'default' : 'od'
    );
  }
}
