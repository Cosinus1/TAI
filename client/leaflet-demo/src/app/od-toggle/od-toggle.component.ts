import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'od-toggle',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="group">
      <label><input type="checkbox" [checked]="show" (change)="onToggle($event.target.checked)" /> Afficher la ligne OD</label>
    </div>
  `,
  styles: [`:host { display:block } .group { margin: 10px 0; }`],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class OdToggleComponent {
  @Input() show = true;
  @Output() showChange = new EventEmitter<boolean>();

  onToggle(checked: boolean) { this.show = checked; this.showChange.emit(checked); }
}
