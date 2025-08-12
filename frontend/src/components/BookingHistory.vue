<template>
  <div class="container mt-4">

    <!-- Back to Dashboard -->
    <div class="mb-3">
      <router-link
        to="/dashboard"
        class="btn btn-outline-primary"
        aria-label="Back to Dashboard"
      >
        <i class="bi bi-arrow-left"></i> Back to Dashboard
      </router-link>
    </div>

    <!-- Page Title -->
    <h3 class="mb-4 text-primary fw-bold">
      <i class="bi bi-clock-history"></i> My Booking History
    </h3>

    <!-- Loading -->
    <div v-if="loading" class="text-center my-5">
      <div class="spinner-border text-primary" role="status"></div>
      <div>Loading bookings...</div>
    </div>

    <!-- Error -->
    <transition name="fade">
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
    </transition>

    <!-- Table -->
    <div v-if="bookings.length" class="table-responsive">
      <table class="table table-hover align-middle shadow-sm rounded overflow-hidden">
        <thead class="table-light">
          <tr>
            <th>Lot</th>
            <th>Address</th>
            <th>Spot #</th>
            <th>Start</th>
            <th>End</th>
            <th>Status / Actions</th>
            <th>Parked Duration</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in bookings" :key="b.id">
            <td class="fw-semibold">{{ b.prime_location_name }}</td>
            <td>{{ b.address }}</td>
            <td><span class="badge bg-info text-dark">{{ b.spot_id }}</span></td>
            <td>{{ formatDate(b.start_time) }}</td>
            <td>{{ formatDate(b.end_time) }}</td>
            <td>
              <span :class="statusClass(b.status)" class="px-2 py-1 rounded">{{ statusLabel(b.status) }}</span>

              <!-- Booking Actions -->
              <div class="mt-2" v-if="b.status === 'active' || b.status === 'occupied'">
                <button
                  v-if="b.status === 'active'"
                  class="btn btn-sm btn-outline-success me-1"
                  @click="occupySpot(b.id)"
                  :disabled="actionLoading && currentActionId === b.id"
                  aria-label="Mark booking as occupied"
                >
                  <span v-if="isProcessing(b.id, 'occupy')" class="spinner-border spinner-border-sm me-1"></span>
                  Mark as Occupied
                </button>

                <button
                  v-if="b.status === 'occupied'"
                  class="btn btn-sm btn-outline-primary"
                  @click="releaseSpot(b.id)"
                  :disabled="actionLoading && currentActionId === b.id"
                  aria-label="Mark booking as released"
                >
                  <span v-if="isProcessing(b.id, 'release')" class="spinner-border spinner-border-sm me-1"></span>
                  Mark as Released
                </button>
              </div>
            </td>
            <td>{{ formatDuration(b.start_time, b.end_time) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading" class="alert alert-info shadow-sm">
      No bookings found.
    </div>
  </div>
</template>

<script>
import axios from '../axios';

export default {
  data() {
    return {
      bookings: [],
      loading: true,
      error: '',
      actionLoading: false,
      currentActionId: null,
      currentAction: null
    };
  },
  async mounted() {
    await this.refreshBookings();
  },
  methods: {
    formatDate(dt) {
      if (!dt) return '-';
      return new Date(dt).toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short'
      });
    },
    formatDuration(start, end) {
      if (!start) return '-';
      const startDate = new Date(start);
      const endDate = end ? new Date(end) : new Date();
      let diffMs = endDate - startDate;
      if (diffMs < 0) return '-';

      const hrs = Math.floor(diffMs / 3600000);
      const mins = Math.floor((diffMs % 3600000) / 60000);
      const secs = Math.floor((diffMs % 60000) / 1000);

      return `${hrs > 0 ? hrs + 'h ' : ''}${mins > 0 ? mins + 'm ' : ''}${hrs === 0 && mins === 0 ? secs + 's' : ''}`.trim();
    },
    statusClass(status) {
      return {
        'badge bg-success': status === 'occupied',
        'badge bg-secondary': status === 'completed',
        'badge bg-danger': status === 'cancelled',
        'badge bg-warning text-dark': status === 'active'
      };
    },
    statusLabel(status) {
      const labels = {
        occupied: 'Occupied',
        completed: 'Completed',
        cancelled: 'Cancelled',
        active: 'Active'
      };
      return labels[status] || status;
    },
    isProcessing(id, action) {
      return this.actionLoading && this.currentActionId === id && this.currentAction === action;
    },
    async occupySpot(reservation_id) {
      this.setActionState(reservation_id, 'occupy');
      try {
        await axios.post('/user/occupy-spot', { reservation_id });
        await this.refreshBookings();
      } catch (err) {
        alert(err.response?.data?.msg || 'Failed to mark as occupied.');
      } finally {
        this.resetActionState();
      }
    },
    async releaseSpot(reservation_id) {
      this.setActionState(reservation_id, 'release');
      try {
        await axios.post('/user/release-spot', { reservation_id });
        await this.refreshBookings();
      } catch (err) {
        alert(err.response?.data?.msg || 'Failed to mark as released.');
      } finally {
        this.resetActionState();
      }
    },
    setActionState(id, action) {
      this.actionLoading = true;
      this.currentActionId = id;
      this.currentAction = action;
    },
    resetActionState() {
      this.actionLoading = false;
      this.currentActionId = null;
      this.currentAction = null;
    },
    async refreshBookings() {
      this.loading = true;
      this.error = '';
      try {
        const res = await axios.get('/user/bookings');
        this.bookings = res.data;
      } catch (err) {
        this.error = err.response?.data?.msg || 'Failed to load bookings.';
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
.table-hover tbody tr:hover {
  background-color: rgba(0, 123, 255, 0.05);
}
.fade-enter-active, .fade-leave-active {
  transition: opacity .3s;
}
.fade-enter, .fade-leave-to {
  opacity: 0;
}
</style>
