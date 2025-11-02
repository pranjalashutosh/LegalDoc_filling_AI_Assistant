/**
 * API Client Utilities
 * Provides helper functions for making API requests with error handling
 */

class APIClient {
    constructor() {
        this.baseURL = '';
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }

    /**
     * Make a GET request
     * @param {string} endpoint - API endpoint path
     * @param {Object} options - Additional fetch options
     * @returns {Promise<Object>} Response data
     */
    async get(endpoint, options = {}) {
        return this._request(endpoint, {
            method: 'GET',
            ...options
        });
    }

    /**
     * Make a POST request
     * @param {string} endpoint - API endpoint path
     * @param {Object} data - Request body data
     * @param {Object} options - Additional fetch options
     * @returns {Promise<Object>} Response data
     */
    async post(endpoint, data = null, options = {}) {
        const requestOptions = {
            method: 'POST',
            ...options
        };

        // Only add headers and body if data is not FormData
        if (!(data instanceof FormData)) {
            requestOptions.headers = {
                ...this.defaultHeaders,
                ...options.headers
            };
            if (data) {
                requestOptions.body = JSON.stringify(data);
            }
        } else {
            // For FormData, let browser set Content-Type with boundary
            requestOptions.body = data;
        }

        return this._request(endpoint, requestOptions);
    }

    /**
     * Make a DELETE request
     * @param {string} endpoint - API endpoint path
     * @param {Object} options - Additional fetch options
     * @returns {Promise<Object>} Response data
     */
    async delete(endpoint, options = {}) {
        return this._request(endpoint, {
            method: 'DELETE',
            ...options
        });
    }

    /**
     * Internal request handler
     * @param {string} endpoint - API endpoint path
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} Response data
     * @throws {APIError} On request failure
     */
    async _request(endpoint, options) {
        const url = `${this.baseURL}${endpoint}`;

        try {
            const response = await fetch(url, options);
            const data = await response.json();

            if (!response.ok) {
                throw new APIError(
                    data.error || 'Request failed',
                    response.status,
                    data
                );
            }

            return data;
        } catch (error) {
            if (error instanceof APIError) {
                throw error;
            }

            // Network error or parsing error
            throw new APIError(
                'Network error. Please check your connection and try again.',
                0,
                { originalError: error.message }
            );
        }
    }
}

/**
 * Custom API Error class
 */
class APIError extends Error {
    constructor(message, statusCode, details = {}) {
        super(message);
        this.name = 'APIError';
        this.statusCode = statusCode;
        this.details = details;
    }

    /**
     * Get user-friendly error message
     * @returns {string} Formatted error message
     */
    getUserMessage() {
        // Handle specific status codes
        if (this.statusCode === 413) {
            return 'File is too large. Maximum size is 5 MB.';
        }
        if (this.statusCode === 415) {
            return 'Invalid file type. Please upload a .docx file.';
        }
        if (this.statusCode === 400) {
            return this.message || 'Invalid request. Please check your input.';
        }
        if (this.statusCode === 404) {
            return 'Resource not found. Your session may have expired.';
        }
        if (this.statusCode === 500) {
            return 'Server error. Please try again later.';
        }
        if (this.statusCode === 0) {
            return this.message; // Network error message
        }

        return this.message || 'An unexpected error occurred.';
    }
}

/**
 * Session Management
 */
class SessionManager {
    constructor() {
        this.sessionKey = 'legal_doc_filler_session';
    }

    /**
     * Store session data in sessionStorage
     * @param {Object} data - Session data to store
     */
    setSessionData(key, value) {
        try {
            const sessionData = this.getSessionData() || {};
            sessionData[key] = value;
            sessionStorage.setItem(this.sessionKey, JSON.stringify(sessionData));
        } catch (error) {
            console.error('Failed to store session data:', error);
        }
    }

