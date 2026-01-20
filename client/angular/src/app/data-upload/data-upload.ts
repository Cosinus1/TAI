import { Component, signal } from '@angular/core';

@Component({
  selector: 'app-data-upload',
  imports: [],
  templateUrl: './data-upload.html',
  styleUrl: './data-upload.scss',
})
export class DataUpload {
  selectedFormat = signal<string>('');
  showCustomFormat = signal<boolean>(false);

  columns = signal<{ id: number; value: string }[]>([
    { id: 1, value: '' },
    { id: 2, value: '' },
    { id: 3, value: '' },
    { id: 4, value: '' },
  ]);
  nextColumnId = signal<number>(5);

  onFormatChange(event: Event) {
    const target = event.target as HTMLSelectElement;
    const value = target.value;
    
    this.selectedFormat.set(value);
    
    // Afficher le formulaire personnalisé si aucun format ou "custom"
    this.showCustomFormat.set(value === '' || value === 'custom');
  }

  getFormatPreview(): string {
    switch (this.selectedFormat()) {
      case 'tdrive':
        return 'taxi_id, latitude, longitude, timestamp';
      case 'csv':
        return 'latitude, longitude, timestamp';
      case 'custom':
        return 'Format personnalisé (à définir)';
      default:
        return 'Sélectionnez un format';
    }
  }

    addColumn() {
    const currentColumns = this.columns();
    const newId = this.nextColumnId();
    this.columns.set([...currentColumns, { id: newId, value: '' }]);
    this.nextColumnId.set(newId + 1);
  }

  removeColumn(id: number) {
    const currentColumns = this.columns();
    if (currentColumns.length > 1) {
      this.columns.set(currentColumns.filter(col => col.id !== id));
    }
  }

  updateColumn(id: number, value: string) {
    const currentColumns = this.columns();
    this.columns.set(
      currentColumns.map(col => 
        col.id === id ? { ...col, value } : col
      )
    );
  }
}
