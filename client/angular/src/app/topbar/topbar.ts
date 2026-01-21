import { Component, inject, ChangeDetectionStrategy, signal } from '@angular/core';
import { Mode } from '../services/mode';
import { DataUpload } from '../data-upload/data-upload';
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: 'app-topbar',
  imports: [],
  templateUrl: './topbar.html',
  styleUrl: './topbar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class Topbar {
  private Mode = inject(Mode);
  private modalService = inject(NgbModal);

  // on réutilise directement le signal du service
  mode = this.Mode.mode;

  setMode(mode: 'default' | 'od' | 'gps') {
    this.Mode.setMode(mode);
  }

  openUploadModal() {
    this.modalService.open(DataUpload, { size: 'lg' });
  }

}
