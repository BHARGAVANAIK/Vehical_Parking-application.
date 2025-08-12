<template>
  <div class="container mt-5">
    <div class="row">
      <div class="col-12 col-md-10 offset-md-1">

        <!-- Top Actions -->
        <div class="d-flex justify-content-end mb-3 gap-2">
          <router-link
            to="/booking-history"
            class="btn btn-outline-secondary"
            aria-label="View your booking history"
          >
            <i class="bi bi-clock-history"></i> My Booking History
          </router-link>
          <button
            class="btn btn-outline-danger"
            @click="logout"
            aria-label="Logout"
          >
            <i class="bi bi-box-arrow-right"></i> Logout
          </button>
        </div>

        <!-- Title -->
        <h2 class="mb-4 fw-bold text-primary">
          <i class="bi bi-car-front"></i>
          Available Parking Lots
        </h2>

        <!-- Search -->
        <input
          v-model="searchQuery"
          type="text"
          class="form-control mb-3"
          placeholder="Search by location or address..."
          aria-label="Search parking lots"
        />

        <!-- Loading -->
        <div v-if="loading" class="text-center my-5">
          <div class="spinner-border text-primary" role="status"></div>
          <div>Loading parking lots...</div>
        </div>

        <!-- Error -->
        <transition name="fade">
          <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>
        </transition>

        <!-- No Results -->
        <transition name="fade">
          <div
            v-if="!loading && filteredLots.length === 0 && !error"
            class="alert alert-warning"
          >
            No parking lots found.
          </div>
        </transition>

        <!-- Parking Lots List -->
        <div class="parking-lots-list-container">
          <div
            v-for="lot in paginatedLots"
            :key="lot.id"
            class="card mb-3 shadow-sm hover-card"
          >
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <h5 class="card-title mb-1">
                    <i class="bi bi-geo-alt-fill text-primary"></i>
                    {{ lot.prime_location_name }}
                  </h5>
                  <p class="mb-1 text-muted">
                    <small>
                      Address: {{ lot.address }}
                      <button
                        class="btn btn-outline-primary btn-sm ms-2"
                        @click="openInMaps(lot.address)"
                        aria-label="Open location in Google Maps"
                      >
                        <i class="bi bi-geo-alt"></i> View Map
                      </button>
                    </small>
                  </p>
                </div>
                <span
                  class="badge fs-6"
                  :class="{
                    'bg-success': lot.available_spots > 5,
                    'bg-warning text-dark': lot.available_spots > 0 && lot.available_spots <= 5,
                    'bg-danger': lot.available_spots === 0
                  }"
                >
                  {{ lot.available_spots }} Spot{{ lot.available_spots === 1 ? '' : 's' }} Available
                </span>
              </div>

              <div class="mt-3">
                <!-- Booking Actions -->
                <template v-if="confirmingLotId !== lot.id">
                  <button
                    class="btn btn-primary"
                    :disabled="lot.available_spots === 0 || bookingLotId === lot.id"
                    @click="startConfirm(lot.id)"
                  >
                    Book Spot
                  </button>
                </template>
                <template v-else>
                  <button
                    class="btn btn-success me-2"
                    :disabled="bookingLotId === lot.id"
                    @click="book(lot.id)"
                  >
                    <span v-if="bookingLotId === lot.id" class="spinner-border spinner-border-sm me-2"></span>
                    Confirm
                  </button>
                  <button class="btn btn-secondary" @click="cancelConfirm">
                    Cancel
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <nav v-if="totalPages > 1" class="mt-3" aria-label="Pages">
          <ul class="pagination justify-content-center">
            <li class="page-item" :class="{disabled: currentPage === 1}">
              <button class="page-link" @click="changePage(currentPage - 1)">Previous</button>
            </li>
            <li
              v-for="page in totalPages"
              :key="page"
              class="page-item"
              :class="{active: currentPage === page}"
            >
              <button class="page-link" @click="changePage(page)">{{ page }}</button>
            </li>
            <li class="page-item" :class="{disabled: currentPage === totalPages}">
              <button class="page-link" @click="changePage(currentPage + 1)">Next</button>
            </li>
          </ul>
        </nav>

        <!-- Message -->
        <transition name="fade">
          <div v-if="msg" class="alert alert-info mt-4" role="alert">
            {{ msg }}
          </div>
        </transition>

        <!-- Summary -->
        <h3 class="mb-4 mt-5 text-primary"><i class="bi bi-graph-up"></i> Your Parking Activity Summary</h3>

        <div v-if="chartLoading" class="text-center my-3">
          <div class="spinner-border text-info" role="status"></div>
          <div>Loading summary...</div>
        </div>
        <div v-if="chartError" class="alert alert-danger" role="alert">{{ chartError }}</div>

        <div v-if="!chartLoading && !chartError" class="row">
          <div class="col-12 mb-4">
            <div class="card shadow-sm">
              <div class="card-body">
                <h5 class="card-title">Total Spent</h5>
                <p class="fs-3 text-success">₹{{ totalSpent.toFixed(2) }}</p>
              </div>
            </div>
          </div>
          <div class="col-12 col-md-6 mb-4">
            <div class="card shadow-sm">
              <div class="card-body">
                <h5 class="card-title">Bookings per Month</h5>
                <canvas id="bookingsPerMonthChart"></canvas>
              </div>
            </div>
          </div>
          <div class="col-12 col-md-6 mb-4">
            <div class="card shadow-sm">
              <div class="card-body">
                <h5 class="card-title">Bookings per Lot</h5>
                <canvas id="bookingsPerLotChart"></canvas>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script>
