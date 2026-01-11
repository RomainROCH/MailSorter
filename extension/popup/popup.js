/**
 * MailSorter Popup Script
 * Quick status and controls popup
 */

// State
let undoInterval = null;

// DOM Elements
const elements = {};

/**
 * Initialize popup
 */
async function init() {
    // Cache elements
    cacheElements();
    
    // Apply translations
    if (window.I18n) {
        window.I18n.translateDocument();
    }
    
    // Load current state
    await loadState();
    
    // Set up event listeners
    setupEventListeners();
    
    // Check connection status
    await checkConnection();
    
    // Load stats
    await loadStats();
    
    // Check for undo availability
    await checkUndo();
    
    // Start status polling
    startStatusPolling();
    
    console.log('[Popup] Initialized');
}

/**
 * Cache DOM element references
 */
function cacheElements() {
    elements.statusDot = document.getElementById('status-dot');
    elements.backendStatus = document.getElementById('backend-status');
    elements.llmStatus = document.getElementById('llm-status');
    elements.llmName = document.getElementById('llm-name');
    elements.processingSection = document.getElementById('processing-section');
    elements.processingText = document.getElementById('processing-text');
    elements.processingProgress = document.getElementById('processing-progress');
    elements.passiveToggle = document.getElementById('passive-toggle');
    elements.passiveLabel = document.getElementById('passive-label');
    elements.statToday = document.getElementById('stat-today');
    elements.statWeek = document.getElementById('stat-week');
    elements.undoSection = document.getElementById('undo-section');
    elements.undoMessage = document.getElementById('undo-message');
    elements.undoCountdown = document.getElementById('undo-countdown');
    elements.undoButton = document.getElementById('undo-button');
    elements.undoProgress = document.getElementById('undo-progress');
    elements.openOptions = document.getElementById('open-options');
    elements.liveRegion = document.getElementById('live-region');
}

/**
 * Load current state from storage
 */
async function loadState() {
    try {
        const stored = await browser.storage.local.get(['config', 'processing', 'undo']);
        
        // Passive mode
        const passiveMode = stored.config?.passiveMode || false;
        elements.passiveToggle.checked = passiveMode;
        updatePassiveModeUI(passiveMode);
        
        // Processing state
        if (stored.processing?.active) {
            showProcessing(stored.processing);
        }
        
    } catch (e) {
        console.error('[Popup] Failed to load state:', e);
    }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Passive mode toggle
    elements.passiveToggle.addEventListener('change', async (e) => {
        const passiveMode = e.target.checked;
        await togglePassiveMode(passiveMode);
    });
    
    // Undo button
    elements.undoButton.addEventListener('click', async () => {
        await performUndo();
    });
    
    // Open options
    elements.openOptions.addEventListener('click', () => {
        browser.runtime.openOptionsPage();
        window.close();
    });
    
    // Listen for storage changes
    browser.storage.onChanged.addListener((changes, area) => {
        if (area === 'local') {
            handleStorageChange(changes);
        }
    });
}

/**
 * Check backend and LLM connection
 */
async function checkConnection() {
    updateStatusIndicator('checking');
    
    try {
        const response = await browser.runtime.sendMessage({ type: 'health-check' });
        
        if (response) {
            updateBackendStatus(response.status === 'ok');
            updateLLMStatus(response.provider?.healthy, response.provider?.name);
            updateStatusIndicator(response.status === 'ok' ? 'connected' : 'warning');
        } else {
            updateBackendStatus(false);
            updateLLMStatus(false);
            updateStatusIndicator('disconnected');
        }
        
    } catch (e) {
        console.warn('[Popup] Health check failed:', e);
        updateBackendStatus(false);
        updateLLMStatus(false);
        updateStatusIndicator('disconnected');
    }
}

/**
 * Update main status indicator
 */
function updateStatusIndicator(status) {
    elements.statusDot.className = 'ms-status-dot';
    
    switch (status) {
        case 'connected':
            elements.statusDot.classList.add('ms-status-dot-connected');
            break;
        case 'warning':
            elements.statusDot.classList.add('ms-status-dot-warning');
            break;
        case 'checking':
            elements.statusDot.classList.add('ms-status-dot-processing');
            break;
        default:
            elements.statusDot.classList.add('ms-status-dot-disconnected');
    }
}

/**
 * Update backend status display
 */
function updateBackendStatus(connected) {
    const dot = elements.backendStatus.querySelector('.ms-status-dot');
    const text = elements.backendStatus.querySelector('span:last-child');
    
    dot.className = 'ms-status-dot ' + 
        (connected ? 'ms-status-dot-connected' : 'ms-status-dot-disconnected');
    
    text.textContent = browser.i18n.getMessage(connected ? 'status_connected' : 'status_disconnected') 
        || (connected ? 'Connected' : 'Disconnected');
    
    elements.backendStatus.className = 'ms-status-badge ' + 
        (connected ? 'ms-status-badge-success' : 'ms-status-badge-error');
}

/**
 * Update LLM status display
 */
function updateLLMStatus(connected, providerName = null) {
    const dot = elements.llmStatus.querySelector('.ms-status-dot');

    // `connected` can be true/false/null (unknown)
    const isUnknown = connected === null || typeof connected === 'undefined';

    dot.className = 'ms-status-dot ' +
        (isUnknown
            ? 'ms-status-dot-warning'
            : (connected ? 'ms-status-dot-connected' : 'ms-status-dot-disconnected'));

    elements.llmName.textContent = providerName || (isUnknown ? 'Unknown' : '-');

    elements.llmStatus.className = 'ms-status-badge ' +
        (isUnknown
            ? 'ms-status-badge-warning'
            : (connected ? 'ms-status-badge-success' : 'ms-status-badge-error'));
}

