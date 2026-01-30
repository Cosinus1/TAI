// client/angular/src/app/services/mode.ts
import { Injectable, signal } from '@angular/core';

export type AppMode = 'gps' | 'trajectory';

@Injectable({
  providedIn: 'root'
})
export class Mode {
  mode = signal<AppMode>('gps');
  
  constructor() {
    this.mode.set('gps');
  }
  
  setMode(mode: AppMode) {
    this.mode.set(mode);
    console.log('Mode switched to:', mode);
  }
  
  isGPSMode(): boolean {
    return this.mode() === 'gps';
  }
  
  isTrajectoryMode(): boolean {
    return this.mode() === 'trajectory';
  }
}