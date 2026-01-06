/**
 * MailSorter Options Page (V5-027)
 * Full configuration UI for the extension
 */

// State
let currentConfig = {};
let isDirty = false;
let folders = [];

// DOM Elements
const elements = {};

/**
 * Initialize the options page
 */
async function init() {
    // Cache DOM elements
    cacheElements();
    
    // Apply translations
    if (window.I18n) {
        window.I18n.translateDocument();
    }
    
    // Set up tab navigation
    setupTabs();
    
    // Load configuration
    await loadConfiguration();
    
    // Load folders for mapping
    await loadFolders();
    
    // Set up event listeners
    setupEventListeners();
    
    // Check connection status
    await checkConnection();
    
    // Update stats display
    await updateStats();
    
    // Load keyboard shortcut
    await loadKeyboardShortcut();
    
    console.log('[Options] Initialized');
}

/**
 * Cache DOM element references
 */
function cacheElements() {
    elements.providerSelect = document.getElementById('provider-select');
    elements.analysisMode = document.getElementById('analysis-mode');
    elements.passiveMode = document.getElementById('passive-mode');
    elements.testConnection = document.getElementById('test-connection');
    elements.testSpinner = document.getElementById('test-spinner');
    elements.testResult = document.getElementById('test-result');
    elements.statusDot = document.getElementById('status-dot');
    elements.statusText = document.getElementById('status-text');
    elements.saveButton = document.getElementById('save-button');
    elements.saveStatus = document.getElementById('save-status');
    elements.thresholdDefault = document.getElementById('threshold-default');
    elements.thresholdDefaultValue = document.getElementById('threshold-default-value');
    elements.folderThresholds = document.getElementById('folder-thresholds');
    elements.addThreshold = document.getElementById('add-threshold');
    elements.categoryList = document.getElementById('category-list');
    elements.folderList = document.getElementById('folder-list');
    elements.mappingsList = document.getElementById('mappings-list');
    elements.noMappings = document.getElementById('no-mappings');
    elements.keyboardShortcut = document.getElementById('keyboard-shortcut');
    elements.statToday = document.getElementById('stat-today');
    elements.statWeek = document.getElementById('stat-week');
    elements.resetStats = document.getElementById('reset-stats');
    elements.resetSettings = document.getElementById('reset-settings');
    elements.toastContainer = document.getElementById('toast-container');
    elements.liveRegion = document.getElementById('live-region');
}

/**
 * Set up tab navigation
 */
function setupTabs() {
    const tabs = document.querySelectorAll('[role="tab"]');
    const panels = document.querySelectorAll('[role="tabpanel"]');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            activateTab(tab, tabs, panels);
        });
        
        tab.addEventListener('keydown', (e) => {
            handleTabKeydown(e, tabs, panels);
        });
    });
}

/**
 * Activate a tab
 */
function activateTab(selectedTab, tabs, panels) {
    // Deactivate all tabs
    tabs.forEach(tab => {
        tab.setAttribute('aria-selected', 'false');
        tab.classList.remove('ms-tab-active');
        tab.setAttribute('tabindex', '-1');
    });
    
    // Activate selected tab
    selectedTab.setAttribute('aria-selected', 'true');
    selectedTab.classList.add('ms-tab-active');
    selectedTab.setAttribute('tabindex', '0');
    selectedTab.focus();
    
    // Show corresponding panel
    const panelId = selectedTab.getAttribute('aria-controls');
    panels.forEach(panel => {
        if (panel.id === panelId) {
            panel.hidden = false;
            panel.classList.add('ms-tab-panel-active');
        } else {
            panel.hidden = true;
            panel.classList.remove('ms-tab-panel-active');
        }
    });
}

/**
 * Handle keyboard navigation in tabs
 */
function handleTabKeydown(e, tabs, panels) {
    const tabsArray = Array.from(tabs);
    const currentIndex = tabsArray.indexOf(e.target);
    let newIndex;
    
    switch (e.key) {
        case 'ArrowLeft':
            newIndex = currentIndex > 0 ? currentIndex - 1 : tabsArray.length - 1;
            activateTab(tabsArray[newIndex], tabs, panels);
            e.preventDefault();
            break;
        case 'ArrowRight':
            newIndex = currentIndex < tabsArray.length - 1 ? currentIndex + 1 : 0;
            activateTab(tabsArray[newIndex], tabs, panels);
            e.preventDefault();
            break;
        case 'Home':
            activateTab(tabsArray[0], tabs, panels);
            e.preventDefault();
            break;
        case 'End':
            activateTab(tabsArray[tabsArray.length - 1], tabs, panels);
            e.preventDefault();
            break;
    }
}

