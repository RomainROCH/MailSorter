/**
 * MailSorter Options Page (V5-027)
 * Full configuration UI for the extension
 */

// State
let currentConfig = {};
let isDirty = false;
let folders = [];
let userFoldersForMapping = [];

// Autosave (debounced)
let _autoSaveTimer = null;
let _autoSaveInProgress = false;

// DOM Elements
const elements = {};

function setVisible(el, visible) {
    if (!el) return;
    // Be robust across Betterbird/Thunderbird surfaces
    el.hidden = !visible;
    el.style.display = visible ? '' : 'none';
}

/**
 * Initialize the options page
 */
async function init() {
    // Cache DOM elements
    cacheElements();

    // Force a clean initial UI state (prevents "Saving..." or spinners from showing)
    setVisible(elements.saveStatus, false);
    setVisible(elements.testSpinner, false);
    setVisible(elements.testResult, false);

    // Render version so we can confirm the correct build is installed
    try {
        const manifest = browser.runtime.getManifest();
        const versionEl = document.getElementById('ms-version');
        if (versionEl && manifest?.version) {
            versionEl.textContent = `MailSorter v${manifest.version}`;
        }
    } catch (e) {
        // ignore
    }
    
    // Apply translations
    if (window.I18n) {
        window.I18n.translateDocument();
    }
    
    // Set up tab navigation
    setupTabs();

    // Safety: while options is open, pause automatic moving (prevents accidental sorting)
    try {
        await browser.runtime.sendMessage({ type: 'options-editing', enabled: true });
    } catch (_) {
        // ignore
    }

    const endEditing = async () => {
        try {
            await browser.runtime.sendMessage({ type: 'options-editing', enabled: false });
        } catch (_) {
            // ignore
        }
    };
        const flushAndClose = () => {
            // Best-effort flush (important if user closes immediately after mapping).
            if (isDirty) {
                try {
                    browser.storage.local.set({ config: currentConfig });
                    browser.runtime.sendMessage({ type: 'config-updated', config: currentConfig });
                } catch (e) {
                    // ignore
                }
            }
            try {
                browser.runtime.sendMessage({ type: 'options-editing', enabled: false });
            } catch (e) {
                // ignore
            }
        };

        window.addEventListener('pagehide', flushAndClose);
        window.addEventListener('unload', flushAndClose);
    
    // Load configuration
    await loadConfiguration();

    // Load UI-only preferences into controls
    await loadUiPreferences();
    
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
    elements.fontMode = document.getElementById('font-mode');
}

async function loadUiPreferences() {
    if (!elements.fontMode) return;
    try {
        const mode = await window.MSUiPrefs?.getFontMode?.();
        if (mode) elements.fontMode.value = mode;
    } catch (_) {
        // ignore
    }
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
        userFoldersForMapping = userFolders;
        
        // Populate folder list
        renderFolderList(userFolders);
        
        // Populate categories
        renderCategoryList();

        // Apply mapping visuals (mapped indicators + folder tags)
        renderMappingVisuals();
        
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
    const usePointerDrag = typeof window.PointerEvent !== 'undefined';
    
    elements.categoryList.innerHTML = categories.map(cat => `
        <li class="ms-list-item ms-draggable category-item" 
            draggable="${usePointerDrag ? 'false' : 'true'}" 
            data-category="${cat.id}"
            role="option"
            tabindex="0"
            aria-grabbed="false">
            <span class="category-icon">${cat.icon}</span>
            <span class="category-label">${cat.label}</span>
            <span class="category-mapped-to" aria-hidden="true"></span>
        </li>
    `).join('');
    
    // Set up drag events
    setupDragAndDrop();

    renderMappingVisuals();
}

/**
 * Render folder list for mapping targets
 */
function renderFolderList(folderList) {
    elements.folderList.innerHTML = folderList.map(folder => `
        <li class="ms-list-item folder-item" 
            data-folder-path="${folder.fullPath || folder.path}"
            data-folder-name="${folder.name}"
            role="option"
            tabindex="0"
            aria-dropeffect="move">
            <span class="folder-icon">📁</span>
            <span class="folder-name">${folder.name}</span>
            <span class="folder-account ms-text-secondary">${folder.accountName || ''}</span>
            <span class="folder-tags" aria-label=""></span>
        </li>
    `).join('');

    // Re-bind listeners for newly rendered targets
    setupDragAndDrop();

    renderMappingVisuals();
}

/**
 * Set up drag and drop for folder mapping
 */
