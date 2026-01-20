import { HttpClient, HttpEvent, HttpProgressEvent } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface UploadResponse {
  success: boolean;
  message: string;
  batch_id?: string;
  points_imported?: number;
  errors?: string[];
}

@Injectable({
  providedIn: 'root',
})

export class Upload {
  private apiUrl = 'http://localhost:8000/api/mobility/import';

  constructor(private http: HttpClient) {}

  uploadTDriveFile(
    file: File,
    datasetName: string,
    datasetDescription: string,
    geoLocation: string
  ): Observable<HttpEvent<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('dataset_name', datasetName);
    formData.append('dataset_description', datasetDescription);
    formData.append('geo_location', geoLocation);
    formData.append('format', 'tdrive');

    return this.http.post<UploadResponse>(
      this.apiUrl,
      formData,
      { reportProgress: true, responseType: 'json' as any, observe: 'events' }
    );

  }

  uploadCustomFormatFile(
    file: File,
    columnMapping: { [key: number]: string },
    separator: string,
    hasHeader: boolean,
    datasetName: string,
    datasetDescription: string,
    geoLocation: string
  ): Observable<HttpEvent<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('column_mapping', JSON.stringify(columnMapping));
    formData.append('separator', separator);
    formData.append('has_header', String(hasHeader));
    formData.append('dataset_name', datasetName);
    formData.append('dataset_description', datasetDescription);
    formData.append('geo_location', geoLocation);
    formData.append('format', 'custom');

    return this.http.post<UploadResponse>(
      this.apiUrl,
      formData,
      { reportProgress: true, responseType: 'json' as any, observe: 'events' }
    );
  }
}
