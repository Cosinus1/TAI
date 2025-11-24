import { TestBed } from '@angular/core/testing';

import { Mode } from './mode';

describe('Mode', () => {
  let service: Mode;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Mode);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
