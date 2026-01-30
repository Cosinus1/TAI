import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { DataUpload } from '../data-upload/data-upload';
import { Mode } from '../services/mode';

@Component({
  selector: 'app-topbar',
  imports: [],
  templateUrl: './topbar.html',
  styleUrl: './topbar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class Topbar {
  private modalService = inject(NgbModal);
  private Mode = inject(Mode);
  
  mode = this.Mode.mode;

  ngOnInit() {
    // Ensure GPS mode is set on initialization
    this.Mode.setMode('gps');
  }

  openUploadModal() {
    this.modalService.open(DataUpload, { size: 'lg' });
  }
}