/**
 * Load configuration from storage
 */
async function loadConfiguration() {
    try {
        const stored = await browser.storage.local.get('config');
        const defaults = window.MS_CONSTANTS?.DEFAULTS || {};
        
        currentConfig = {
            provider: defaults.provider || 'ollama',
            analysisMode: defaults.analysisMode || 'full',
            passiveMode: defaults.passiveMode || false,
            thresholds: { ...defaults.thresholds },
            folderMappings: {},
            ...stored.config
        };
        
        // Update UI
        elements.providerSelect.value = currentConfig.provider;
        elements.analysisMode.value = currentConfig.analysisMode;
        elements.passiveMode.checked = currentConfig.passiveMode;
        
        // Update threshold slider
        const defaultThreshold = (currentConfig.thresholds?.default || 0.7) * 100;
        elements.thresholdDefault.value = defaultThreshold;
        elements.thresholdDefaultValue.textContent = (defaultThreshold / 100).toFixed(2);
        
        // Render folder-specific thresholds
        renderFolderThresholds();
        
        // Render folder mappings
        renderMappings();
        
        console.log('[Options] Loaded config:', currentConfig);
        
    } catch (e) {
        console.error('[Options] Failed to load config:', e);
        showToast('Failed to load settings', 'error');
    }
}

/**
 * Load available folders from accounts
 */
async function loadFolders() {
    try {
        const accounts = await browser.accounts.list();
        folders = [];
        
        for (const account of accounts) {
            const accountFolders = await getAllFolders(account);
            folders.push(...accountFolders.map(f => ({
                ...f,
                accountName: account.name,
                accountId: account.id
            })));
        }
        
        // Filter out system folders
        const systemFolders = window.MS_CONSTANTS?.SYSTEM_FOLDERS || [];
        const userFolders = folders.filter(f => !systemFolders.includes(f.name));
        
        // Populate folder list
        renderFolderList(userFolders);
        
        // Populate categories
        renderCategoryList();
        
        console.log('[Options] Loaded folders:', folders.length);
        
    } catch (e) {
        console.error('[Options] Failed to load folders:', e);
    }
}

/**
 * Recursively get all folders from an account
 */
async function getAllFolders(account) {
    let allFolders = [];
    
    async function traverse(folder, path = '') {
        const fullPath = path ? `${path}/${folder.name}` : folder.name;
        allFolders.push({ ...folder, fullPath });
        
        if (folder.subFolders && Array.isArray(folder.subFolders)) {
            for (const sub of folder.subFolders) {
                await traverse(sub, fullPath);
            }
        }
    }
    
    if (account.folders && Array.isArray(account.folders)) {
        for (const f of account.folders) {
            await traverse(f);
        }
    }
    
    return allFolders;
}

/**
 * Render category list for folder mapping
 */
function renderCategoryList() {
    const categories = window.MS_CONSTANTS?.DEFAULT_CATEGORIES || [];
    
    elements.categoryList.innerHTML = categories.map(cat => `
        <li class="ms-list-item ms-draggable category-item" 
            draggable="true" 
            data-category="${cat.id}"
            role="option"
            tabindex="0"
            aria-grabbed="false">
            <span class="category-icon">${cat.icon}</span>
            <span class="category-label">${cat.label}</span>
        </li>
    `).join('');
    
    // Set up drag events
    setupDragAndDrop();
}

/**
 * Render folder list for mapping targets
 */
function renderFolderList(folderList) {
    elements.folderList.innerHTML = folderList.map(folder => `
        <li class="ms-list-item ms-droppable folder-item" 
            data-folder-path="${folder.fullPath || folder.path}"
            data-folder-name="${folder.name}"
            role="option"
            tabindex="0"
            aria-dropeffect="move">
            <span class="folder-icon">📁</span>
            <span class="folder-name">${folder.name}</span>
            <span class="folder-account ms-text-secondary">${folder.accountName || ''}</span>
        </li>
    `).join('');
}

/**
 * Set up drag and drop for folder mapping
 */
