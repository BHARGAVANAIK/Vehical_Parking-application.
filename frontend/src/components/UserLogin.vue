<template>
  <div class="container mt-5 d-flex justify-content-center align-items-center" style="min-height:80vh;">
    <div class="card shadow-lg p-4 animated fadeIn" style="max-width:400px; width:100%;">
      <h2 class="text-center mb-4 text-primary fw-bold">🔐 Login</h2>

      <form @submit.prevent="login" novalidate>
        <!-- Username -->
        <div class="mb-3">
          <label class="form-label fw-semibold" for="username">Username</label>
          <input
            id="username"
            v-model.trim="username"
            class="form-control form-control-lg"
            placeholder="Enter username"
            :class="{'is-invalid': usernameTouched && !usernameValid}"
            required
            :disabled="loading"
            @blur="usernameTouched = true"
          />
          <div class="invalid-feedback" v-if="usernameTouched && !usernameValid">
            Username must be at least 3 characters
          </div>
        </div>

        <!-- Password -->
        <div class="mb-3 position-relative">
          <label class="form-label fw-semibold" for="password">Password</label>
          <input
            id="password"
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            class="form-control form-control-lg pe-5"
            placeholder="Enter password"
            :class="{'is-invalid': passwordTouched && !passwordValid}"
            required
            :disabled="loading"
            @blur="passwordTouched = true"
            @keyup.enter="login"
          />
          <i
            class="bi"
            :class="showPassword ? 'bi-eye-slash' : 'bi-eye'"
            @click="togglePassword"
            style="position:absolute; right:10px; top:38px; cursor:pointer; font-size:1.2rem;"
          ></i>
          <div class="invalid-feedback" v-if="passwordTouched && !passwordValid">
            Password must be at least 6 characters
          </div>
        </div>

        <!-- Remember Me -->
        <div class="form-check mb-3">
          <input
            class="form-check-input"
            type="checkbox"
            id="rememberMe"
            v-model="rememberMe"
            :disabled="loading"
          />
          <label class="form-check-label" for="rememberMe">
            Remember Me
          </label>
        </div>

        <!-- Error Message -->
        <transition name="fade">
          <div v-if="error" class="alert alert-danger py-2 my-2">
            <small>{{ error }}</small>
          </div>
        </transition>

        <!-- Buttons -->
        <div class="d-grid gap-2 mt-4">
          <button
            class="btn btn-primary btn-lg"
            type="submit"
            :disabled="loading || !formValid"
          >
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            Login
          </button>
          <button
            type="button"
            class="btn btn-outline-secondary btn-lg"
            @click="$router.push('/register')"
            :disabled="loading"
          >
            📝 New User? Register
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import axios from '../axios';

export default {
  data() {
    return {
      username: '',
      password: '',
      rememberMe: false,
      error: '',
      showPassword: false,
      loading: false,
      usernameTouched: false,
      passwordTouched: false
    };
  },
  computed: {
    usernameValid() {
      return this.username.trim().length >= 3;
    },
    passwordValid() {
      return this.password.length >= 6;
    },
    formValid() {
      return this.usernameValid && this.passwordValid;
    }
  },
  methods: {
    togglePassword() {
      this.showPassword = !this.showPassword;
    },
    async login() {
      this.usernameTouched = true;
      this.passwordTouched = true;
      this.error = '';

      if (!this.formValid) {
        return;
      }

      this.loading = true;
      try {
        const res = await axios.post('/login', {
          username: this.username,
          password: this.password
        });

        localStorage.setItem('token', res.data.access_token);
        if (this.rememberMe) {
          localStorage.setItem('rememberMe', 'true');
        } else {
          localStorage.removeItem('rememberMe');
        }

        // Decode JWT
        const base64Url = res.data.access_token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
          atob(base64)
            .split('')
            .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join('')
        );
        const payload = JSON.parse(jsonPayload);

        if (payload.role === 'admin') {
          this.$router.push('/admin');
        } else {
          this.$router.push('/dashboard');
        }
      } catch (err) {
        this.error = err.response?.data?.msg || 'Login failed. Please try again.';
      } finally {
        this.loading = false;
      }
    }
  },
  mounted() {
    // Auto-check rememberMe based on stored preference
    this.rememberMe = localStorage.getItem('rememberMe') === 'true';
  }
};
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter,
.fade-leave-to {
  opacity: 0;
}
/* Optionally highlight invalid input with red outline */
.is-invalid {
  border-color: #dc3545;
  padding-right: calc(1.5em + 0.75rem);
  background-position: right calc(0.375em + 0.1875rem) center;
  background-repeat: no-repeat;
  background-size: calc(0.75em + 0.375rem) calc(0.75em + 0.375rem);
}
</style>
