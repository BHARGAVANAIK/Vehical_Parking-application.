<template>
  <div class="container mt-4">

    <!-- Dashboard Title -->
    <h2 class="fw-bold text-primary mb-4">
      <i class="bi bi-speedometer2"></i> Admin Dashboard
    </h2>

    <!-- Success / Error Messages -->
    <transition name="fade">
      <div v-if="msg" class="alert alert-info shadow-sm">{{ msg }}</div>
    </transition>

    <!-- Summary Cards -->
    <div class="row g-3 mb-4">
      <div class="col-md-3" v-for="(value, key) in summary" :key="key">
        <div class="card shadow-sm border-0 summary-card h-100 text-center">
          <div class="card-body">
            <div class="display-6 text-primary mb-2">
              <i :class="summaryIcon(key)"></i>
            </div>
            <h6 class="text-uppercase fw-bold text-muted">{{ key.replaceAll('_', ' ') }}</h6>
            <p class="fs-4 fw-bold m-0">{{ value }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Parking Lot -->
    <div class="card shadow-sm border-0 mb-4">
      <div class="card-header fw-bold text-success bg-light">
        <i class="bi bi-plus-circle"></i> Add Parking Lot
      </div>
      <div class="card-body">
        <form @submit.prevent="addLot" class="row g-2 align-items-end">
          <div class="col">
            <input v-model="newLot.prime_location_name" class="form-control" placeholder="Location Name" required/>
          </div>
          <div class="col">
            <input v-model="newLot.address" class="form-control" placeholder="Address" required/>
          </div>
          <div class="col">
            <input v-model="newLot.pin_code" class="form-control" placeholder="Pin Code" required/>
          </div>
          <div class="col">
            <input v-model.number="newLot.price" type="number" min="0" class="form-control" placeholder="Price" required/>
          </div>
          <div class="col">
            <input v-model.number="newLot.number_of_spots" type="number" min="1" class="form-control" placeholder="Spots" required/>
          </div>
          <div class="col-auto">
            <button class="btn btn-success">
              <i class="bi bi-check-lg"></i> Add
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Parking Lots Table -->
    <div class="card shadow-sm border-0">
      <div class="card-header fw-bold bg-light">
        <i class="bi bi-car-front"></i> Parking Lots
      </div>
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Location</th>
              <th>Address</th>
              <th>Pin Code</th>
              <th>Price</th>
              <th>Available / Total</th>
              <th style="width: 150px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="lot in lots" :key="lot.id">
              <template v-if="editingLotId === lot.id">
                <td><input v-model="editLotData.prime_location_name" class="form-control"/></td>
                <td><input v-model="editLotData.address" class="form-control"/></td>
                <td><input v-model="editLotData.pin_code" class="form-control"/></td>
                <td><input v-model.number="editLotData.price" type="number" class="form-control"/></td>
                <td>
                  <input v-model.number="editLotData.number_of_spots" type="number" class="form-control"/>
                  <small class="text-muted">Available: {{ lot.available_spots }}</small>
                </td>
                <td>
                  <button class="btn btn-sm btn-success me-1" @click="saveLot(lot.id)">
                    <i class="bi bi-save"></i>
                  </button>
                  <button class="btn btn-sm btn-secondary" @click="cancelEdit">
                    <i class="bi bi-x-lg"></i>
                  </button>
                </td>
              </template>
              <template v-else>
                <td class="fw-semibold">{{ lot.prime_location_name }}</td>
                <td>{{ lot.address }}</td>
                <td>{{ lot.pin_code }}</td>
                <td>₹{{ lot.price }}</td>
                <td>
                  <span :class="{'text-success fw-bold': lot.available_spots > 0, 'text-danger fw-bold': lot.available_spots === 0}">
                    {{ lot.available_spots }}
                  </span> / {{ lot.number_of_spots }}
                </td>
                <td>
                  <button class="btn btn-sm btn-warning me-1" @click="editLot(lot)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-danger" @click="deleteLot(lot)" :disabled="lot.available_spots !== lot.number_of_spots">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Registered Users -->
    <div class="card shadow-sm border-0 mt-4">
      <div class="card-header fw-bold bg-light">
        <i class="bi bi-people"></i> Registered Users
      </div>
      <div class="table-responsive">
        <table class="table table-striped align-middle mb-0">
          <thead>
            <tr>
              <th>User ID</th>
              <th>Username</th>
              <th>Email</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td class="fw-semibold">{{ user.id }}</td>
              <td>{{ user.username }}</td>
              <td>{{ user.email }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Chart Section -->
    <div class="card shadow-sm border-0 my-4">
      <div class="card-header fw-bold bg-light">
        <i class="bi bi-bar-chart-fill"></i> Bookings per Lot
      </div>
      <div class="card-body" style="height: 300px;">
        <BarChart v-if="chartData" :chartData="chartData" :chartOptions="chartOptions"/>
        <div v-else class="text-muted">No chart data available.</div>
      </div>
    </div>

  </div>
</template>

<script>
import axios from '../axios';
import BarChart from './charts/BarChart.vue';

export default {
  name: 'AdminDashboard',
  components: { BarChart },
  data() {
    return {
      summary: {},
      lots: [],
      newLot: { prime_location_name: '', address: '', pin_code: '', price: '', number_of_spots: '' },
      msg: '',
      users: [],
      editingLotId: null,
      editLotData: {},
      chartData: null,
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: true }, tooltip: { enabled: true } },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: 'Number of Bookings' } },
          x: { title: { display: true, text: 'Parking Lot Location' } }
        }
      }
    };
  },
  async mounted() {
    await Promise.all([this.fetchSummary(), this.fetchLots(), this.fetchUsers(), this.fetchChartData()]);
  },
  methods: {
    summaryIcon(key) {
      const icons = {
        total_users: 'bi bi-people-fill',
        total_lots: 'bi bi-car-front-fill',
        total_bookings: 'bi bi-calendar-check-fill',
        revenue: 'bi bi-cash-stack'
      };
      return icons[key] || 'bi bi-info-circle-fill';
    },
    async fetchSummary() {
      try {
        const res = await axios.get('/admin/summary');
        this.summary = res.data;
      } catch (err) {
        this.msg = err.response?.data?.msg || "Error fetching summary";
      }
    },
    async fetchLots() {
      try {
        const res = await axios.get('/admin/parking-lots');
        this.lots = res.data;
      } catch (err) {
        this.msg = err.response?.data?.msg || "Error fetching parking lots";
      }
    },
    async addLot() {
      try {
        await axios.post('/admin/parking-lots', this.newLot);
        this.msg = "✅ Parking lot added!";
        this.newLot = { prime_location_name: '', address: '', pin_code: '', price: '', number_of_spots: '' };
        await Promise.all([this.fetchLots(), this.fetchSummary(), this.fetchChartData()]);
      } catch (err) {
        this.msg = err.response?.data?.msg || "Error adding lot";
      }
    },
    async deleteLot(lot) {
      if (confirm('Delete this lot? Only possible if all spots are empty.')) {
        try {
          await axios.delete(`/admin/parking-lots/${lot.id}`);
          this.msg = "🗑 Parking lot deleted!";
          await Promise.all([this.fetchLots(), this.fetchSummary(), this.fetchChartData()]);
        } catch (err) {
          this.msg = err.response?.data?.msg || "Error deleting lot";
        }
      }
    },
    editLot(lot) {
      this.editingLotId = lot.id;
      this.editLotData = { ...lot };
    },
    cancelEdit() {
      this.editingLotId = null;
      this.editLotData = {};
    },
    async saveLot(lotId) {
      try {
        await axios.put(`/admin/parking-lots/${lotId}`, this.editLotData);
        this.msg = "✅ Parking lot updated!";
        this.cancelEdit();
        await Promise.all([this.fetchLots(), this.fetchSummary(), this.fetchChartData()]);
      } catch (err) {
        this.msg = err.response?.data?.msg || "Error updating lot";
      }
    },
    async fetchUsers() {
      try {
        const res = await axios.get('/admin/users');
        this.users = res.data;
      } catch (err) {
        this.msg = err.response?.data?.msg || "Error fetching users";
      }
    },
    async fetchChartData() {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get('/admin/summary-charts', {
          headers: { Authorization: `Bearer ${token}` }
        });
        this.chartData = {
          labels: res.data.lots,
          datasets: [{ label: 'Bookings', data: res.data.bookings, backgroundColor: '#0d6efd' }]
        };
      } catch (err) {
        this.msg = err.response?.data?.msg || "Error fetching chart data";
      }
    }
  }
};
</script>

<style scoped>
.summary-card {
  border-radius: 10px;
  transition: transform 0.2s ease-in-out;
}
.summary-card:hover {
  transform: translateY(-4px);
}
.table-hover tbody tr:hover {
  background-color: rgba(13, 110, 253, 0.05);
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter, .fade-leave-to { opacity: 0; }
</style>
