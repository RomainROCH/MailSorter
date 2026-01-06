/**
 * Feature Detection Module for Thunderbird/Betterbird API Compatibility
 * Plan V5: Ensures graceful degradation when APIs are unavailable.
 */

const FeatureDetection = {
    // Cache detected features
    _cache: {},

    /**
     * Check if a specific API method exists
     * @param {string} namespace - e.g., 'messages', 'accounts'
     * @param {string} method - e.g., 'update', 'getFull'
     * @returns {boolean}
     */
    hasMethod(namespace, method) {
        const cacheKey = `${namespace}.${method}`;
        if (this._cache[cacheKey] !== undefined) {
            return this._cache[cacheKey];
        }

        try {
            const ns = browser[namespace];
            const result = ns && typeof ns[method] === 'function';
            this._cache[cacheKey] = result;
            return result;
        } catch (e) {
            this._cache[cacheKey] = false;
            return false;
        }
    },

    /**
     * Check if custom headers can be set on messages
     * @returns {boolean}
     */
    supportsCustomHeaders() {
        // messages.update with headers support was added in TB 115+
        return this.hasMethod('messages', 'update');
    },

    /**
     * Check if full message body retrieval is available
     * @returns {boolean}
     */
    supportsGetFull() {
        return this.hasMethod('messages', 'getFull');
    },

    /**
     * Check if message tags are supported
     * @returns {boolean}
     */
    supportsMessageTags() {
        return this.hasMethod('messages', 'listTags');
    },

    /**
     * Check if folder creation is supported
     * @returns {boolean}
     */
    supportsFolderCreation() {
        return this.hasMethod('folders', 'create');
    },

    /**
     * Get Thunderbird/Betterbird version info
     * @returns {Promise<{name: string, version: string}>}
     */
    async getBrowserInfo() {
        try {
            if (browser.runtime && browser.runtime.getBrowserInfo) {
                return await browser.runtime.getBrowserInfo();
            }
        } catch (e) {
            console.warn('Could not get browser info:', e);
        }
        return { name: 'Unknown', version: '0.0' };
    },

    /**
     * Get full feature report
     * @returns {Promise<Object>}
     */
    async getFeatureReport() {
        const browserInfo = await this.getBrowserInfo();
        return {
            browser: browserInfo,
            features: {
                customHeaders: this.supportsCustomHeaders(),
                getFullMessage: this.supportsGetFull(),
                messageTags: this.supportsMessageTags(),
                folderCreation: this.supportsFolderCreation()
            }
        };
    },

    /**
     * Log feature support on startup
     */
    async logFeatures() {
        const report = await this.getFeatureReport();
        console.log('MailSorter Feature Detection Report:', report);
        
        if (!report.features.getFullMessage) {
            console.warn('⚠️ messages.getFull not available - body extraction will be limited');
        }
        if (!report.features.customHeaders) {
            console.warn('⚠️ Custom headers not supported - will use tags as fallback');
        }
        
        return report;
    }
};

// Export for use in background.js
window.FeatureDetection = FeatureDetection;