    /**
     * Get session data from sessionStorage
     * @param {string} key - Optional key to get specific value
     * @returns {Object|*} Session data or specific value
     */
    getSessionData(key = null) {
        try {
            const data = sessionStorage.getItem(this.sessionKey);
            if (!data) return null;

            const sessionData = JSON.parse(data);
            return key ? sessionData[key] : sessionData;
        } catch (error) {
            console.error('Failed to retrieve session data:', error);
            return null;
        }
    }

    /**
     * Clear session data
     */
    clearSession() {
        try {
            sessionStorage.removeItem(this.sessionKey);
        } catch (error) {
            console.error('Failed to clear session:', error);
        }
    }

    /**
     * Check if session exists and is valid
     * @returns {boolean} True if session exists
     */
    hasValidSession() {
        const data = this.getSessionData();
        return data !== null && Object.keys(data).length > 0;
    }
}

/**
 * Loading State Manager
 */
class LoadingManager {
    constructor() {
        this.loadingElements = new Set();
    }

    /**
     * Show loading state for an element
     * @param {HTMLElement|string} element - Element or selector
     * @param {Object} options - Loading options
     */
    show(element, options = {}) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (!el) return;

        const {
            disableInteraction = true,
            text = null,
            spinner = false
        } = options;

        // Store original state
        if (!this.loadingElements.has(el)) {
            el.dataset.originalDisabled = el.disabled;
            el.dataset.originalText = el.textContent;
        }

        // Apply loading state
        if (disableInteraction) {
            el.disabled = true;
        }

        if (text) {
            el.textContent = text;
        }

        if (spinner) {
            el.classList.add('loading');
        }

        this.loadingElements.add(el);
    }

    /**
     * Hide loading state for an element
     * @param {HTMLElement|string} element - Element or selector
     */
    hide(element) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (!el || !this.loadingElements.has(el)) return;

        // Restore original state
        el.disabled = el.dataset.originalDisabled === 'true';
        if (el.dataset.originalText) {
            el.textContent = el.dataset.originalText;
        }
        el.classList.remove('loading');

        // Clean up
        delete el.dataset.originalDisabled;
        delete el.dataset.originalText;
        this.loadingElements.delete(el);
    }

    /**
     * Hide all loading states
     */
    hideAll() {
        this.loadingElements.forEach(el => this.hide(el));
    }
}

/**
 * Utility Functions
 */
const Utils = {
    /**
     * Format file size to human-readable string
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Validate file extension
     * @param {string} filename - File name
     * @param {Array<string>} allowedExtensions - Allowed extensions
     * @returns {boolean} True if valid
     */
    validateFileExtension(filename, allowedExtensions = ['.docx']) {
        const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
        return allowedExtensions.includes(extension);
    },

    /**
     * Validate file size
     * @param {number} size - File size in bytes
     * @param {number} maxSize - Maximum size in MB
     * @returns {boolean} True if valid
     */
    validateFileSize(size, maxSize = 5) {
        const maxBytes = maxSize * 1024 * 1024;
        return size <= maxBytes;
    },

    /**
     * Show element by removing 'hidden' class
     * @param {HTMLElement|string} element - Element or selector
     */
    show(element) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (el) el.classList.remove('hidden');
    },

    /**
     * Hide element by adding 'hidden' class
     * @param {HTMLElement|string} element - Element or selector
     */
    hide(element) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (el) el.classList.add('hidden');
    },

    /**
     * Toggle element visibility
     * @param {HTMLElement|string} element - Element or selector
     */
    toggle(element) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (el) el.classList.toggle('hidden');
    },

    /**
     * Debounce function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in ms
     * @returns {Function} Debounced function
     */
    debounce(func, wait = 300) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Export instances
const api = new APIClient();
const session = new SessionManager();
const loading = new LoadingManager();

// Make available globally
window.api = api;
window.session = session;
window.loading = loading;
window.Utils = Utils;
window.APIError = APIError;

