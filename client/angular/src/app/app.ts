import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Map } from './map/map';
import { Topbar } from './topbar/topbar';
import { Sidebar } from './sidebar/sidebar';
import { ODPair } from './interfaces/od';
import { Taxi } from './interfaces/gps';
import { Gps } from './services/gps';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Map, Topbar, Sidebar],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit{
    odPairs: ODPair[] = [
    {
      origin: { name: 'Tour Eiffel', lat: 48.8584, lng: 2.2945 },
      destination: { name: 'Louvre', lat: 48.8606, lng: 2.3376 },
    },
    {
      origin: { name: 'Gare du Nord', lat: 48.8809, lng: 2.3553 },
      destination: { name: 'Montparnasse', lat: 48.8400, lng: 2.3200 },
    },
    {
      origin: { name: 'La Défense', lat: 48.8924, lng: 2.2369 },
      destination: { name: 'Champs-Élysées', lat: 48.8698, lng: 2.3073 },
    },
  ];


  // Index sélectionné (null = afficher toutes les paires)
  selectedIndex: number | null = null;
  taxis: Taxi[] = [];
  selectedTaxi: string | null = null;

  constructor(private gps: Gps) {}

  ngOnInit() {
    this.gps.getTaxis().subscribe({
      next: taxis => {
        console.log('taxis loaded', taxis);
        this.taxis = taxis;
      },
      error: err => console.error(err)
    });
  }

  // Handler appelé par le Sidebar quand l'utilisateur choisit une OD
  setSelectedIndex(index: number | null) {
    this.selectedIndex = index;
  }

  setSelectedTaxi(taxiId: string | null) {
    this.selectedTaxi = taxiId;
  }
}
