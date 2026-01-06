/**
 * MailSorter Onboarding Wizard (UX-001)
 * First-run setup experience
 */

// State
let currentStep = 0;
const totalSteps = 5; // 0-4
let selectedProvider = 'ollama';
let folderMappings = {};
let testPassed = false;

// DOM Elements
const elements = {};

/**
 * Initialize onboarding
 */
async function init() {
    // Cache elements
    cacheElements();
    
    // Apply translations
    if (window.I18n) {
        window.I18n.translateDocument();
    }
    
    // Load folders for mapping
    await loadFolders();
    
    // Set up event listeners
    setupEventListeners();
    
    // Check if already completed
    const completed = await isOnboardingComplete();
    if (completed) {
        // Redirect to options or close
        console.log('[Onboarding] Already completed');
    }
    
    console.log('[Onboarding] Initialized');
}

/**
 * Cache DOM element references
 */
function cacheElements() {
    elements.steps = document.querySelectorAll('.onboarding-step');
    elements.progressSteps = document.querySelectorAll('.progress-step');
    elements.providerOptions = document.querySelectorAll('.provider-option');
    elements.runTest = document.getElementById('run-test');
    elements.testSpinner = document.getElementById('test-spinner');
    elements.testButtonText = document.getElementById('test-button-text');
    elements.testBackend = document.getElementById('test-backend');
    elements.testLLM = document.getElementById('test-llm');
    elements.testResult = document.getElementById('test-result');
    elements.testSuccess = document.getElementById('test-success');
    elements.testFailure = document.getElementById('test-failure');
    elements.step2Next = document.getElementById('step-2-next');
    elements.mappingSelects = document.querySelectorAll('.mapping-folder');
    elements.summaryProvider = document.getElementById('summary-provider');
    elements.summaryMappings = document.getElementById('summary-mappings');
    elements.openSettings = document.getElementById('open-settings');
    elements.closeOnboarding = document.getElementById('close-onboarding');
    elements.liveRegion = document.getElementById('live-region');
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Navigation buttons
    document.querySelectorAll('.step-next').forEach(btn => {
        btn.addEventListener('click', () => nextStep());
    });
    
    document.querySelectorAll('.step-back').forEach(btn => {
        btn.addEventListener('click', () => prevStep());
    });
    
    document.querySelectorAll('.step-skip').forEach(btn => {
        btn.addEventListener('click', () => nextStep());
    });
    
    // Provider selection
    elements.providerOptions.forEach(option => {
        option.addEventListener('click', () => selectProvider(option));
        
        const radio = option.querySelector('input[type="radio"]');
        radio.addEventListener('change', () => selectProvider(option));
    });
    
    // Test button
    elements.runTest.addEventListener('click', () => runConnectionTest());
    
    // Folder mapping
    elements.mappingSelects.forEach(select => {
        select.addEventListener('change', (e) => {
            const category = e.target.dataset.category;
            folderMappings[category] = e.target.value;
        });
    });
    
    // Complete actions
    elements.openSettings.addEventListener('click', () => {
        browser.runtime.openOptionsPage();
        window.close();
    });
    
    elements.closeOnboarding.addEventListener('click', () => {
        completeOnboarding();
    });
    
    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            // Allow skipping with Escape
        } else if (e.key === 'Enter' && e.target.matches('.step-next, .step-back')) {
            e.target.click();
        }
    });
}

/**
 * Go to next step
 */
function nextStep() {
    if (currentStep < totalSteps - 1) {
        goToStep(currentStep + 1);
    }
}

/**
 * Go to previous step
 */
function prevStep() {
    if (currentStep > 0) {
        goToStep(currentStep - 1);
    }
}

/**
 * Go to a specific step
 */
