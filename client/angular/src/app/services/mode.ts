// client/angular/src/app/services/mode.ts
import { Injectable, signal } from '@angular/core';

export type AppMode = 'gps';

@Injectable({
  providedIn: 'root'
})
export class Mode {
  // Always set to 'gps' mode
  mode = signal<AppMode>('gps');
  
  constructor() {
    // Initialize to GPS mode
    this.mode.set('gps');
  }
  
  // Keep method signature for backward compatibility
  // but always sets to 'gps'
  setMode(mode: AppMode) {
    this.mode.set('gps');
  }
  
  // Helper to check if in GPS mode (always true)
  isGPSMode(): boolean {
    return true;
  }
}