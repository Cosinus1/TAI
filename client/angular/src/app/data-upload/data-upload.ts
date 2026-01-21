import { Component, signal } from '@angular/core';
import { Upload } from '../services/upload';
import { HttpEventType } from '@angular/common/http';
import { inject } from '@angular/core';
@Component({
  selector: 'app-data-upload',
  imports: [],
  templateUrl: './data-upload.html',
  styleUrl: './data-upload.scss',
})
export class DataUpload {
  private upload = inject(Upload);


  selectedFormat = signal<string>('');
  showCustomFormat = signal<boolean>(false);
  selectedFile = signal<File | null>(null);
  isUploading = signal<boolean>(false);
  uploadProgress = signal<number>(0)
  uploadMessage = signal<string>('');
  uploadMessageType = signal<'success' | 'error'>('success');

  datasetName = signal<string>('');
  datasetDescription = signal<string>('');
  geoLocation = signal<string>('');

  columns = signal<{ id: number; value: string }[]>([
    { id: 1, value: '' },
    { id: 2, value: '' },
    { id: 3, value: '' },
    { id: 4, value: '' },
  ]);
  nextColumnId = signal<number>(5);

  onFileSelected(event: Event) {
    const target = event.target as HTMLInputElement;
    if (target.files?.length) {
      this.selectedFile.set(target.files[0]);
    }
  }

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

  submitUpload() {
    const file = this.selectedFile();
    if (!file || !this.selectedFormat() || !this.datasetName()) {
      this.showError('Veuillez remplir tous les champs');
      return;
    }

    this.isUploading.set(true);
    this.uploadProgress.set(0);

    this.upload.uploadTDriveFile(
      file,
      this.datasetName(),
      this.datasetDescription(),
      this.geoLocation()
    ).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          this.uploadProgress.set(Math.round((event.loaded / event.total) * 100));
        } else if (event.type === HttpEventType.Response) {
          this.showSuccess('✅ Import réussi!');
          this.resetForm();
          this.isUploading.set(false);
        }
      },
      error: (err) => {
        this.showError('❌ Erreur lors de l\'import');
        this.isUploading.set(false);
      }
    });
  }

  resetForm() {
    this.selectedFile.set(null);
    this.selectedFormat.set('');
    this.datasetName.set('');
    this.datasetDescription.set('');
    this.geoLocation.set('');
    this.uploadProgress.set(0);
  }

  private showSuccess(message: string) {
    this.uploadMessage.set(message);
    this.uploadMessageType.set('success');
  }

  private showError(message: string) {
    this.uploadMessage.set(message);
    this.uploadMessageType.set('error');
  }
}
