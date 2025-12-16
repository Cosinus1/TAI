import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GpsLayer } from './gps-layer';

describe('GpsLayer', () => {
  let component: GpsLayer;
  let fixture: ComponentFixture<GpsLayer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GpsLayer]
    })
    .compileComponents();

    fixture = TestBed.createComponent(GpsLayer);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