function setupDragAndDrop() {
    const categories = elements.categoryList.querySelectorAll('.category-item');
    const folderItems = elements.folderList.querySelectorAll('.folder-item');
    
    categories.forEach(cat => {
        if (cat.dataset.msBound === '1') return;
        cat.dataset.msBound = '1';

        cat.addEventListener('dragstart', handleDragStart);
        cat.addEventListener('dragend', handleDragEnd);
        cat.addEventListener('click', handleCategoryClick);

        // Betterbird-friendly pseudo-drag using Pointer Events (HTML5 DnD can be unreliable)
        cat.addEventListener('pointerdown', handlePointerDown);
        
        // Keyboard support
        cat.addEventListener('keydown', handleDragKeydown);
    });
    
    folderItems.forEach(folder => {
        if (folder.dataset.msBound === '1') return;
        folder.dataset.msBound = '1';

        folder.addEventListener('dragover', handleDragOver);
        folder.addEventListener('dragleave', handleDragLeave);
        folder.addEventListener('drop', handleDrop);
        folder.addEventListener('click', handleFolderClick);

        // Keyboard support: apply mapping when a category is "grabbed"
        folder.addEventListener('keydown', handleFolderKeydown);
    });

    // Global pointer listeners (registered once)
    if (!setupDragAndDrop._pointerListenersAdded) {
        document.addEventListener('pointermove', handlePointerMove, { passive: true });
        document.addEventListener('pointerup', handlePointerUp, true);
        document.addEventListener('pointercancel', handlePointerUp, true);
        setupDragAndDrop._pointerListenersAdded = true;
    }
}

let draggedCategory = null;

let pointerDrag = null;
const POINTER_DRAG_THRESHOLD_PX = 3;

function handleDragStart(e) {
    const categoryItem = e.currentTarget;
    draggedCategory = categoryItem.dataset.category;
    categoryItem.classList.add('dragging');
    categoryItem.setAttribute('aria-grabbed', 'true');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/x-mailsorter-category', draggedCategory);
    e.dataTransfer.setData('text/plain', draggedCategory);
}

function handlePointerDown(e) {
    // Only primary mouse button for mouse pointers
    if (e.pointerType === 'mouse' && e.button !== 0) return;

    const categoryItem = e.currentTarget;
    const category = categoryItem?.dataset?.category;
    if (!category) return;

    // Always capture the intended category immediately.
    // This prevents "previous category" being reused if the gesture is short.
    draggedCategory = category;

    pointerDrag = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        active: false,
        category,
        categoryItem,
        lastFolderItem: null
    };

    try {
        categoryItem.setPointerCapture?.(e.pointerId);
    } catch (_) {
        // ignore
    }
}

function handlePointerMove(e) {
    if (!pointerDrag || e.pointerId !== pointerDrag.pointerId) return;

    const dx = e.clientX - pointerDrag.startX;
    const dy = e.clientY - pointerDrag.startY;
    const dist = Math.sqrt(dx * dx + dy * dy);

    if (!pointerDrag.active) {
        if (dist < POINTER_DRAG_THRESHOLD_PX) return;
        pointerDrag.active = true;

        // Mark as actively dragging
        draggedCategory = pointerDrag.category;
        pointerDrag.categoryItem.classList.add('dragging');
        pointerDrag.categoryItem.setAttribute('aria-grabbed', 'true');
    }

    // Identify folder target under pointer
    const under = document.elementFromPoint(e.clientX, e.clientY);
    const folderItem = under?.closest?.('.folder-item') || null;

    if (pointerDrag.lastFolderItem && pointerDrag.lastFolderItem !== folderItem) {
        pointerDrag.lastFolderItem.classList.remove('drag-over');
        pointerDrag.lastFolderItem = null;
    }

    if (folderItem) {
        folderItem.classList.add('drag-over');
        pointerDrag.lastFolderItem = folderItem;
    }
}