/**
 * Toggle passive mode
 */
async function togglePassiveMode(enabled) {
    try {
        // Update storage
        const stored = await browser.storage.local.get('config');
        const config = stored.config || {};
        config.passiveMode = enabled;
        await browser.storage.local.set({ config });
        
        // Notify background
        await browser.runtime.sendMessage({ 
            type: 'set-passive-mode', 
            enabled 
        });
        
        updatePassiveModeUI(enabled);
        announce(enabled ? 'Sorting paused' : 'Sorting resumed');
        
    } catch (e) {
        console.error('[Popup] Failed to toggle passive mode:', e);
        // Revert toggle
        elements.passiveToggle.checked = !enabled;
    }
}

/**
 * Update passive mode UI
 */
function updatePassiveModeUI(enabled) {
    elements.passiveLabel.textContent = browser.i18n.getMessage(
        enabled ? 'popup_passive_on' : 'popup_passive_off'
    ) || (enabled ? 'Sorting Paused' : 'Sorting Active');
    
    elements.passiveLabel.className = 'passive-label ' + 
        (enabled ? 'passive-paused' : 'passive-active');
}

/**
 * Load and display stats
 */
async function loadStats() {
    try {
        const stored = await browser.storage.local.get('stats');
        const stats = stored.stats?.sortedEmails || [];
        const now = Date.now();
        const dayAgo = now - (24 * 60 * 60 * 1000);
        const weekAgo = now - (7 * 24 * 60 * 60 * 1000);
        
        const today = stats.filter(s => s.timestamp >= dayAgo).length;
        const week = stats.filter(s => s.timestamp >= weekAgo).length;
        
        elements.statToday.textContent = today;
        elements.statWeek.textContent = week;
        
    } catch (e) {
        console.warn('[Popup] Could not load stats:', e);
    }
}

/**
 * Check for undo availability
 */
async function checkUndo() {
    try {
        const stored = await browser.storage.local.get('undo');
        const undo = stored.undo;
        
        if (undo?.available && undo.action && undo.expiresAt > Date.now()) {
            showUndo(undo);
        } else {
            hideUndo();
        }
        
    } catch (e) {
        console.warn('[Popup] Could not check undo:', e);
    }
}

/**
 * Show undo section
 */
function showUndo(undo) {
    elements.undoSection.hidden = false;
    
    const message = browser.i18n.getMessage('undo_message', [undo.action.toFolder])
        || `Moved to ${undo.action.toFolder}`;
    elements.undoMessage.textContent = message;
    
    // Start countdown
    updateUndoCountdown(undo.expiresAt);
    
    if (undoInterval) clearInterval(undoInterval);
    undoInterval = setInterval(() => {
        const remaining = undo.expiresAt - Date.now();
        if (remaining <= 0) {
            hideUndo();
            clearInterval(undoInterval);
        } else {
            updateUndoCountdown(undo.expiresAt);
        }
    }, 100);
}

/**
 * Update undo countdown display
 */
function updateUndoCountdown(expiresAt) {
    const remaining = Math.max(0, expiresAt - Date.now());
    const seconds = Math.ceil(remaining / 1000);
    
    elements.undoCountdown.textContent = `${seconds}s`;
    
    const windowMs = window.MS_CONSTANTS?.UNDO?.WINDOW_MS || 10000;
    const progress = (remaining / windowMs) * 100;
    elements.undoProgress.style.width = `${progress}%`;
}

/**
 * Hide undo section
 */
function hideUndo() {
    elements.undoSection.hidden = true;
    if (undoInterval) {
        clearInterval(undoInterval);
        undoInterval = null;
    }
}

/**
 * Perform undo action
 */
async function performUndo() {
    elements.undoButton.disabled = true;
    
    try {
        const response = await browser.runtime.sendMessage({ type: 'undo-last-action' });
        
        if (response?.success) {
            hideUndo();
            announce(browser.i18n.getMessage('undo_success') || 'Move undone');
        } else {
            announce('Undo failed');
        }
        
    } catch (e) {
        console.error('[Popup] Undo failed:', e);
        announce('Undo failed');
    } finally {
        elements.undoButton.disabled = false;
    }
}

/**
 * Show processing indicator
 */
function showProcessing(processing) {
    elements.processingSection.hidden = false;
    
    if (processing.queue && processing.queue.length > 0) {
        const total = processing.queue.length;
        const current = total - processing.queue.length + 1;
        elements.processingText.textContent = `${current}/${total}`;
        elements.processingProgress.style.width = `${(current / total) * 100}%`;
    }
}

/**
 * Hide processing indicator
 */
function hideProcessing() {
    elements.processingSection.hidden = true;
}

/**
 * Handle storage changes
 */
function handleStorageChange(changes) {
    if (changes.config) {
        const passiveMode = changes.config.newValue?.passiveMode || false;
        elements.passiveToggle.checked = passiveMode;
        updatePassiveModeUI(passiveMode);
    }
    
    if (changes.processing) {
        if (changes.processing.newValue?.active) {
            showProcessing(changes.processing.newValue);
        } else {
            hideProcessing();
        }
    }
    
    if (changes.undo) {
        if (changes.undo.newValue?.available) {
            showUndo(changes.undo.newValue);
        } else {
            hideUndo();
        }
    }
    
    if (changes.stats) {
        loadStats();
    }
}

/**
 * Start polling for status updates
 */
function startStatusPolling() {
    // Check connection every 30 seconds
    setInterval(() => {
        checkConnection();
    }, 30000);
}

/**
 * Announce message to screen readers
 */
function announce(message) {
    elements.liveRegion.textContent = message;
    setTimeout(() => {
        elements.liveRegion.textContent = '';
    }, 1000);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
