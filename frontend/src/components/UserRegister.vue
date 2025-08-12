<template>
  <div class="container mt-5 d-flex justify-content-center align-items-center" style="min-height:80vh;">
    <div class="card shadow-lg p-4 animated fadeIn" style="max-width:450px; width:100%;">
      <h2 class="text-center mb-4 text-success fw-bold">📝 Register</h2>

      <form @submit.prevent="register" novalidate>
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
            @blur="usernameTouched = true"
            :disabled="loading"
          />
          <div class="invalid-feedback" v-if="usernameTouched && !usernameValid">
            Username must be at least 3 characters
          </div>
        </div>

        <!-- Email -->
        <div class="mb-3">
          <label class="form-label fw-semibold" for="email">Email</label>
          <input
            id="email"
            v-model.trim="email"
            type="email"
            class="form-control form-control-lg"
            placeholder="Enter email"
            :class="{'is-invalid': emailTouched && !emailValid}"
            required
            @blur="emailTouched = true"
            :disabled="loading"
          />
          <div class="invalid-feedback" v-if="emailTouched && !emailValid">
            Please enter a valid email address
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
            @blur="passwordTouched = true"
            :disabled="loading"
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

        <!-- Success/Error Message -->
        <transition name="fade">
          <div v-if="msg" :class="{'alert alert-success': success, 'alert alert-danger': !success}" class="py-2 my-2">
            <small>{{ msg }}</small>
          </div>
        </transition>

        <!-- Action Buttons -->
        <div class="d-grid gap-2 mt-4">
          <button
            class="btn btn-success btn-lg"
            type="submit"
            :disabled="loading || !formValid"
          >
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            Register
          </button>
          <button
            type="button"
            class="btn btn-outline-primary btn-lg"
            @click="$router.push('/')"
            :disabled="loading"
          >
            ⬅ Back to Login
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
      email: '',
      password: '',
      msg: '',
      success: false,
      loading: false,
      showPassword: false,
      usernameTouched: false,
      emailTouched: false,
      passwordTouched: false
    };
  },
  computed: {
    usernameValid() {
      return this.username.trim().length >= 3;
    },
    emailValid() {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.email);
    },
    passwordValid() {
      return this.password.length >= 6;
    },
    formValid() {
      return this.usernameValid && this.emailValid && this.passwordValid;
    }
  },
  methods: {
    togglePassword() {
      this.showPassword = !this.showPassword;
    },
    async register() {
      // mark all touched for validation check
      this.usernameTouched = true;
      this.emailTouched = true;
      this.passwordTouched = true;
      this.msg = '';

      if (!this.formValid) {
        return;
      }

      this.loading = true;
      try {
        await axios.post('/register', {
          username: this.username,
          email: this.email,
          password: this.password
        });
        this.success = true;
        this.msg = '🎉 Registration successful! Please login.';
        this.username = '';
        this.email = '';
        this.password = '';
        this.usernameTouched = false;
        this.emailTouched = false;
        this.passwordTouched = false;
      } catch (err) {
        this.success = false;
        this.msg = err.response?.data?.msg || '❌ Registration failed. Try again.';
      } finally {
        this.loading = false;
      }
    }
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
/* Invalid input styling */
.is-invalid {
  border-color: #dc3545;
}
</style>
