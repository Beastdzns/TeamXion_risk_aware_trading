/**
 * API Configuration
 * This file manages the backend API URL based on the environment
 */

const API_CONFIG = {
    // Automatically detect environment and set appropriate base URL
    BASE_URL: (() => {
        const hostname = window.location.hostname;

        // Local development
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return ''; // Use relative URLs for local development
        }

        // Production - Replace with your Railway backend URL
        // After deploying to Railway, update this URL
        // Example: 'https://your-app-name.up.railway.app'
        return 'teamxionriskawaretrading-production.up.railway.app';
    })(),

    // WebSocket/SSE endpoints (if different from REST API)
    WS_BASE_URL: (() => {
        const hostname = window.location.hostname;

        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return '';
        }

        // For Railway, WebSocket uses the same URL
        return 'teamxionriskawaretrading-production.up.railway.app';
    })(),

    // Helper method to build full API URL
    getApiUrl: function (endpoint) {
        // Ensure endpoint starts with /
        const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        return `${this.BASE_URL}${path}`;
    },

    // Helper method for WebSocket/SSE URLs
    getWsUrl: function (endpoint) {
        const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        return `${this.WS_BASE_URL}${path}`;
    },

    // Check if running in production
    isProduction: function () {
        const hostname = window.location.hostname;
        return hostname !== 'localhost' && hostname !== '127.0.0.1';
    }
};

// Log current configuration (helpful for debugging)
console.log('[Config] API Base URL:', API_CONFIG.BASE_URL || 'relative URLs (local)');
console.log('[Config] Environment:', API_CONFIG.isProduction() ? 'Production' : 'Development');