function setupDragAndDrop() {
    const categories = elements.categoryList.querySelectorAll('.category-item');
    const folderItems = elements.folderList.querySelectorAll('.folder-item');
    
    categories.forEach(cat => {
        cat.addEventListener('dragstart', handleDragStart);
        cat.addEventListener('dragend', handleDragEnd);
        
        // Keyboard support
        cat.addEventListener('keydown', handleDragKeydown);
    });
    
    folderItems.forEach(folder => {
        folder.addEventListener('dragover', handleDragOver);
        folder.addEventListener('dragleave', handleDragLeave);
        folder.addEventListener('drop', handleDrop);
    });
}

let draggedCategory = null;

function handleDragStart(e) {
    draggedCategory = e.target.dataset.category;
    e.target.classList.add('dragging');
    e.target.setAttribute('aria-grabbed', 'true');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', draggedCategory);
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    e.target.setAttribute('aria-grabbed', 'false');
    draggedCategory = null;
    
    // Remove all drag-over states
    document.querySelectorAll('.folder-item').forEach(f => {
        f.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    e.target.closest('.folder-item')?.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.target.closest('.folder-item')?.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    const folderItem = e.target.closest('.folder-item');
    if (!folderItem || !draggedCategory) return;
    
    folderItem.classList.remove('drag-over');
    
    const folderPath = folderItem.dataset.folderPath;
    const folderName = folderItem.dataset.folderName;
    
    // Add mapping
    addMapping(draggedCategory, folderPath, folderName);
}

function handleDragKeydown(e) {
    // Keyboard-based drag and drop
    if (e.key === ' ' || e.key === 'Enter') {
        const category = e.target.dataset.category;
        // Toggle selection for keyboard users
        if (e.target.getAttribute('aria-grabbed') === 'true') {
            e.target.setAttribute('aria-grabbed', 'false');
            draggedCategory = null;
        } else {
            // Clear other selections
            document.querySelectorAll('.category-item').forEach(c => {
                c.setAttribute('aria-grabbed', 'false');
            });
            e.target.setAttribute('aria-grabbed', 'true');
            draggedCategory = category;
            announce('Press Enter on a folder to create mapping');
        }
        e.preventDefault();
    }
}

/**
 * Add a folder mapping
 */
function addMapping(categoryId, folderPath, folderName) {
    currentConfig.folderMappings = currentConfig.folderMappings || {};
    currentConfig.folderMappings[categoryId] = {
        path: folderPath,
        name: folderName
    };
    
    markDirty();
    renderMappings();
    
    const category = window.MS_CONSTANTS?.DEFAULT_CATEGORIES?.find(c => c.id === categoryId);
    showToast(`Mapped "${category?.label || categoryId}" → "${folderName}"`, 'success');
}

/**
 * Remove a folder mapping
 */
function removeMapping(categoryId) {
    if (currentConfig.folderMappings) {
        delete currentConfig.folderMappings[categoryId];
        markDirty();
        renderMappings();
    }
}

/**
 * Render current mappings
 */
function renderMappings() {
    const mappings = currentConfig.folderMappings || {};
    const categories = window.MS_CONSTANTS?.DEFAULT_CATEGORIES || [];
    const entries = Object.entries(mappings);
    
    if (entries.length === 0) {
        elements.mappingsList.innerHTML = '';
        elements.noMappings.hidden = false;
        return;
    }
    
    elements.noMappings.hidden = true;
    elements.mappingsList.innerHTML = entries.map(([catId, folder]) => {
        const cat = categories.find(c => c.id === catId);
        return `
            <li class="ms-list-item mapping-item">
                <span class="mapping-category">${cat?.icon || ''} ${cat?.label || catId}</span>
                <span class="mapping-arrow">→</span>
                <span class="mapping-folder">📁 ${folder.name}</span>
                <button class="ms-button ms-button-ghost ms-button-sm remove-mapping" 
                        data-category="${catId}"
                        aria-label="Remove mapping">
                    ×
                </button>
            </li>
        `;
    }).join('');
    
    // Add remove handlers
    elements.mappingsList.querySelectorAll('.remove-mapping').forEach(btn => {
        btn.addEventListener('click', () => {
            removeMapping(btn.dataset.category);
        });
    });
}

/**
 * Render folder-specific thresholds
 */
function renderFolderThresholds() {
    const thresholds = currentConfig.thresholds || {};
    const entries = Object.entries(thresholds).filter(([key]) => key !== 'default');
    
    elements.folderThresholds.innerHTML = entries.map(([folder, value]) => `
        <div class="ms-form-group threshold-row" data-folder="${folder}">
            <label class="ms-label">${folder}</label>
            <div class="threshold-input">
                <input type="range" min="0" max="100" value="${value * 100}" class="ms-range folder-threshold-range">
                <span class="threshold-value">${value.toFixed(2)}</span>
                <button class="ms-button ms-button-ghost ms-button-sm remove-threshold" aria-label="Remove">×</button>
            </div>
        </div>
    `).join('');
    
    // Add event listeners
    elements.folderThresholds.querySelectorAll('.folder-threshold-range').forEach(range => {
        range.addEventListener('input', (e) => {
            const row = e.target.closest('.threshold-row');
            const folder = row.dataset.folder;
            const value = e.target.value / 100;
            row.querySelector('.threshold-value').textContent = value.toFixed(2);
            currentConfig.thresholds[folder] = value;
            markDirty();
        });
    });
    
    elements.folderThresholds.querySelectorAll('.remove-threshold').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const row = e.target.closest('.threshold-row');
            const folder = row.dataset.folder;
            delete currentConfig.thresholds[folder];
            row.remove();
            markDirty();
        });
    });
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Provider change
    elements.providerSelect.addEventListener('change', (e) => {
        currentConfig.provider = e.target.value;
        markDirty();
    });
    
    // Analysis mode change
    elements.analysisMode.addEventListener('change', (e) => {
        currentConfig.analysisMode = e.target.value;
        markDirty();
    });
    
    // Passive mode toggle
    elements.passiveMode.addEventListener('change', (e) => {
        currentConfig.passiveMode = e.target.checked;
        markDirty();
    });
    
    // Default threshold slider
    elements.thresholdDefault.addEventListener('input', (e) => {
        const value = e.target.value / 100;
        elements.thresholdDefaultValue.textContent = value.toFixed(2);
        currentConfig.thresholds = currentConfig.thresholds || {};
        currentConfig.thresholds.default = value;
        markDirty();
    });
    
    // Add threshold button
    elements.addThreshold.addEventListener('click', () => {
        addFolderThreshold();
    });
    
    // Test connection button
    elements.testConnection.addEventListener('click', () => {
        testConnection();
    });
    
    // Save button
    elements.saveButton.addEventListener('click', () => {
        saveConfiguration();
    });
    
    // Reset buttons
    elements.resetStats.addEventListener('click', () => {
        resetStats();
    });
    
    elements.resetSettings.addEventListener('click', () => {
        resetSettings();
    });
    
    // Keyboard shortcut on save
    window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveConfiguration();
        }
    });
}

