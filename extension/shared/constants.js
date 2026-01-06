/**
 * MailSorter Shared Constants
 * Centralized configuration values used across the extension
 */

const MS_CONSTANTS = {
    // Native messaging
    NATIVE_APP_NAME: "com.mailsorter.backend",
    
    // Providers
    PROVIDERS: {
        OLLAMA: "ollama",
        OPENAI: "openai",
        ANTHROPIC: "anthropic",
        GEMINI: "gemini"
    },
    
    // Analysis modes
    ANALYSIS_MODES: {
        FULL: "full",
        HEADERS_ONLY: "headers_only"
    },
    
    // Connection states (UX-008)
    CONNECTION_STATUS: {
        CONNECTED: "connected",
        DISCONNECTED: "disconnected",
        CHECKING: "checking",
        ERROR: "error"
    },
    
    // Processing states (V5-029)
    PROCESSING_STATUS: {
        IDLE: "idle",
        PROCESSING: "processing",
        SUCCESS: "success",
        ERROR: "error"
    },
    
    // Undo configuration (UX-005)
    UNDO: {
        WINDOW_MS: 10000,  // 10 second undo window
        MAX_HISTORY: 10    // Max undo history items
    },
    
    // Health check intervals
    HEALTH_CHECK: {
        INTERVAL_MS: 30000,  // 30 seconds
        TIMEOUT_MS: 5000     // 5 second timeout
    },
    
    // Storage keys
    STORAGE_KEYS: {
        CONFIG: "config",
        ONBOARDING: "onboarding",
        STATS: "stats",
        UI_PREFERENCES: "ui"
    },
    
    // Default configuration
    DEFAULTS: {
        provider: "ollama",
        analysisMode: "full",
        passiveMode: false,
        thresholds: {
            default: 0.7,
            Trash: 0.9,
            Spam: 0.9
        },
        folderMappings: {}
    },
    
    // UI limits
    UI: {
        MAX_BODY_LENGTH: 2000,
        MAX_STATS_ENTRIES: 1000,
        DEBOUNCE_SAVE_MS: 500,
        TOAST_DURATION_MS: 5000
    },
    
    // Keyboard shortcuts (UX-002)
    SHORTCUTS: {
        CLASSIFY_SELECTED: "classify-selected"
    },
    
    // Context menu IDs (UX-003)
    MENU_IDS: {
        SORT_EMAIL: "mailsorter-sort-email",
        SORT_SELECTION: "mailsorter-sort-selection"
    },
    
    // Onboarding steps (UX-001)
    ONBOARDING_STEPS: {
        WELCOME: 0,
        PROVIDER: 1,
        CONNECTION: 2,
        FOLDERS: 3,
        COMPLETE: 4
    },
    
    // Message types for native messaging
    MESSAGE_TYPES: {
        // Existing
        PING: "ping",
        CLASSIFY: "classify",
        HEALTH: "health",
        BATCH_START: "batch_start",
        BATCH_STATUS: "batch_status",
        FEEDBACK: "feedback",
        STATS: "stats",
        
        // New for Phase 5
        GET_CONFIG: "get_config",
        SET_CONFIG: "set_config",
        TEST_CONNECTION: "test_connection",
        SET_PASSIVE: "set_passive",
        GET_STATS: "get_stats"
    },
    
    // Categories for folder mapping
    DEFAULT_CATEGORIES: [
        { id: "newsletters", label: "Newsletters", icon: "📧" },
        { id: "invoices", label: "Invoices", icon: "🧾" },
        { id: "work", label: "Work", icon: "💼" },
        { id: "personal", label: "Personal", icon: "👤" },
        { id: "support", label: "Support", icon: "🎫" },
        { id: "social", label: "Social", icon: "🌐" },
        { id: "promotions", label: "Promotions", icon: "🏷️" }
    ],
    
    // System folders to exclude from mapping
    SYSTEM_FOLDERS: [
        "Inbox", "Trash", "Sent", "Drafts", "Junk", 
        "Templates", "Archives", "Outbox"
    ]
};

// Freeze to prevent accidental modifications
Object.freeze(MS_CONSTANTS);
Object.freeze(MS_CONSTANTS.PROVIDERS);
Object.freeze(MS_CONSTANTS.ANALYSIS_MODES);
Object.freeze(MS_CONSTANTS.CONNECTION_STATUS);
Object.freeze(MS_CONSTANTS.PROCESSING_STATUS);
Object.freeze(MS_CONSTANTS.UNDO);
Object.freeze(MS_CONSTANTS.HEALTH_CHECK);
Object.freeze(MS_CONSTANTS.STORAGE_KEYS);
Object.freeze(MS_CONSTANTS.DEFAULTS);
Object.freeze(MS_CONSTANTS.UI);
Object.freeze(MS_CONSTANTS.SHORTCUTS);
Object.freeze(MS_CONSTANTS.MENU_IDS);
Object.freeze(MS_CONSTANTS.ONBOARDING_STEPS);
Object.freeze(MS_CONSTANTS.MESSAGE_TYPES);
Object.freeze(MS_CONSTANTS.DEFAULT_CATEGORIES);
Object.freeze(MS_CONSTANTS.SYSTEM_FOLDERS);

// Export for use in other modules
window.MS_CONSTANTS = MS_CONSTANTS;