import axios from '../axios';
import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

export default {
  data() {
    return {
      lots: [],
      searchQuery: '',
      search: '',
      loading: true,
      error: '',
      msg: '',
      bookingLotId: null,
      confirmingLotId: null,
      currentPage: 1,
      pageSize: 5,
      chartLoading: true,
      chartError: '',
      months: [],
      bookingsPerMonth: [],
      lotsBooked: [],
      bookingsPerLot: [],
      totalSpent: 0,
      bookingsPerMonthChart: null,
      bookingsPerLotChart: null
    };
  },
  computed: {
    filteredLots() {
      if (!this.search) return this.lots;
      const term = this.search.toLowerCase();
      return this.lots.filter(l =>
        l.prime_location_name.toLowerCase().includes(term) ||
        l.address.toLowerCase().includes(term)
      );
    },
    paginatedLots() {
      const start = (this.currentPage - 1) * this.pageSize;
      return this.filteredLots.slice(start, start + this.pageSize);
    },
    totalPages() {
      return Math.ceil(this.filteredLots.length / this.pageSize);
    }
  },
  watch: {
    searchQuery: {
      immediate: true,
      handler(val) {
        clearTimeout(this._debounce);
        this._debounce = setTimeout(() => {
          this.search = val;
          this.currentPage = 1;
        }, 300);
      }
    }
  },
  async mounted() {
    await this.fetchLots();
    await this.fetchUserSummaryCharts();
  },
  methods: {
    async fetchLots() {
      this.loading = true;
      this.error = '';
      try {
        const res = await axios.get('/user/parking-lots');
        this.lots = res.data;
      } catch (err) {
        this.error = err.response?.data?.msg || 'Failed to load parking lots.';
      } finally {
        this.loading = false;
      }
    },
    startConfirm(lotId) {
      this.confirmingLotId = lotId;
    },
    cancelConfirm() {
      this.confirmingLotId = null;
    },
    async book(lot_id) {
      this.bookingLotId = lot_id;
      this.msg = '';
      this.confirmingLotId = null;
      try {
        const res = await axios.post('/user/book', { lot_id });
        const lot = this.lots.find(l => l.id === lot_id);
        this.msg = `✅ Booked spot #${res.data.spot_id} in ${lot.prime_location_name}`;
        await this.fetchLots();
        await this.fetchUserSummaryCharts();
      } catch (err) {
        this.msg = err.response?.data?.msg || 'Booking failed. Please try again.';
      } finally {
        this.bookingLotId = null;
      }
    },
    changePage(page) {
      if (page >= 1 && page <= this.totalPages) {
        this.currentPage = page;
      }
    },
    openInMaps(address) {
      const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
      window.open(url, '_blank', 'noopener');
    },
    logout() {
      localStorage.removeItem('token');
      this.$router.push('/');
    },
    async fetchUserSummaryCharts() {
      this.chartLoading = true;
      this.chartError = '';
      try {
        const res = await axios.get('/user/summary-charts');
        this.months = res.data.months;
        this.bookingsPerMonth = res.data.bookings_per_month;
        this.lotsBooked = res.data.lots;
        this.bookingsPerLot = res.data.bookings_per_lot;
        this.totalSpent = res.data.total_spent;
      } catch (err) {
        this.chartError = err.response?.data?.msg || 'Failed to load summary charts.';
      } finally {
        this.chartLoading = false;
        if (!this.chartError) {
          this.$nextTick(() => {
            this.renderBookingsPerMonthChart();
            this.renderBookingsPerLotChart();
          });
        }
      }
    },
    renderBookingsPerMonthChart() {
      const ctx = document.getElementById('bookingsPerMonthChart');
      if (!ctx) return;
      if (this.bookingsPerMonthChart) this.bookingsPerMonthChart.destroy();
      this.bookingsPerMonthChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: this.months,
          datasets: [{
            label: 'Bookings',
            data: this.bookingsPerMonth,
            backgroundColor: 'rgba(54, 162, 235, 0.6)'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    },
    renderBookingsPerLotChart() {
      const ctx = document.getElementById('bookingsPerLotChart');
      if (!ctx) return;
      if (this.bookingsPerLotChart) this.bookingsPerLotChart.destroy();
      this.bookingsPerLotChart = new Chart(ctx, {
        type: 'pie',
        data: {
          labels: this.lotsBooked,
          datasets: [{
            data: this.bookingsPerLot,
            backgroundColor: [
              'rgba(255, 99, 132, 0.6)',
              'rgba(54, 162, 235, 0.6)',
              'rgba(255, 206, 86, 0.6)',
              'rgba(75, 192, 192, 0.6)'
            ]
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }
  }
};
</script>

<style scoped>
.hover-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  transition: 0.2s;
}
.parking-lots-list-container {
  max-height: 500px;
  overflow-y: auto;
  padding-right: 10px;
}
#bookingsPerMonthChart,
#bookingsPerLotChart {
  height: 300px !important;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter, .fade-leave-to {
  opacity: 0;
}
</style>
