/**
 * MailSorter Undo Manager
 * Handles undo functionality for email moves (UX-005)
 * State machine: IDLE -> UNDO_READY -> (EXPIRED | UNDOING | NEW_SORT) -> IDLE
 */

const UndoManager = {
    // State constants
    STATE: {
        IDLE: 'idle',
        UNDO_READY: 'undo_ready',
        UNDOING: 'undoing',
        EXPIRED: 'expired'
    },
    
    // Current state
    _state: 'idle',
    
    // Current undo action
    _action: null,
    
    // Expiry timer
    _expiryTimer: null,
    
    // Subscribers for state changes
    _subscribers: new Set(),
    
    // Undo window duration (from constants)
    get WINDOW_MS() {
        return window.MS_CONSTANTS?.UNDO?.WINDOW_MS || 10000;
    },
    
    /**
     * Record an action that can be undone
     * @param {object} action - { messageId, fromFolder, toFolder, subject }
     */
    recordAction(action) {
        // Cancel any existing undo window
        this._cancelTimer();
        
        // Store the new action
        this._action = {
            ...action,
            timestamp: Date.now(),
            expiresAt: Date.now() + this.WINDOW_MS
        };
        
        // Transition to UNDO_READY state
        this._setState(this.STATE.UNDO_READY);
        
        // Set expiry timer
        this._expiryTimer = setTimeout(() => {
            this._handleExpiry();
        }, this.WINDOW_MS);
        
        // Notify subscribers
        this._notify('recorded', this._action);
        
        console.log('[UndoManager] Recorded action:', this._action);
        
        // Update StateStore if available
        this._syncToStateStore();
    },
    
    /**
     * Check if undo is available
     * @returns {boolean}
     */
    canUndo() {
        return this._state === this.STATE.UNDO_READY && this._action !== null;
    },
    
    /**
     * Get time remaining in undo window
     * @returns {number} - Milliseconds remaining, or 0 if expired
     */
    getTimeRemaining() {
        if (!this._action || !this._action.expiresAt) {
            return 0;
        }
        
        const remaining = this._action.expiresAt - Date.now();
        return Math.max(0, remaining);
    },
    
    /**
     * Get the current undo action
     * @returns {object|null}
     */
    getAction() {
        if (this.canUndo()) {
            return { ...this._action };
        }
        return null;
    },
    
    /**
     * Perform the undo operation
     * @returns {Promise<boolean>} - True if undo succeeded
     */
    async undo() {
        if (!this.canUndo()) {
            console.warn('[UndoManager] Cannot undo - not in UNDO_READY state');
            return false;
        }
        
        const action = this._action;
        
        // Transition to UNDOING state
        this._setState(this.STATE.UNDOING);
        this._cancelTimer();
        
        try {
            // Get the message and original folder
            const message = await browser.messages.get(action.messageId);
            if (!message) {
                throw new Error('Message not found');
            }
            
            // Find the original folder
            const account = await browser.accounts.get(message.folder.accountId);
            const folders = await this._getAllFolders(account);
            const originalFolder = folders.find(f => f.path === action.fromFolder || f.name === action.fromFolder);
            
            if (!originalFolder) {
                throw new Error('Original folder not found: ' + action.fromFolder);
            }
            
            // Move the message back
            await browser.messages.move([action.messageId], originalFolder);
            
            // Success - clear action and return to IDLE
            this._action = null;
            this._setState(this.STATE.IDLE);
            this._notify('undone', action);
            this._syncToStateStore();
            
            console.log('[UndoManager] Undo successful:', action);
            return true;
            
        } catch (e) {
            console.error('[UndoManager] Undo failed:', e);
            
            // Return to IDLE on failure
            this._action = null;
            this._setState(this.STATE.IDLE);
            this._notify('error', e);
            this._syncToStateStore();
            
            // Notify error handler if available
            if (window.ErrorHandler) {
                window.ErrorHandler.handle(
                    'Failed to undo move: ' + e.message,
                    window.ErrorHandler.SEVERITY.ERROR,
                    e,
                    true
                );
            }
            
            return false;
        }
    },
    
    /**
     * Cancel the current undo window without performing undo
     */
    cancel() {
        this._cancelTimer();
        this._action = null;
        this._setState(this.STATE.IDLE);
        this._syncToStateStore();
    },
    
    /**
     * Subscribe to undo manager events
     * @param {Function} callback - Called with (event, data)
     * @returns {Function} - Unsubscribe function
     */
    subscribe(callback) {
        this._subscribers.add(callback);
        
        return () => {
            this._subscribers.delete(callback);
        };
    },
    
    /**
     * Get current state
     * @returns {string}
     */
    getState() {
        return this._state;
    },
    
    // Private methods
    
    _setState(newState) {
        const oldState = this._state;
        this._state = newState;
        
        if (oldState !== newState) {
            this._notify('stateChange', { from: oldState, to: newState });
        }
    },
    
    _cancelTimer() {
        if (this._expiryTimer) {
            clearTimeout(this._expiryTimer);
            this._expiryTimer = null;
        }
    },
    
    _handleExpiry() {
        console.log('[UndoManager] Undo window expired');
        
        this._setState(this.STATE.EXPIRED);
        this._notify('expired', this._action);
        
        // Clear action and return to IDLE
        this._action = null;
        this._setState(this.STATE.IDLE);
        this._syncToStateStore();
    },
    
    _notify(event, data) {
        this._subscribers.forEach(cb => {
            try {
                cb(event, data);
            } catch (e) {
                console.error('[UndoManager] Subscriber error:', e);
            }
        });
    },
    
    _syncToStateStore() {
        if (window.StateStore) {
            window.StateStore.set('undo', {
                available: this.canUndo(),
                action: this._action,
                expiresAt: this._action?.expiresAt || null
            }, true);
        }
    },
    
    /**
     * Recursively get all folders from an account
     * @param {object} account - Account object
     * @returns {Promise<Array>}
     */
    async _getAllFolders(account) {
        let allFolders = [];
        
        async function traverse(folder) {
            allFolders.push(folder);
            if (folder.subFolders && Array.isArray(folder.subFolders)) {
                for (let sub of folder.subFolders) {
                    await traverse(sub);
                }
            }
        }

        if (account.folders && Array.isArray(account.folders)) {
            for (let f of account.folders) {
                await traverse(f);
            }
        }
        
        return allFolders;
    }
};

// Export for use in other modules
window.UndoManager = UndoManager;
