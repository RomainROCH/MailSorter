/**
 * Error Handler Module for MailSorter Extension
 * Provides user notifications and error logging.
 */

const ErrorHandler = {
    // Error severity levels
    SEVERITY: {
        INFO: 'info',
        WARNING: 'warning',
        ERROR: 'error',
        CRITICAL: 'critical'
    },

    // Recent errors for debugging
    _errorLog: [],
    _maxLogSize: 50,

    /**
     * Log and optionally notify user of an error
     * @param {string} message - Error message
     * @param {string} severity - Error severity level
     * @param {Error|null} originalError - Original error object if available
     * @param {boolean} notify - Whether to show user notification
     */
    handle(message, severity = 'error', originalError = null, notify = false) {
        const entry = {
            timestamp: new Date().toISOString(),
            message,
            severity,
            stack: originalError?.stack || null
        };

        // Console logging with appropriate level
        switch (severity) {
            case this.SEVERITY.INFO:
                console.info(`[MailSorter] ${message}`);
                break;
            case this.SEVERITY.WARNING:
                console.warn(`[MailSorter] ${message}`);
                break;
            case this.SEVERITY.CRITICAL:
                console.error(`[MailSorter CRITICAL] ${message}`, originalError);
                break;
            default:
                console.error(`[MailSorter] ${message}`, originalError);
        }

        // Add to internal log
        this._errorLog.push(entry);
        if (this._errorLog.length > this._maxLogSize) {
            this._errorLog.shift();
        }

        // User notification for important errors
        if (notify && this._shouldNotify(severity)) {
            this._notifyUser(message, severity);
        }

        return entry;
    },

    /**
     * Determine if user should be notified based on severity
     */
    _shouldNotify(severity) {
        return severity === this.SEVERITY.ERROR || severity === this.SEVERITY.CRITICAL;
    },

    /**
     * Show notification to user
     */
    async _notifyUser(message, severity) {
        try {
            // Use browser notifications API if available
            if (browser.notifications && browser.notifications.create) {
                const iconPath = severity === this.SEVERITY.CRITICAL 
                    ? 'icons/icon-error.png' 
                    : 'icons/icon-48.png';
                
                await browser.notifications.create({
                    type: 'basic',
                    title: 'MailSorter',
                    message: message.substring(0, 200), // Truncate for notification
                    iconUrl: iconPath
                });
            }
        } catch (e) {
            // Fallback: just log, don't recurse
            console.warn('Could not show notification:', e);
        }
    },

    /**
     * Handle backend connection errors
     */
    handleBackendError(error, context = '') {
        const message = context 
            ? `Backend error (${context}): ${error.message || error}`
            : `Backend error: ${error.message || error}`;
        
        return this.handle(message, this.SEVERITY.ERROR, error, true);
    },

    /**
     * Handle classification errors
     */
    handleClassificationError(messageId, error) {
        const message = `Failed to classify message ${messageId}: ${error.message || error}`;
        return this.handle(message, this.SEVERITY.WARNING, error, false);
    },

    /**
     * Handle move operation errors
     */
    handleMoveError(messageId, targetFolder, error) {
        const message = `Failed to move message ${messageId} to ${targetFolder}: ${error.message || error}`;
        return this.handle(message, this.SEVERITY.ERROR, error, true);
    },

    /**
     * Handle native messaging disconnection
     */
    handleDisconnection(error) {
        const message = error 
            ? `Native backend disconnected: ${error.message || error}`
            : 'Native backend disconnected unexpectedly';
        
        return this.handle(message, this.SEVERITY.CRITICAL, error, true);
    },

    /**
     * Get recent error log
     * @returns {Array}
     */
    getErrorLog() {
        return [...this._errorLog];
    },

    /**
     * Clear error log
     */
    clearLog() {
        this._errorLog = [];
    },

    /**
     * Wrap async function with error handling
     * @param {Function} fn - Async function to wrap
     * @param {string} context - Context description for errors
     * @returns {Function}
     */
    wrap(fn, context = '') {
        return async (...args) => {
            try {
                return await fn(...args);
            } catch (error) {
                this.handle(
                    `${context}: ${error.message || error}`,
                    this.SEVERITY.ERROR,
                    error,
                    false
                );
                throw error; // Re-throw for caller handling
            }
        };
    }
};

// Export for use in background.js
window.ErrorHandler = ErrorHandler;
