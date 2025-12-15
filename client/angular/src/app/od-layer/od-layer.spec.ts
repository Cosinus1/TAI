import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OdLayer } from './od-layer';

describe('OdLayer', () => {
  let component: OdLayer;
  let fixture: ComponentFixture<OdLayer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OdLayer]
    })
    .compileComponents();

    fixture = TestBed.createComponent(OdLayer);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
