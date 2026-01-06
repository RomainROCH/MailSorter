/**
 * MailSorter State Store
 * Centralized state management with browser.storage.local persistence
 */

const StateStore = {
    // In-memory state cache
    _state: null,
    
    // Subscribers for state changes
    _subscribers: new Map(),
    
    // Debounce timer for persistence
    _persistTimer: null,
    
    // Whether store is initialized
    _initialized: false,
    
    /**
     * Initialize the state store by loading from storage
     * @returns {Promise<void>}
     */
    async init() {
        if (this._initialized) {
            return;
        }
        
        try {
            const stored = await browser.storage.local.get(null);
            
            // Merge with defaults
            this._state = this._mergeWithDefaults(stored);
            
            // Listen for storage changes from other contexts
            browser.storage.onChanged.addListener((changes, area) => {
                if (area === 'local') {
                    this._handleStorageChange(changes);
                }
            });
            
            this._initialized = true;
            console.log('[StateStore] Initialized with state:', this._state);
            
        } catch (e) {
            console.error('[StateStore] Failed to initialize:', e);
            this._state = this._getDefaultState();
            this._initialized = true;
        }
    },
    
    /**
     * Get default state structure
     * @returns {object}
     */
    _getDefaultState() {
        const constants = window.MS_CONSTANTS || {};
        const defaults = constants.DEFAULTS || {};
        
        return {
            config: {
                provider: defaults.provider || 'ollama',
                analysisMode: defaults.analysisMode || 'full',
                passiveMode: defaults.passiveMode || false,
                thresholds: { ...defaults.thresholds } || {},
                folderMappings: { ...defaults.folderMappings } || {}
            },
            connection: {
                backend: 'disconnected',
                llm: 'disconnected',
                lastCheck: null
            },
            processing: {
                active: false,
                currentEmail: null,
                queue: []
            },
            undo: {
                available: false,
                action: null,
                expiresAt: null
            },
            stats: {
                sortedEmails: [],
                lastReset: Date.now()
            },
            onboarding: {
                completed: false,
                completedAt: null,
                currentStep: 0
            },
            ui: {
                locale: 'en',
                theme: 'auto'
            }
        };
    },
    
    /**
     * Merge stored data with defaults
     * @param {object} stored - Stored state
     * @returns {object} - Merged state
     */
    _mergeWithDefaults(stored) {
        const defaults = this._getDefaultState();
        
        // Deep merge each section
        const merged = { ...defaults };
        
        Object.keys(defaults).forEach(section => {
            if (stored[section] && typeof stored[section] === 'object') {
                merged[section] = { ...defaults[section], ...stored[section] };
            }
        });
        
        return merged;
    },
    
    /**
     * Get a value from state by path
     * @param {string} path - Dot-notation path (e.g., "config.provider")
     * @returns {any}
     */
    get(path) {
        if (!this._initialized) {
            console.warn('[StateStore] Not initialized, returning undefined');
            return undefined;
        }
        
        if (!path) {
            return { ...this._state };
        }
        
        const parts = path.split('.');
        let value = this._state;
        
        for (const part of parts) {
            if (value === undefined || value === null) {
                return undefined;
            }
            value = value[part];
        }
        
        // Return a copy to prevent mutation
        if (typeof value === 'object' && value !== null) {
            return Array.isArray(value) ? [...value] : { ...value };
        }
        
        return value;
    },
    
    /**
     * Set a value in state by path
     * @param {string} path - Dot-notation path
     * @param {any} value - Value to set
     * @param {boolean} persist - Whether to persist to storage
     * @returns {Promise<void>}
     */
    async set(path, value, persist = true) {
        if (!this._initialized) {
            await this.init();
        }
        
        const parts = path.split('.');
        const lastPart = parts.pop();
        let target = this._state;
        
        // Navigate to parent
        for (const part of parts) {
            if (target[part] === undefined) {
                target[part] = {};
            }
            target = target[part];
        }
        
        // Get old value for notification
        const oldValue = target[lastPart];
        
        // Set new value
        target[lastPart] = value;
        
        // Notify subscribers
        this._notifySubscribers(path, value, oldValue);
        
        // Persist to storage (debounced)
        if (persist) {
            this._debouncedPersist();
        }
    },
    
    /**
     * Update multiple values at once
     * @param {object} updates - Object with path:value pairs
     * @returns {Promise<void>}
     */
    async setMultiple(updates) {
        if (!this._initialized) {
            await this.init();
        }
        
        for (const [path, value] of Object.entries(updates)) {
            await this.set(path, value, false);
        }
        
        // Single persist after all updates
        await this.persist();
    },
    
    /**
     * Subscribe to state changes
     * @param {string} path - Path to watch (or '*' for all)
     * @param {Function} callback - Called with (newValue, oldValue, path)
     * @returns {Function} - Unsubscribe function
     */
    subscribe(path, callback) {
        if (!this._subscribers.has(path)) {
            this._subscribers.set(path, new Set());
        }
        
        this._subscribers.get(path).add(callback);
        
        // Return unsubscribe function
        return () => {
            const subs = this._subscribers.get(path);
            if (subs) {
                subs.delete(callback);
            }
        };
    },
    
    /**
     * Notify subscribers of state change
     * @param {string} changedPath - Path that changed
     * @param {any} newValue - New value
     * @param {any} oldValue - Old value
     */
    _notifySubscribers(changedPath, newValue, oldValue) {
        // Exact path match
        const exactSubs = this._subscribers.get(changedPath);
        if (exactSubs) {
            exactSubs.forEach(cb => {
                try {
                    cb(newValue, oldValue, changedPath);
                } catch (e) {
                    console.error('[StateStore] Subscriber error:', e);
                }
            });
        }
        
        // Wildcard subscribers
        const wildcardSubs = this._subscribers.get('*');
        if (wildcardSubs) {
            wildcardSubs.forEach(cb => {
                try {
                    cb(newValue, oldValue, changedPath);
                } catch (e) {
                    console.error('[StateStore] Subscriber error:', e);
                }
            });
        }
        
        // Parent path subscribers (e.g., "config" when "config.provider" changes)
        const parts = changedPath.split('.');
        for (let i = 1; i < parts.length; i++) {
            const parentPath = parts.slice(0, i).join('.');
            const parentSubs = this._subscribers.get(parentPath);
            if (parentSubs) {
                const parentValue = this.get(parentPath);
                parentSubs.forEach(cb => {
                    try {
                        cb(parentValue, null, changedPath);
                    } catch (e) {
                        console.error('[StateStore] Subscriber error:', e);
                    }
                });
            }
        }
    },
    
    /**
     * Debounced persistence to avoid excessive storage writes
     */
    _debouncedPersist() {
        if (this._persistTimer) {
            clearTimeout(this._persistTimer);
        }
        
        const debounceMs = window.MS_CONSTANTS?.UI?.DEBOUNCE_SAVE_MS || 500;
        
        this._persistTimer = setTimeout(() => {
            this.persist();
        }, debounceMs);
    },
    
    /**
     * Persist state to browser storage
     * @returns {Promise<void>}
     */
    async persist() {
        try {
            await browser.storage.local.set(this._state);
            console.log('[StateStore] State persisted');
        } catch (e) {
            console.error('[StateStore] Failed to persist state:', e);
            throw e;
        }
    },
    
    /**
     * Handle storage changes from other contexts
     * @param {object} changes - Storage changes
     */
    _handleStorageChange(changes) {
        Object.entries(changes).forEach(([key, { newValue, oldValue }]) => {
            if (this._state[key] !== newValue) {
                this._state[key] = newValue;
                this._notifySubscribers(key, newValue, oldValue);
            }
        });
    },
    
    /**
     * Reset state to defaults
     * @param {string} section - Section to reset (or null for all)
     * @returns {Promise<void>}
     */
    async reset(section = null) {
        const defaults = this._getDefaultState();
        
        if (section) {
            if (defaults[section]) {
                await this.set(section, defaults[section]);
            }
        } else {
            this._state = defaults;
            await this.persist();
            this._notifySubscribers('*', this._state, null);
        }
    },
    
    /**
     * Check if onboarding is complete
     * @returns {boolean}
     */
    isOnboardingComplete() {
        return this.get('onboarding.completed') === true;
    },
    
    /**
     * Mark onboarding as complete
     * @returns {Promise<void>}
     */
    async completeOnboarding() {
        await this.setMultiple({
            'onboarding.completed': true,
            'onboarding.completedAt': Date.now()
        });
    },
    
    /**
     * Record a sorted email for stats
     * @param {object} data - { folder, confidence }
     * @returns {Promise<void>}
     */
    async recordSort(data) {
        const stats = this.get('stats.sortedEmails') || [];
        const maxEntries = window.MS_CONSTANTS?.UI?.MAX_STATS_ENTRIES || 1000;
        
        // Add new entry
        stats.push({
            timestamp: Date.now(),
            folder: data.folder,
            confidence: data.confidence
        });
        
        // Trim if too many entries
        while (stats.length > maxEntries) {
            stats.shift();
        }
        
        await this.set('stats.sortedEmails', stats);
    },
    
    /**
     * Get stats for a time period
     * @param {string} period - 'day', 'week', or 'all'
     * @returns {object}
     */
    getStats(period = 'day') {
        const stats = this.get('stats.sortedEmails') || [];
        const now = Date.now();
        
        let cutoff;
        switch (period) {
            case 'day':
                cutoff = now - (24 * 60 * 60 * 1000);
                break;
            case 'week':
                cutoff = now - (7 * 24 * 60 * 60 * 1000);
                break;
            default:
                cutoff = 0;
        }
        
        const filtered = stats.filter(s => s.timestamp >= cutoff);
        
        // Calculate by folder
        const byFolder = {};
        filtered.forEach(s => {
            byFolder[s.folder] = (byFolder[s.folder] || 0) + 1;
        });
        
        return {
            total: filtered.length,
            byFolder,
            avgConfidence: filtered.length > 0
                ? filtered.reduce((sum, s) => sum + s.confidence, 0) / filtered.length
                : 0
        };
    }
};

// Export for use in other modules
window.StateStore = StateStore;
