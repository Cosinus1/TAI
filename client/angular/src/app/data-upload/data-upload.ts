// client/angular/src/app/data-upload/data-upload.ts
import { Component, signal, inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { Upload } from '../services/upload';
import { HttpEventType } from '@angular/common/http';

@Component({
  selector: 'app-data-upload',
  imports: [],
  templateUrl: './data-upload.html',
  styleUrl: './data-upload.scss',
})
export class DataUpload {
  private upload = inject(Upload);
  modal = inject(NgbActiveModal);

  selectedFormat = signal<string>('');
  showCustomFormat = signal<boolean>(false);
  selectedFiles = signal<File[]>([]);
  isUploading = signal<boolean>(false);
  uploadProgress = signal<number>(0);
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
      const filesArray = Array.from(target.files);
      this.selectedFiles.set(filesArray);
    }
  }

  onFormatChange(event: Event) {
    const target = event.target as HTMLSelectElement;
    const value = target.value;
    
    this.selectedFormat.set(value);
    this.showCustomFormat.set(value === '' || value === 'custom');
  }

  getFormatPreview(): string {
    switch (this.selectedFormat()) {
      case 'tdrive':
        return 'taxi_id, timestamp, longitude, latitude';
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
    const files = this.selectedFiles();
    if (files.length === 0 || !this.selectedFormat() || !this.datasetName()) {
      this.showError('Veuillez remplir tous les champs et sélectionner au moins un fichier');
      return;
    }

    this.isUploading.set(true);
    this.uploadProgress.set(0);
    
    let filesUploaded = 0;
    const totalFiles = files.length;
    
    this.uploadNextFile(files, 0, filesUploaded, totalFiles);
  }
  
  private uploadNextFile(files: File[], index: number, filesUploaded: number, totalFiles: number) {
    if (index >= files.length) {
      this.showSuccess(`✅ Import réussi! ${filesUploaded}/${totalFiles} fichiers importés`);
      this.resetForm();
      this.isUploading.set(false);
      return;
    }
    
    const file = files[index];
    
    this.upload.uploadTDriveFile(
      file,
      this.datasetName(),
      this.datasetDescription(),
      this.geoLocation()
    ).subscribe({
      next: (event) => {
        if (event.type === HttpEventType.UploadProgress && event.total) {
          const fileProgress = Math.round((event.loaded / event.total) * 100);
          const totalProgress = Math.round(((index + fileProgress/100) / totalFiles) * 100);
          this.uploadProgress.set(totalProgress);
        } else if (event.type === HttpEventType.Response) {
          filesUploaded++;
          this.uploadNextFile(files, index + 1, filesUploaded, totalFiles);
        }
      },
      error: (err) => {
        console.error('Upload error:', err);
        this.showError(`❌ Erreur lors de l'import du fichier ${file.name}`);
        this.uploadNextFile(files, index + 1, filesUploaded, totalFiles);
      }
    });
  }

  resetForm() {
    this.selectedFiles.set([]);
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
  
  getFileNamesDisplay(): string {
    const files = this.selectedFiles();
    if (files.length === 0) return '';
    if (files.length === 1) return files[0].name;
    return `${files.length} fichiers sélectionnés`;
  }
}