/**
 * MailSorter Theme Manager
 * Handles theme switching between Palette B (default) and Classic themes
 * 
 * Themes:
 * - palette-b-dark (default): Modern high-tech dark theme
 * - palette-b-light: High contrast light theme
 * - classic-dark: Legacy Photon-inspired dark theme
 * - classic-light: Legacy Photon-inspired light theme
 */

const MSThemeManager = {
    // Storage key for theme preference
    STORAGE_KEY: "theme",
    
    // All theme-related classes
    ALL_THEME_CLASSES: ["theme-light", "theme-classic", "theme-dark"],
    
    /**
     * Initialize theme manager
     * Loads saved theme or respects system preference
     */
    async init() {
        const savedTheme = await this.getSavedTheme();
        
        if (savedTheme) {
            this.applyTheme(savedTheme);
        } else {
            // No saved theme - system preference will handle via CSS media queries
            // Default is Palette B Dark
            this.applyTheme(MS_CONSTANTS.THEMES.PALETTE_B_DARK);
        }
        
        // Listen for system preference changes
        this.watchSystemPreference();
    },
    
    /**
     * Get saved theme from storage
     * @returns {Promise<string|null>}
     */
    async getSavedTheme() {
        try {
            const result = await browser.storage.local.get(this.STORAGE_KEY);
            return result[this.STORAGE_KEY] || null;
        } catch (e) {
            console.warn("[ThemeManager] Could not read saved theme:", e);
            return null;
        }
    },
    
    /**
     * Save theme preference to storage
     * @param {string} theme - Theme identifier
     */
    async saveTheme(theme) {
        try {
            await browser.storage.local.set({ [this.STORAGE_KEY]: theme });
        } catch (e) {
            console.warn("[ThemeManager] Could not save theme:", e);
        }
    },
    
    /**
     * Apply a theme to the document
     * @param {string} theme - Theme identifier from MS_CONSTANTS.THEMES
     */
    applyTheme(theme) {
        const html = document.documentElement;
        
        // Remove all theme classes
        this.ALL_THEME_CLASSES.forEach(cls => html.classList.remove(cls));
        
        // Get classes for the requested theme
        const classes = MS_CONSTANTS.THEME_CLASSES[theme];
        
        if (classes && classes.length > 0) {
            classes.forEach(cls => html.classList.add(cls));
        }
        
        // Store current theme for reference
        html.dataset.theme = theme;
        
        console.log(`[ThemeManager] Applied theme: ${theme}`);
    },
    
    /**
     * Switch to a specific theme and save preference
     * @param {string} theme - Theme identifier
     */
    async setTheme(theme) {
        if (!MS_CONSTANTS.THEME_CLASSES.hasOwnProperty(theme)) {
            console.error(`[ThemeManager] Unknown theme: ${theme}`);
            return;
        }
        
        this.applyTheme(theme);
        await this.saveTheme(theme);
    },
    
    /**
     * Get current active theme
     * @returns {string}
     */
    getCurrentTheme() {
        return document.documentElement.dataset.theme || MS_CONSTANTS.THEMES.PALETTE_B_DARK;
    },
    
    /**
     * Toggle between light and dark mode (within same theme family)
     */
    async toggleLightDark() {
        const current = this.getCurrentTheme();
        let newTheme;
        
        switch (current) {
            case MS_CONSTANTS.THEMES.PALETTE_B_DARK:
                newTheme = MS_CONSTANTS.THEMES.PALETTE_B_LIGHT;
                break;
            case MS_CONSTANTS.THEMES.PALETTE_B_LIGHT:
                newTheme = MS_CONSTANTS.THEMES.PALETTE_B_DARK;
                break;
            case MS_CONSTANTS.THEMES.CLASSIC_DARK:
                newTheme = MS_CONSTANTS.THEMES.CLASSIC_LIGHT;
                break;
            case MS_CONSTANTS.THEMES.CLASSIC_LIGHT:
                newTheme = MS_CONSTANTS.THEMES.CLASSIC_DARK;
                break;
            default:
                newTheme = MS_CONSTANTS.THEMES.PALETTE_B_DARK;
        }
        
        await this.setTheme(newTheme);
    },
    
    /**
     * Toggle between Palette B and Classic theme (keeping light/dark preference)
     */
    async toggleThemeFamily() {
        const current = this.getCurrentTheme();
        const isLight = current.includes("light");
        const isClassic = current.includes("classic");
        
        let newTheme;
        
        if (isClassic) {
            // Switch to Palette B
            newTheme = isLight ? MS_CONSTANTS.THEMES.PALETTE_B_LIGHT : MS_CONSTANTS.THEMES.PALETTE_B_DARK;
        } else {
            // Switch to Classic
            newTheme = isLight ? MS_CONSTANTS.THEMES.CLASSIC_LIGHT : MS_CONSTANTS.THEMES.CLASSIC_DARK;
        }
        
        await this.setTheme(newTheme);
    },
    
    /**
     * Watch for system color scheme preference changes
     */
    watchSystemPreference() {
        if (window.matchMedia) {
            const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
            
            darkQuery.addEventListener("change", (e) => {
                // Only auto-switch if user hasn't explicitly set a theme
                // or if they want to follow system preference
                const current = this.getCurrentTheme();
                const isClassic = current.includes("classic");
                
                if (e.matches) {
                    // System switched to dark
                    this.applyTheme(isClassic ? MS_CONSTANTS.THEMES.CLASSIC_DARK : MS_CONSTANTS.THEMES.PALETTE_B_DARK);
                } else {
                    // System switched to light
                    this.applyTheme(isClassic ? MS_CONSTANTS.THEMES.CLASSIC_LIGHT : MS_CONSTANTS.THEMES.PALETTE_B_LIGHT);
                }
            });
        }
    },
    
    /**
     * Reset to default theme (Palette B Dark)
     */
    async resetToDefault() {
        await this.setTheme(MS_CONSTANTS.THEMES.PALETTE_B_DARK);
    },
    
    /**
     * Check if current theme is a light theme
     * @returns {boolean}
     */
    isLightMode() {
        return this.getCurrentTheme().includes("light");
    },
    
    /**
     * Check if current theme is Classic (Photon-based)
     * @returns {boolean}
     */
    isClassicTheme() {
        return this.getCurrentTheme().includes("classic");
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => MSThemeManager.init());
} else {
    MSThemeManager.init();
}

// Export for use in other modules
window.MSThemeManager = MSThemeManager;
