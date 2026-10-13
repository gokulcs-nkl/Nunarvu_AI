// Authentication module for CMS Frontend
class Auth {
    constructor() {
        this.token = localStorage.getItem('authToken');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
        this.baseURL = window.API_BASE_URL || 'http://localhost:8000/api';
    }

    // Show login modal
    showLogin() {
        document.getElementById('loginModal').style.display = 'block';
    }

    // Close login modal
    closeLogin() {
        document.getElementById('loginModal').style.display = 'none';
        this.clearError();
    }

    // Clear error messages
    clearError() {
        const errorElement = document.getElementById('loginError');
        errorElement.style.display = 'none';
        errorElement.textContent = '';
    }

    // Show error message
    showError(message) {
        const errorElement = document.getElementById('loginError');
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }

    // Show loading state
    showLoading(show = true) {
        const btn = document.querySelector('#loginForm button[type="submit"]');
        if (show) {
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div>Logging in...';
        } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Login';
        }
    }

    // Login function
    async login(username, password) {
        try {
            this.showLoading(true);
            this.clearError();

            const response = await fetch(`${this.baseURL}/auth/login/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.token = data.token || data.access;
                this.user = data.user;
                
                // Store in localStorage
                localStorage.setItem('authToken', this.token);
                localStorage.setItem('user', JSON.stringify(this.user));
                
                // Close modal and redirect
                this.closeLogin();
                this.redirectToDashboard();
            } else {
                this.showError(data.error || data.message || 'Login failed. Please check your credentials.');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Connection error. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    // Logout function
    async logout() {
        try {
            if (this.token) {
                await fetch(`${this.baseURL}/auth/logout/`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.token}`,
                        'Content-Type': 'application/json',
                    }
                });
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Clear local storage regardless of API call result
            localStorage.removeItem('authToken');
            localStorage.removeItem('user');
            this.token = null;
            this.user = null;
            window.location.href = '/';
        }
    }

    // Check if user is authenticated
    isAuthenticated() {
        return !!this.token;
    }

    // Get authorization header
    getAuthHeader() {
        return this.token ? { 'Authorization': `Bearer ${this.token}` } : {};
    }

    // Redirect to dashboard
    redirectToDashboard() {
        window.location.href = './pages/dashboard.html';
    }

    // Check authentication status on page load
    checkAuth() {
        if (this.isAuthenticated()) {
            this.validateToken();
        }
    }

    // Validate token with backend
    async validateToken() {
        try {
            const response = await fetch(`${this.baseURL}/auth/user/`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (!response.ok) {
                // Token is invalid, logout
                this.logout();
            }
        } catch (error) {
            console.error('Token validation error:', error);
            // On network error, keep the token but user will need to retry
        }
    }

    // API helper with authentication
    async apiCall(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const defaultHeaders = {
            'Content-Type': 'application/json',
            ...this.getAuthHeader()
        };

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Unauthorized, logout
                this.logout();
                return null;
            }

            return response;
        } catch (error) {
            console.error('API call error:', error);
            throw error;
        }
    }
}

// Create global auth instance
window.auth = new Auth();

// Global functions for HTML onclick handlers
function showLogin() {
    window.auth.showLogin();
}

function closeLogin() {
    window.auth.closeLogin();
}

function logout() {
    window.auth.logout();
}

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', function() {
    // Setup login form handler
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            await window.auth.login(username, password);
        });
    }

    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        const modal = document.getElementById('loginModal');
        if (e.target === modal) {
            window.auth.closeLogin();
        }
    });

    // Check auth status
    window.auth.checkAuth();
});