function handlePointerUp(e) {
    if (!pointerDrag || e.pointerId !== pointerDrag.pointerId) return;

    const { categoryItem, category } = pointerDrag;
    const lastFolderItem = pointerDrag.lastFolderItem;
    const dx = e.clientX - pointerDrag.startX;
    const dy = e.clientY - pointerDrag.startY;
    const dist = Math.sqrt(dx * dx + dy * dy);

    // Cleanup visuals
    categoryItem.classList.remove('dragging');
    categoryItem.setAttribute('aria-grabbed', 'false');
    if (lastFolderItem) {
        lastFolderItem.classList.remove('drag-over');
    }

    // Find folder under pointer at release (more reliable than relying on dragover).
    const under = document.elementFromPoint(e.clientX, e.clientY);
    const folderItem = under?.closest?.('.folder-item') || lastFolderItem || null;

    const shouldTreatAsDrag = dist >= POINTER_DRAG_THRESHOLD_PX;

    pointerDrag = null;

    if (!folderItem || !shouldTreatAsDrag) {
        // No mapping; leave click-to-map behavior available.
        return;
    }

    // Avoid a stray click toggling selection after a drag gesture
    try {
        categoryItem.dataset.msIgnoreClick = '1';
        setTimeout(() => {
            try { delete categoryItem.dataset.msIgnoreClick; } catch (_) { /* ignore */ }
        }, 0);
        e.preventDefault?.();
        e.stopPropagation?.();
    } catch (_) {
        // ignore
    }

    const folderPath = folderItem.dataset.folderPath;
    const folderName = folderItem.dataset.folderName;
    if (!folderPath || !folderName) return;

    addMapping(category, folderPath, folderName);

    // Clear selection after mapping
    document.querySelectorAll('.category-item').forEach(c => {
        c.setAttribute('aria-grabbed', 'false');
        c.classList.remove('ms-selected');
    });
    draggedCategory = null;
}

