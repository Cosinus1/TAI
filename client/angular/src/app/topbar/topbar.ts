// client/angular/src/app/topbar/topbar.ts
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
  private modeService = inject(Mode);
  
  mode = this.modeService.mode;

  ngOnInit() {
    this.modeService.setMode('gps');
  }

  setMode(mode: 'gps' | 'trajectory') {
    this.modeService.setMode(mode);
  }

  openUploadModal() {
    this.modalService.open(DataUpload, { size: 'lg' });
  }
}