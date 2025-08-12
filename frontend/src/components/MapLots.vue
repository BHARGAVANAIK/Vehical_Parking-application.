<template>
  <div class="container mt-5">
    <h3 class="mb-4 text-primary">
      <i class="bi bi-map"></i> Parking Lots Map
    </h3>
    <div id="map" class="map-container rounded shadow-sm"></div>
  </div>
</template>

<script>
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import markerClusterGroup from 'leaflet.markercluster';
import axios from '../axios';

// Custom colored marker icons for availability status
const greenIcon = new L.Icon({
  iconUrl: 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon-2x-green.png',
  shadowUrl: 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const orangeIcon = new L.Icon({
  iconUrl: 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon-2x-orange.png',
  shadowUrl: 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const redIcon = new L.Icon({
  iconUrl: 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-icon-2x-red.png',
  shadowUrl: 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

export default {
  data() {
    return {
      lots: [],
      map: null,
      markersCluster: null,
    };
  },
  async mounted() {
    try {
      const res = await axios.get('/user/parking-lots');
      this.lots = res.data;
      this.initMap();
    } catch (error) {
      console.error('Failed to load parking lots:', error);
    }
  },
  methods: {
    initMap() {
      // Initialize map centered at Bangalore with zoom level 12
      this.map = L.map('map', {
        center: [12.9716, 77.5946],
        zoom: 12,
        zoomControl: true,
        scrollWheelZoom: true,
      });

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data © OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(this.map);

      // Use marker clustering for better visualization
      this.markersCluster = markerClusterGroup();
      this.markersCluster.addTo(this.map);

      // Add markers with custom icons based on availability
      this.lots.forEach(lot => {
        if (lot.latitude && lot.longitude) {
          let icon;
          if (lot.available_spots > 5) icon = greenIcon;
          else if (lot.available_spots > 0) icon = orangeIcon;
          else icon = redIcon;

          const popupContent = `
            <div style="font-weight:bold; font-size:1.1em; margin-bottom:0.3em;">
              ${lot.prime_location_name}
            </div>
            <div>${lot.address}</div>
            <div style="margin-top:0.5em;">
              <strong>Available Spots:</strong> ${lot.available_spots}
            </div>
            <div style="margin-top:0.5em;">
              <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(lot.address)}" target="_blank" rel="noopener" style="text-decoration:none; color:#007bff;">
                <i class="bi bi-geo-alt"></i> Open in Google Maps
              </a>
            </div>
          `;

          const marker = L.marker([lot.latitude, lot.longitude], { icon })
            .bindPopup(popupContent);

          this.markersCluster.addLayer(marker);
        }
      });

      // Fit map bounds to markers if any available
      const bounds = L.latLngBounds(this.lots
        .filter(lot => lot.latitude && lot.longitude)
        .map(lot => [lot.latitude, lot.longitude]));

      if (bounds.isValid()) {
        this.map.fitBounds(bounds.pad(0.1));
      }
    }
  }
};
</script>

<style scoped>
.map-container {
  height: 400px;
  width: 100%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

</style>
