import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PoiFiltersComponent } from '../poi-filters/poi-filters.component';
import { OdToggleComponent } from '../od-toggle/od-toggle.component';
import type { ODPair } from '../models/od.model';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, FormsModule, PoiFiltersComponent, OdToggleComponent],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SidebarComponent {
  // --- Notes générales ---
  // Composant `Sidebar` autonome utilisé pour contrôler les filtres de la carte.
  // Il expose des `@Input` pour initialiser l'interface (valeurs persistées, liste OD,
  // liste des taxis disponibles, etc.) et des `@Output` pour notifier le parent
  // (MapComponent) des actions de l'utilisateur (changement OD, application des filtres,
  // demande de taxi, sélection de taxi, contrôles temporels, play/pause).

  // --- Entrées (Inputs) ---
  // Valeurs de début/fin de filtre temporel (chaînes `datetime-local` ou null).
  @Input() startTime: string | null = null;
  @Input() endTime: string | null = null;
  ngOnChanges(changes: SimpleChanges) {
    if (changes['startTime'] && typeof changes['startTime'].currentValue === 'string') {
      this.startTimeStr = changes['startTime'].currentValue;
    }
    if (changes['endTime'] && typeof changes['endTime'].currentValue === 'string') {
      this.endTimeStr = changes['endTime'].currentValue;
    }
  }
  @Input() odPairs: ODPair[] = [];
  @Input() selectedIndex = 0;
  @Input() showRestaurant = true;
  @Input() showCafe = true;
  @Input() showCinema = true;
  @Input() showODLine = true;
  // list of available taxi ids (populated by parent if taxi data available)
  @Input() taxiList: string[] = [];
  @Input() selectedTaxiId: string | null = null;

  // --- Sorties (Outputs) — événements émis vers le parent ---
  // Emis quand l'utilisateur change la paire OD sélectionnée (index de l'option)
  @Output() odChange = new EventEmitter<number>();
  // Emis quand les filtres POI changent
  @Output() filtersChange = new EventEmitter<{ restaurant: boolean; cafe: boolean; cinema: boolean }>();
  // Emis quand l'utilisateur clique sur "Appliquer"
  @Output() apply = new EventEmitter<void>();
  // Emis quand l'utilisateur clique sur "Réinitialiser"
  @Output() reset = new EventEmitter<void>();
  // Emis quand on montre/masque la ligne OD
  @Output() showChange = new EventEmitter<boolean>();
  // Demande explicite de récupération de taxis (utile si backend était arrêté)
  @Output() taxiRequest = new EventEmitter<void>();
  // Emis quand l'utilisateur sélectionne un taxi (ou vide pour aucun)
  @Output() taxiSelect = new EventEmitter<string | null>();
  // Contrôles temporels: émission d'un nouvel intervalle start/end (strings)
  @Output() timeRangeChange = new EventEmitter<{ start: string | null; end: string | null }>();
  // Play/Pause pour l'animation temporelle
  @Output() playToggle = new EventEmitter<boolean>();

  // local state for controls (string ISO local) - initialized empty
  startTimeStr: string | null = null;
  endTimeStr: string | null = null;
  playing = false;
  // --- Méthodes utilitaires appelées depuis le template ---
  // Émet l'index sélectionné dans la liste OD
  emitOdChange(e: Event) { const select = e.target as HTMLSelectElement; this.odChange.emit(Number(select.value)); }
  // Émet les filtres POI courants
  onFiltersChange(f: { restaurant: boolean; cafe: boolean; cinema: boolean }) { this.filtersChange.emit(f); }
  // Demande d'application des options (recherche POI, redraw)
  onApply() { this.apply.emit(); }
  // Réinitialise les filtres aux valeurs par défaut
  onReset() { this.reset.emit(); }
  // Montre/masque la ligne OD
  onShowChange(v: boolean) { this.showChange.emit(v); }
  // Demande manuelle au parent de récupérer des taxis (utile pour le mock)
  requestTaxi() { this.taxiRequest.emit(); }
  // Sélection d'un taxi dans le select; vide => null
  selectTaxi(e: Event) { const s = e.target as HTMLSelectElement; this.taxiSelect.emit(s.value === '' ? null : s.value); }
  // Émet le couple start/end sélectionné pour filtrer les points
  emitTimeRange() { this.timeRangeChange.emit({ start: this.startTimeStr, end: this.endTimeStr }); }
  // Basculer play/pause et avertir le parent
  togglePlay() { this.playing = !this.playing; this.playToggle.emit(this.playing); }
}