function goToStep(stepIndex) {
    // Hide current step
    elements.steps[currentStep].hidden = true;
    elements.steps[currentStep].classList.remove('active');
    
    // Update progress indicators
    elements.progressSteps.forEach((step, idx) => {
        step.classList.remove('active', 'completed');
        if (idx < stepIndex) {
            step.classList.add('completed');
        } else if (idx === stepIndex) {
            step.classList.add('active');
        }
    });
    
    // Show new step
    currentStep = stepIndex;
    elements.steps[currentStep].hidden = false;
    elements.steps[currentStep].classList.add('active');
    
    // Focus first focusable element
    const firstFocusable = elements.steps[currentStep].querySelector('button, input, select, [tabindex]');
    if (firstFocusable) {
        firstFocusable.focus();
    }
    
    // Update progress bar aria
    const progressBar = document.querySelector('.onboarding-progress');
    progressBar.setAttribute('aria-valuenow', stepIndex + 1);
    
    // Announce step change
    const heading = elements.steps[currentStep].querySelector('h1');
    if (heading) {
        announce(`Step ${stepIndex + 1} of ${totalSteps - 1}: ${heading.textContent}`);
    }
    
    // Step-specific actions
    if (stepIndex === 4) {
        // Update summary on complete step
        updateSummary();
    }
}

/**
 * Select a provider
 */
function selectProvider(optionElement) {
    // Update UI
    elements.providerOptions.forEach(opt => {
        opt.classList.remove('selected');
        opt.querySelector('input').checked = false;
    });
    
    optionElement.classList.add('selected');
    optionElement.querySelector('input').checked = true;
    
    // Update state
    selectedProvider = optionElement.dataset.provider;
    
    // Reset test results when provider changes
    resetTestResults();
    
    announce(`Selected ${selectedProvider} provider`);
}

/**
 * Reset test results
 */
function resetTestResults() {
    testPassed = false;
    elements.step2Next.disabled = true;
    elements.testResult.hidden = true;
    elements.testSuccess.hidden = true;
    elements.testFailure.hidden = true;
    
    updateTestItem(elements.testBackend, 'waiting');
    updateTestItem(elements.testLLM, 'waiting');
}

/**
 * Run connection test
 */
async function runConnectionTest() {
    elements.runTest.disabled = true;
    elements.testSpinner.hidden = false;
    elements.testButtonText.textContent = 'Testing...';
    elements.testResult.hidden = true;
    
    // Update test items to "testing"
    updateTestItem(elements.testBackend, 'testing');
    updateTestItem(elements.testLLM, 'testing');
    
    try {
        // Test backend connection
        let backendOk = false;
        let llmOk = false;
        
        try {
            const response = await browser.runtime.sendMessage({ type: 'health-check' });
            backendOk = response && response.status === 'ok';
            llmOk = response?.provider?.healthy || false;
        } catch (e) {
            console.warn('[Onboarding] Health check failed:', e);
        }
        
        // Update UI
        updateTestItem(elements.testBackend, backendOk ? 'success' : 'failure');
        
        // Small delay for visual effect
        await new Promise(r => setTimeout(r, 500));
        
        updateTestItem(elements.testLLM, llmOk ? 'success' : 'failure');
        
        // Show result
        elements.testResult.hidden = false;
        
        if (backendOk && llmOk) {
            elements.testSuccess.hidden = false;
            elements.testFailure.hidden = true;
            testPassed = true;
            elements.step2Next.disabled = false;
            announce('Connection test passed');
        } else {
            elements.testSuccess.hidden = true;
            elements.testFailure.hidden = false;
            testPassed = false;
            announce('Connection test failed');
        }
        
    } catch (e) {
        console.error('[Onboarding] Test failed:', e);
        updateTestItem(elements.testBackend, 'failure');
        updateTestItem(elements.testLLM, 'failure');
        elements.testResult.hidden = false;
        elements.testFailure.hidden = false;
        
    } finally {
        elements.runTest.disabled = false;
        elements.testSpinner.hidden = true;
        elements.testButtonText.textContent = 'Run Test';
    }
}

/**
 * Update a test item's status
 */