/**
 * Add a folder-specific threshold
 */
function addFolderThreshold() {
    const folderName = prompt('Enter folder name:');
    if (!folderName) return;
    
    currentConfig.thresholds = currentConfig.thresholds || {};
    currentConfig.thresholds[folderName] = 0.7;
    
    renderFolderThresholds();
    markDirty();
}

/**
 * Mark configuration as dirty (needs saving)
 */
function markDirty() {
    isDirty = true;
    elements.saveButton.textContent = 'Save *';
}

/**
 * Save configuration to storage
 */
async function saveConfiguration() {
    elements.saveStatus.hidden = false;
    elements.saveButton.disabled = true;
    
    try {
        await browser.storage.local.set({ config: currentConfig });
        
        // Notify background script
        try {
            await browser.runtime.sendMessage({
                type: 'config-updated',
                config: currentConfig
            });
        } catch (e) {
            // Background might not be listening, that's OK
        }
        
        isDirty = false;
        elements.saveButton.textContent = 'Save';
        
        showToast(browser.i18n.getMessage('options_saved') || 'Settings saved successfully', 'success');
        announce('Settings saved');
        
    } catch (e) {
        console.error('[Options] Failed to save:', e);
        showToast('Failed to save settings', 'error');
    } finally {
        elements.saveStatus.hidden = true;
        elements.saveButton.disabled = false;
    }
}

/**
 * Check backend connection status
 */
async function checkConnection() {
    updateConnectionStatus('checking');
    
    try {
        // Send health check via runtime message to background
        const response = await browser.runtime.sendMessage({ type: 'health-check' });
        
        if (response && response.status === 'ok') {
            updateConnectionStatus('connected', response);
        } else {
            updateConnectionStatus('disconnected');
        }
        
    } catch (e) {
        console.warn('[Options] Connection check failed:', e);
        updateConnectionStatus('disconnected');
    }
}

