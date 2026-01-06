/**
 * MailSorter Internationalization Helper
 * Provides i18n utilities for the extension (V5-028)
 */

const I18n = {
    /**
     * Get a localized message by key
     * @param {string} key - Message key from messages.json
     * @param {string|string[]} substitutions - Optional substitution values
     * @returns {string} - Localized message or key if not found
     */
    get(key, substitutions = []) {
        try {
            // Ensure substitutions is an array
            const subs = Array.isArray(substitutions) ? substitutions : [substitutions];
            
            const message = browser.i18n.getMessage(key, subs);
            
            // Return key if message not found (for debugging)
            if (!message) {
                console.warn(`[I18n] Missing translation for key: ${key}`);
                return key;
            }
            
            return message;
        } catch (e) {
            console.error(`[I18n] Error getting message for key: ${key}`, e);
            return key;
        }
    },

    /**
     * Get the current UI locale
     * @returns {string} - Current locale (e.g., "en", "fr")
     */
    getLocale() {
        try {
            return browser.i18n.getUILanguage().split('-')[0];
        } catch (e) {
            return 'en';
        }
    },

    /**
     * Check if current locale is RTL
     * @returns {boolean}
     */
    isRTL() {
        const rtlLocales = ['ar', 'he', 'fa', 'ur'];
        return rtlLocales.includes(this.getLocale());
    },

    /**
     * Format a number according to locale
     * @param {number} num - Number to format
     * @param {object} options - Intl.NumberFormat options
     * @returns {string}
     */
    formatNumber(num, options = {}) {
        try {
            return new Intl.NumberFormat(browser.i18n.getUILanguage(), options).format(num);
        } catch (e) {
            return String(num);
        }
    },

    /**
     * Format a date according to locale
     * @param {Date|number} date - Date to format
     * @param {object} options - Intl.DateTimeFormat options
     * @returns {string}
     */
    formatDate(date, options = { dateStyle: 'medium', timeStyle: 'short' }) {
        try {
            const dateObj = date instanceof Date ? date : new Date(date);
            return new Intl.DateTimeFormat(browser.i18n.getUILanguage(), options).format(dateObj);
        } catch (e) {
            return String(date);
        }
    },

    /**
     * Format a relative time (e.g., "2 hours ago")
     * @param {Date|number} date - Date to format
     * @returns {string}
     */
    formatRelativeTime(date) {
        try {
            const dateObj = date instanceof Date ? date : new Date(date);
            const now = new Date();
            const diffMs = now - dateObj;
            const diffSec = Math.floor(diffMs / 1000);
            const diffMin = Math.floor(diffSec / 60);
            const diffHour = Math.floor(diffMin / 60);
            const diffDay = Math.floor(diffHour / 24);

            const rtf = new Intl.RelativeTimeFormat(browser.i18n.getUILanguage(), { 
                numeric: 'auto' 
            });

            if (diffSec < 60) {
                return rtf.format(-diffSec, 'second');
            } else if (diffMin < 60) {
                return rtf.format(-diffMin, 'minute');
            } else if (diffHour < 24) {
                return rtf.format(-diffHour, 'hour');
            } else if (diffDay < 30) {
                return rtf.format(-diffDay, 'day');
            } else {
                return this.formatDate(dateObj);
            }
        } catch (e) {
            return this.formatDate(date);
        }
    },

    /**
     * Pluralize a message based on count
     * Uses ICU message format pattern in messages.json
     * @param {string} key - Base message key
     * @param {number} count - Count for pluralization
     * @returns {string}
     */
    plural(key, count) {
        // Try to get specific plural form
        const pluralKey = count === 1 ? `${key}_one` : `${key}_other`;
        const message = this.get(pluralKey, [String(count)]);
        
        // Fall back to base key if plural form not found
        if (message === pluralKey) {
            return this.get(key, [String(count)]);
        }
        
        return message;
    },

    /**
     * Apply translations to DOM elements with data-i18n attribute
     * @param {Element} root - Root element to search in (default: document)
     */
    translateDocument(root = document) {
        // Translate text content
        root.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translated = this.get(key);
            
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = translated;
            } else {
                el.textContent = translated;
            }
        });

        // Translate attributes (data-i18n-attr="title:key,aria-label:key")
        root.querySelectorAll('[data-i18n-attr]').forEach(el => {
            const attrs = el.getAttribute('data-i18n-attr').split(',');
            attrs.forEach(attr => {
                const [attrName, key] = attr.split(':').map(s => s.trim());
                if (attrName && key) {
                    el.setAttribute(attrName, this.get(key));
                }
            });
        });

        // Translate HTML content (use with caution - sanitize!)
        root.querySelectorAll('[data-i18n-html]').forEach(el => {
            const key = el.getAttribute('data-i18n-html');
            // Only allow safe HTML (no scripts)
            const translated = this.get(key)
                .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
            el.innerHTML = translated;
        });

        // Set document direction for RTL languages
        if (this.isRTL()) {
            document.documentElement.setAttribute('dir', 'rtl');
        }
    },

    /**
     * Create a translated element
     * @param {string} tag - HTML tag name
     * @param {string} i18nKey - Translation key
     * @param {object} attrs - Additional attributes
     * @returns {HTMLElement}
     */
    createElement(tag, i18nKey, attrs = {}) {
        const el = document.createElement(tag);
        el.textContent = this.get(i18nKey);
        el.setAttribute('data-i18n', i18nKey);
        
        Object.entries(attrs).forEach(([key, value]) => {
            el.setAttribute(key, value);
        });
        
        return el;
    }
};

// Export for use in other modules
window.I18n = I18n;
