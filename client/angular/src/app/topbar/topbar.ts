import { Component, inject, ChangeDetectionStrategy, signal } from '@angular/core';
import { Mode } from '../services/mode';
import { DataUpload } from '../data-upload/data-upload';
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: 'app-topbar',
  imports: [DataUpload],
  templateUrl: './topbar.html',
  styleUrl: './topbar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class Topbar {
  private Mode = inject(Mode);

  // on réutilise directement le signal du service
  mode = this.Mode.mode;

  setMode(mode: 'default' | 'od' | 'gps') {
    this.Mode.setMode(mode);
  }

  isModalOpen = signal(false);

  openUploadModal() {
    this.isModalOpen.set(true);
  }

  closeUploadModal() {
    this.isModalOpen.set(false);
  }
}
