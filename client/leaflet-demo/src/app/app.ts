import { Component, signal, ChangeDetectionStrategy } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MapComponent } from './map/map';
import { TopbarComponent } from './topbar/topbar.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, TopbarComponent, MapComponent],
  templateUrl: './app.html',
  styleUrls: ['./app.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class App {
  protected readonly title = signal<string>('leaflet-demo');
  // displayMode shared with topbar and map
  displayMode = signal<'od' | 'taxi'>('od');

  onModeChange(mode: 'od' | 'taxi') {
    this.displayMode.set(mode);
  }
}
