import { HttpClient, HttpEvent } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ImportJobCreate, Dataset } from '../interfaces/gps';

@Injectable({
  providedIn: 'root',
})

export class Upload {
  private http = inject(HttpClient);

  private apiUrl = 'http://localhost:8000/api';


  uploadTDriveFile(
    file: File,
    datasetName: string,
    description: string,
    geoLocation: string
  ): Observable<HttpEvent<any>> {
    
    const formData = new FormData();
    console.log('📁 Fichier à uploader:', file.name, `(${(file.size / 1024).toFixed(2)} KB)`);
    formData.append('file', file);
    console.log('📝 Métadonnées:', { datasetName, description, geoLocation });
    formData.append('dataset_name', datasetName);
    formData.append('description', description);
    formData.append('geographic_scope', geoLocation);
    formData.append('source_type', 'file');
    formData.append('file_format', 'txt');
    formData.append('delimiter', ',');
    formData.append('skip_header', 'true');
    
    // T-Drive field mapping: taxi_id -> entity_id
    const fieldMapping = {
      'taxi_id': 'entity_id',
      'latitude': 'latitude',
      'longitude': 'longitude',
      'timestamp': 'timestamp'
    };
    console.log('🗂️ Field mapping:', fieldMapping);
    formData.append('field_mapping', JSON.stringify(fieldMapping));

    console.log('🚀 Envoi vers:', `${this.apiUrl}/imports/start_import/`);
    console.log('📦 Contenu du FormData envoyé :');
    formData.forEach((value, key) => {
      if (value instanceof File) {
        console.log(`- ${key}: File(name=${value.name}, size=${value.size}, type=${value.type})`);
      } else {
        console.log(`- ${key}:`, value);
      }
    });
    return this.http.post(
      `${this.apiUrl}/imports/start_import/`,
      formData,
      { reportProgress: true, responseType: 'json', observe: 'events' }
    );
  }
}
