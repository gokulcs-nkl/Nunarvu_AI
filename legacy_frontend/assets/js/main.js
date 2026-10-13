// Main JavaScript functionality for CMS Frontend

// Global functions for demo and other interactions
function showDemo() {
    alert('Demo functionality - This would show a video demonstration of the face recognition system.');
}

// Initialize page functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('CMS Frontend initialized');
    
    // Update API base URL based on environment
    if (window.location.hostname === 'localhost') {
        window.API_BASE_URL = 'http://localhost:8000/api';
    } else {
        // In production/Docker environment
        window.API_BASE_URL = '/api';
    }
    
    console.log('API Base URL:', window.API_BASE_URL);
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Add loading states to buttons
    const buttons = document.querySelectorAll('.cta-btn, .login-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            if (!this.classList.contains('loading')) {
                const originalText = this.innerHTML;
                this.classList.add('loading');
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.classList.remove('loading');
                }, 2000);
            }
        });
    });
    
    // Intersection Observer for animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe elements for scroll animations
    document.querySelectorAll('.feature-card, .benefit').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// Utility functions
const API = {
    // Generic API call handler
    async call(endpoint, options = {}) {
        const url = `${window.API_BASE_URL}${endpoint}`;
        const defaultHeaders = {
            'Content-Type': 'application/json'
        };
        
        if (window.auth && window.auth.token) {
            defaultHeaders['Authorization'] = `Bearer ${window.auth.token}`;
        }
        
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
                console.log('Unauthorized - redirecting to login');
                if (window.auth) {
                    window.auth.logout();
                }
                return null;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    },
    
    // Health check
    async healthCheck() {
        try {
            const result = await this.call('/health/');
            console.log('Backend health check:', result);
            return result;
        } catch (error) {
            console.error('Backend health check failed:', error);
            return null;
        }
    }
};

// Initialize API health check
setTimeout(() => {
    API.healthCheck();
}, 1000);