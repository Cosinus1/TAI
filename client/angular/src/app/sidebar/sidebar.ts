import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { Mode } from '../services/mode';
import { ODPair } from '../interfaces/od';
import { Taxi } from '../interfaces/gps';


@Component({
  selector: 'app-sidebar',
  imports: [],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
})

export class Sidebar {  
  @Input() odPairs: ODPair[] = [];
  // Événement émis lorsque l'utilisateur sélectionne une paire OD.
  // On émet `number | null` : `null` signifie "tous les OD".
  @Input() taxis: Taxi[] = [];
  @Output() odChange = new EventEmitter<number | null>();
  @Output() taxiChange = new EventEmitter<string | null>();
  @Output() apply = new EventEmitter<void>();
  @Output() reset = new EventEmitter<void>();
  @Output() showChange = new EventEmitter<boolean>();

  private Mode = inject(Mode);
  mode = this.Mode.mode;

  emitOdChange(e: Event) {
    const select = e.target as HTMLSelectElement;
    // Si la valeur est vide, on l'interprète comme "tous les OD" -> null
    const raw = select.value;
    if (raw === '') {
      this.odChange.emit(null);
      return;
    }
    const index = Number(raw);
    this.odChange.emit(Number.isNaN(index) ? null : index);
  }


  emitTaxiChange(e: Event) {
    const select = e.target as HTMLSelectElement;
    const taxiId = select.value || null;
    this.taxiChange.emit(taxiId);
  }
  
  onApply() { 
    this.apply.emit(); 
  }

  onReset() { 
    this.reset.emit(); 
  }

  onShowChange(v: boolean) { 
    this.showChange.emit(v); 
  }
}