function updateTestItem(element, status) {
    const icon = element.querySelector('.test-icon');
    const statusText = element.querySelector('.test-status');
    
    element.className = 'test-item test-' + status;
    
    switch (status) {
        case 'waiting':
            icon.textContent = '⏳';
            statusText.textContent = 'Waiting...';
            break;
        case 'testing':
            icon.textContent = '🔄';
            statusText.textContent = 'Testing...';
            break;
        case 'success':
            icon.textContent = '✅';
            statusText.textContent = 'Connected';
            break;
        case 'failure':
            icon.textContent = '❌';
            statusText.textContent = 'Failed';
            break;
    }
}

/**
 * Load available folders
 */
async function loadFolders() {
    try {
        const accounts = await browser.accounts.list();
        let allFolders = [];
        
        for (const account of accounts) {
            const folders = await getAllFolders(account);
            allFolders.push(...folders.map(f => ({
                ...f,
                accountName: account.name,
                displayName: account.name ? `${f.name} (${account.name})` : f.name
            })));
        }
        
        // Filter out system folders
        const systemFolders = window.MS_CONSTANTS?.SYSTEM_FOLDERS || [];
        const userFolders = allFolders.filter(f => !systemFolders.includes(f.name));
        
        // Populate folder selects
        elements.mappingSelects.forEach(select => {
            // Keep the default option
            const defaultOption = select.querySelector('option');
            select.innerHTML = '';
            select.appendChild(defaultOption);
            
            userFolders.forEach(folder => {
                const option = document.createElement('option');
                option.value = folder.path || folder.name;
                option.textContent = folder.displayName || folder.name;
                select.appendChild(option);
            });
        });
        
    } catch (e) {
        console.error('[Onboarding] Failed to load folders:', e);
    }
}

/**
 * Recursively get all folders from an account
 */
async function getAllFolders(account) {
    let allFolders = [];
    
    async function traverse(folder, path = '') {
        const fullPath = path ? `${path}/${folder.name}` : folder.name;
        allFolders.push({ ...folder, path: fullPath });
        
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
 * Update the summary on the complete step
 */
function updateSummary() {
    // Provider
    const providerNames = {
        ollama: 'Ollama (Local)',
        openai: 'OpenAI (GPT-4)',
        anthropic: 'Anthropic (Claude)',
        gemini: 'Google Gemini'
    };
    elements.summaryProvider.textContent = providerNames[selectedProvider] || selectedProvider;
    
    // Mappings
    const mappingCount = Object.values(folderMappings).filter(v => v).length;
    elements.summaryMappings.textContent = mappingCount > 0 
        ? `${mappingCount} categories configured`
        : 'No mappings (using defaults)';
}

/**
 * Complete onboarding and save settings
 */
async function completeOnboarding() {
    try {
        // Save configuration
        const config = {
            provider: selectedProvider,
            analysisMode: 'full',
            passiveMode: false,
            thresholds: { default: 0.7 },
            folderMappings: folderMappings
        };
        
        await browser.storage.local.set({
            config: config,
            onboarding: {
                completed: true,
                completedAt: Date.now()
            }
        });
        
        // Notify background script
        try {
            await browser.runtime.sendMessage({
                type: 'onboarding-complete',
                config: config
            });
        } catch (e) {
            // Background might not be listening
        }
        
        // Close the tab
        window.close();
        
    } catch (e) {
        console.error('[Onboarding] Failed to complete:', e);
        announce('Failed to save settings');
    }
}

/**
 * Check if onboarding was already completed
 */
async function isOnboardingComplete() {
    try {
        const stored = await browser.storage.local.get('onboarding');
        return stored.onboarding?.completed === true;
    } catch (e) {
        return false;
    }
}

/**
 * Announce message to screen readers
 */
function announce(message) {
    if (elements.liveRegion) {
        elements.liveRegion.textContent = message;
        setTimeout(() => {
            elements.liveRegion.textContent = '';
        }, 1000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