function handleDragEnd(e) {
    const categoryItem = e.currentTarget;
    categoryItem.classList.remove('dragging');
    categoryItem.setAttribute('aria-grabbed', 'false');
    draggedCategory = null;
    
    // Remove all drag-over states
    document.querySelectorAll('.folder-item').forEach(f => {
        f.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    const folderItem = e.currentTarget;
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
        const category = e.currentTarget.dataset.category;
        // Toggle selection for keyboard users
        if (e.currentTarget.getAttribute('aria-grabbed') === 'true') {
            e.currentTarget.setAttribute('aria-grabbed', 'false');
            draggedCategory = null;
        } else {
            // Clear other selections
            document.querySelectorAll('.category-item').forEach(c => {
                c.setAttribute('aria-grabbed', 'false');
            });
            e.currentTarget.setAttribute('aria-grabbed', 'true');
            draggedCategory = category;
            announce('Press Enter on a folder to create mapping');
        }
        e.preventDefault();
    }
}

function handleCategoryClick(e) {
    const categoryItem = e.currentTarget;
    if (categoryItem?.dataset?.msIgnoreClick === '1') {
        try { delete categoryItem.dataset.msIgnoreClick; } catch (_) { /* ignore */ }
        return;
    }
    const category = categoryItem.dataset.category;
    if (!category) return;

    // Toggle selection
    const isSelected = categoryItem.getAttribute('aria-grabbed') === 'true';
    document.querySelectorAll('.category-item').forEach(c => {
        c.setAttribute('aria-grabbed', 'false');
        c.classList.remove('ms-selected');
    });

    if (!isSelected) {
        categoryItem.setAttribute('aria-grabbed', 'true');
        categoryItem.classList.add('ms-selected');
        draggedCategory = category;
        announce('Category selected. Click a folder to map.');
    } else {
        draggedCategory = null;
        announce('Category selection cleared.');
    }
}

function handleFolderClick(e) {
    if (!draggedCategory) return;
    const folderItem = e.currentTarget;
    const folderPath = folderItem.dataset.folderPath;
    const folderName = folderItem.dataset.folderName;
    if (!folderPath || !folderName) return;

    addMapping(draggedCategory, folderPath, folderName);

    // Clear selection after mapping
    document.querySelectorAll('.category-item').forEach(c => {
        c.setAttribute('aria-grabbed', 'false');
        c.classList.remove('ms-selected');
    });
    draggedCategory = null;
}

function handleFolderKeydown(e) {
    if (!draggedCategory) return;
    if (e.key !== ' ' && e.key !== 'Enter') return;

    const folderItem = e.currentTarget;
    const folderPath = folderItem.dataset.folderPath;
    const folderName = folderItem.dataset.folderName;
    if (!folderPath || !folderName) return;

    addMapping(draggedCategory, folderPath, folderName);
    e.preventDefault();
}

/**
 * Add a folder mapping
 */
function addMapping(categoryId, folderPath, folderName) {
    currentConfig.folderMappings = currentConfig.folderMappings || {};

    const existing = currentConfig.folderMappings[categoryId];
    if (existing && existing.path === folderPath) {
        const category = window.MS_CONSTANTS?.DEFAULT_CATEGORIES?.find(c => c.id === categoryId);
        showToast(`"${category?.label || categoryId}" is already mapped to "${folderName}"`, 'info');
        return;
    }

    currentConfig.folderMappings[categoryId] = {
        path: folderPath,
        name: folderName
    };
    
    markDirty();
    renderMappings();
    renderMappingVisuals();
    
    const category = window.MS_CONSTANTS?.DEFAULT_CATEGORIES?.find(c => c.id === categoryId);
    showToast(`Mapped "${category?.label || categoryId}" → "${folderName}"`, 'success');

    // Ensure the user sees the newly created mapping
    try {
        const created = elements.mappingsList.querySelector(`.remove-mapping[data-category="${CSS.escape(categoryId)}"]`);
        const row = created?.closest?.('.mapping-item');
        if (row) {
            row.scrollIntoView({ block: 'nearest' });
            row.classList.add('ms-highlight');
            setTimeout(() => row.classList.remove('ms-highlight'), 900);
        }
    } catch (_) {
        // ignore
    }
}

/**
 * Remove a folder mapping
 */
function removeMapping(categoryId) {
    if (currentConfig.folderMappings) {
        delete currentConfig.folderMappings[categoryId];
        markDirty();
        renderMappings();
        renderMappingVisuals();
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
            <li class="ms-list-item mapping-item" data-category="${catId}" style="--ms-category-accent: var(--ms-category-${catId});">
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

    renderMappingVisuals();
}

function renderMappingVisuals() {
    const mappings = currentConfig.folderMappings || {};
    const categories = window.MS_CONSTANTS?.DEFAULT_CATEGORIES || [];

    const knownCategoryIds = new Set(categories.map(c => c.id));
    const catColorVar = (catId) => knownCategoryIds.has(catId) ? `var(--ms-category-${catId})` : 'var(--ms-color-primary)';
    const buildGradient = (catIds) => {
        const unique = Array.from(new Set(catIds.filter(id => knownCategoryIds.has(id))));
        if (unique.length === 0) return null;
        if (unique.length === 1) {
            const c = catColorVar(unique[0]);
            return `linear-gradient(90deg, ${c} 0%, ${c} 100%)`;
        }
        const step = 100 / unique.length;
        const parts = unique.map((id, idx) => {
            const start = (idx * step).toFixed(2);
            const end = ((idx + 1) * step).toFixed(2);
            const c = catColorVar(id);
            return `${c} ${start}%, ${c} ${end}%`;
        });
        return `linear-gradient(90deg, ${parts.join(', ')})`;
    };

    // Category list: mapped stripe + mapped-to label
    if (elements.categoryList) {
        elements.categoryList.querySelectorAll('.category-item').forEach(item => {
            const catId = item.dataset.category;
            const mapping = mappings?.[catId];
            const mappedToEl = item.querySelector('.category-mapped-to');

            if (mapping?.name) {
                item.classList.add('mapped');
                if (mappedToEl) mappedToEl.textContent = `→ ${mapping.name}`;
            } else {
                item.classList.remove('mapped');
                if (mappedToEl) mappedToEl.textContent = '';
            }
        });
    }

    // Folder list: emoji tags for categories mapped to this folder path
    const folderPathToCatIds = new Map();
    Object.entries(mappings).forEach(([catId, folder]) => {
        const path = folder?.path;
        if (!path) return;
        const list = folderPathToCatIds.get(path) || [];
        list.push(catId);
        folderPathToCatIds.set(path, list);
    });

    if (elements.folderList) {
        elements.folderList.querySelectorAll('.folder-item').forEach(item => {
            const folderPath = item.dataset.folderPath;
            const tagsEl = item.querySelector('.folder-tags');
            if (!tagsEl) return;

            const catIds = folderPathToCatIds.get(folderPath) || [];
            const cats = catIds
                .map(id => categories.find(c => c.id === id))
                .filter(Boolean);

            const gradient = buildGradient(catIds);
            if (gradient) {
                item.classList.add('mapped');
                item.style.setProperty('--ms-folder-outline', gradient);
            } else {
                item.classList.remove('mapped');
                item.style.removeProperty('--ms-folder-outline');
            }

            if (cats.length === 0) {
                tagsEl.innerHTML = '';
                tagsEl.setAttribute('aria-label', '');
                return;
            }

            tagsEl.innerHTML = cats
                .map(c => `<span class="folder-tag" data-category="${c.id}" title="${c.label}" aria-label="${c.label}">${c.icon}</span>`)
                .join('');
            tagsEl.setAttribute('aria-label', `Mapped categories: ${cats.map(c => c.label).join(', ')}`);
        });
    }
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

    // UI preference: font mode
    if (elements.fontMode) {
        elements.fontMode.addEventListener('change', async (e) => {
            const mode = e.target.value;
            try {
                await window.MSUiPrefs?.setFontMode?.(mode);
            } catch (_) {
                // ignore
            }
            showToast('Font preference updated', 'success');
        });
    }
    
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

    // Modern settings UX: autosave after a short debounce.
    scheduleAutoSave();
}

function scheduleAutoSave() {
    const delayMs = window.MS_CONSTANTS?.UI?.DEBOUNCE_SAVE_MS || 500;

    if (_autoSaveTimer) {
        clearTimeout(_autoSaveTimer);
        _autoSaveTimer = null;
    }

    _autoSaveTimer = setTimeout(async () => {
        _autoSaveTimer = null;
        if (_autoSaveInProgress) return;
        if (!isDirty) return;
        await saveConfiguration({ silent: true });
    }, delayMs);
}

/**
 * Save configuration to storage
 */
async function saveConfiguration({ silent = false } = {}) {
    setVisible(elements.saveStatus, true);
    elements.saveButton.disabled = true;

    // Cancel any pending autosave; we're saving now.
    if (_autoSaveTimer) {
        clearTimeout(_autoSaveTimer);
        _autoSaveTimer = null;
    }

    _autoSaveInProgress = true;
    
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

        if (!silent) {
            showToast(browser.i18n.getMessage('options_saved') || 'Settings saved successfully', 'success');
            announce('Settings saved');
        }
        
    } catch (e) {
        console.error('[Options] Failed to save:', e);
        if (!silent) {
            showToast('Failed to save settings', 'error');
        }
    } finally {
        setVisible(elements.saveStatus, false);
        elements.saveButton.disabled = false;
        _autoSaveInProgress = false;
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
        } else if (response && response.status === 'degraded') {
            updateConnectionStatus('warning', response);
        } else {
            updateConnectionStatus('disconnected', response);
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
        case 'warning':
            elements.statusDot.classList.add('ms-status-dot-warning');
            elements.statusText.textContent = (details?.provider?.name)
                ? `Connected (${details.provider.name}: degraded)`
                : 'Connected (degraded)';
            break;
        case 'disconnected':
            elements.statusDot.classList.add('ms-status-dot-disconnected');
            elements.statusText.textContent = details?.error
                ? `Disconnected (${details.error})`
                : (browser.i18n.getMessage('status_disconnected') || 'Disconnected');
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
    setVisible(elements.testSpinner, true);
    elements.testConnection.disabled = true;
    setVisible(elements.testResult, false);
    
    try {
        const response = await browser.runtime.sendMessage({ type: 'test-connection' });
        
        setVisible(elements.testResult, true);
        
        const ok = response && (response.status === 'ok' || response.status === 'degraded');
        if (ok) {
            elements.testResult.className = 'test-result test-result-success';
            const providerHealthy = response?.provider?.healthy;
            if (providerHealthy === true) {
                elements.testResult.textContent = browser.i18n.getMessage('options_connection_success') || 
                    'Connection successful! Backend and provider are working.';
            } else if (providerHealthy === false) {
                elements.testResult.textContent = 'Backend reachable, but provider health check failed.';
            } else {
                elements.testResult.textContent = browser.i18n.getMessage('options_connection_success') || 
                    'Connection successful! Backend is reachable.';
            }
            updateConnectionStatus('connected', response);
        } else {
            elements.testResult.className = 'test-result test-result-error';
            elements.testResult.textContent = response?.error
                ? `Connection failed: ${response.error}`
                : (browser.i18n.getMessage('options_connection_failed') || 'Connection failed. Please check your settings.');
            updateConnectionStatus('disconnected', response);
        }
        
    } catch (e) {
        console.error('[Options] Test connection failed:', e);
        setVisible(elements.testResult, true);
        elements.testResult.className = 'test-result test-result-error';
        elements.testResult.textContent = 'Connection test failed: ' + e.message;
        updateConnectionStatus('disconnected');
    } finally {
        setVisible(elements.testSpinner, false);
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
    // One-time global dismiss handlers
    if (!showToast._dismissHandlersAdded) {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                elements.toastContainer?.replaceChildren?.();
            }
        });

        document.addEventListener('pointerdown', (e) => {
            const container = elements.toastContainer;
            if (!container) return;
            if (!container.contains(e.target)) {
                container.replaceChildren?.();
            }
        });

        showToast._dismissHandlersAdded = true;
    }

    const toast = document.createElement('div');
    toast.className = `ms-toast ms-toast-${type}`;
    toast.innerHTML = `
        <div class="ms-toast-content">
            <div class="ms-toast-message">${message}</div>
        </div>
        <button class="ms-toast-close" aria-label="Close" type="button">×</button>
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