/**
 * Update connection status display
 */
function updateConnectionStatus(status, details = null) {
    elements.statusDot.className = 'ms-status-dot';
    
    switch (status) {
        case 'connected':
            elements.statusDot.classList.add('ms-status-dot-connected');
            elements.statusText.textContent = browser.i18n.getMessage('status_connected') || 'Connected';
            break;
        case 'disconnected':
            elements.statusDot.classList.add('ms-status-dot-disconnected');
            elements.statusText.textContent = browser.i18n.getMessage('status_disconnected') || 'Disconnected';
            break;
        case 'checking':
            elements.statusDot.classList.add('ms-status-dot-processing');
            elements.statusText.textContent = browser.i18n.getMessage('status_checking') || 'Checking...';
            break;
    }
}

/**
 * Test connection to backend
 */
async function testConnection() {
    elements.testSpinner.hidden = false;
    elements.testConnection.disabled = true;
    elements.testResult.hidden = true;
    
    try {
        const response = await browser.runtime.sendMessage({ type: 'test-connection' });
        
        elements.testResult.hidden = false;
        
        if (response && response.backend && response.llm) {
            elements.testResult.className = 'test-result test-result-success';
            elements.testResult.textContent = browser.i18n.getMessage('options_connection_success') || 
                'Connection successful! Backend and LLM are working.';
            updateConnectionStatus('connected');
        } else {
            elements.testResult.className = 'test-result test-result-error';
            elements.testResult.textContent = browser.i18n.getMessage('options_connection_failed') || 
                'Connection failed. Please check your settings.';
            updateConnectionStatus('disconnected');
        }
        
    } catch (e) {
        console.error('[Options] Test connection failed:', e);
        elements.testResult.hidden = false;
        elements.testResult.className = 'test-result test-result-error';
        elements.testResult.textContent = 'Connection test failed: ' + e.message;
        updateConnectionStatus('disconnected');
    } finally {
        elements.testSpinner.hidden = true;
        elements.testConnection.disabled = false;
    }
}

/**
 * Load keyboard shortcut
 */
async function loadKeyboardShortcut() {
    try {
        const commands = await browser.commands.getAll();
        const classifyCommand = commands.find(c => c.name === 'classify-selected');
        
        if (classifyCommand && classifyCommand.shortcut) {
            elements.keyboardShortcut.value = classifyCommand.shortcut;
        }
    } catch (e) {
        console.warn('[Options] Could not load keyboard shortcut:', e);
    }
}

/**
 * Update stats display
 */
async function updateStats() {
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
        console.warn('[Options] Could not load stats:', e);
    }
}

/**
 * Reset statistics
 */
async function resetStats() {
    if (!confirm('Are you sure you want to reset all statistics?')) {
        return;
    }
    
    try {
        await browser.storage.local.set({
            stats: {
                sortedEmails: [],
                lastReset: Date.now()
            }
        });
        
        elements.statToday.textContent = '0';
        elements.statWeek.textContent = '0';
        
        showToast('Statistics reset', 'success');
        
    } catch (e) {
        console.error('[Options] Failed to reset stats:', e);
        showToast('Failed to reset statistics', 'error');
    }
}

/**
 * Reset all settings
 */
async function resetSettings() {
    if (!confirm('Are you sure you want to reset ALL settings to defaults? This cannot be undone.')) {
        return;
    }
    
    try {
        const defaults = window.MS_CONSTANTS?.DEFAULTS || {};
        
        currentConfig = {
            provider: defaults.provider || 'ollama',
            analysisMode: defaults.analysisMode || 'full',
            passiveMode: defaults.passiveMode || false,
            thresholds: { ...defaults.thresholds },
            folderMappings: {}
        };
        
        await browser.storage.local.set({ config: currentConfig });
        await loadConfiguration();
        
        showToast('Settings reset to defaults', 'success');
        
    } catch (e) {
        console.error('[Options] Failed to reset settings:', e);
        showToast('Failed to reset settings', 'error');
    }
}

/**
 * Show a toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `ms-toast ms-toast-${type}`;
    toast.innerHTML = `
        <div class="ms-toast-content">
            <div class="ms-toast-message">${message}</div>
        </div>
        <button class="ms-toast-close" aria-label="Close">×</button>
    `;
    
    toast.querySelector('.ms-toast-close').addEventListener('click', () => {
        toast.remove();
    });
    
    elements.toastContainer.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
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
