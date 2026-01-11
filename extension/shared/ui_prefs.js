/**
 * MailSorter UI Preferences
 * Small shared helper to persist and apply UI-only preferences (not backend config).
 */

const MSUiPrefs = {
    STORAGE_KEY_FONT: 'ui_font',

    /**
     * Read saved font mode.
     * @returns {Promise<'default'|'dyslexic'>}
     */
    async getFontMode() {
        try {
            const stored = await browser.storage.local.get(this.STORAGE_KEY_FONT);
            const mode = stored?.[this.STORAGE_KEY_FONT];
            return mode === 'dyslexic' ? 'dyslexic' : 'default';
        } catch (e) {
            return 'default';
        }
    },

    /**
     * Apply a font mode to the current document.
     * @param {'default'|'dyslexic'} mode
     */
    applyFontMode(mode) {
        const html = document.documentElement;
        html.classList.toggle('ms-font-dyslexic', mode === 'dyslexic');
    },

    /**
     * Save and apply font mode.
     * @param {'default'|'dyslexic'} mode
     */
    async setFontMode(mode) {
        const normalized = mode === 'dyslexic' ? 'dyslexic' : 'default';
        try {
            await browser.storage.local.set({ [this.STORAGE_KEY_FONT]: normalized });
        } catch (e) {
            // ignore
        }
        this.applyFontMode(normalized);
    },

    /**
     * Initialize and apply saved UI preferences.
     */
    async init() {
        const mode = await this.getFontMode();
        this.applyFontMode(mode);
    }
};

// Auto-apply as early as possible.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MSUiPrefs.init());
} else {
    MSUiPrefs.init();
}

window.MSUiPrefs = MSUiPrefs;
