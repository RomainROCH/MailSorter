/*
 * MailSorter Background Script - Plan V5
 * Ce code applique le Plan V5 du projet de tri d emails LLM.
 * Conformite RGPD : Aucune donnee stockee en local storage extension.
 */

const NATIVE_APP_NAME = "com.mailsorter.backend";
const MAX_BODY_LENGTH = 2000; // RGPD: truncate body for privacy

let client = null;
let featureReport = null;
let stateStore = null;
let undoManager = null;
let passiveMode = false;

// ============================================================
// Initialization
// ============================================================

async function initialize() {
    // Run feature detection first
    featureReport = await window.FeatureDetection.logFeatures();
    
    // Initialize state store (Phase 5)
    if (window.StateStore) {
        stateStore = window.StateStore;
        await stateStore.init();
        console.log("[StateStore] Initialized");
    }
    
    // Initialize undo manager (UX-005)
    if (window.UndoManager) {
        undoManager = new window.UndoManager();
        console.log("[UndoManager] Initialized");
    }
    
    // Initialize context menu (UX-003)
    if (window.ContextMenu) {
        window.ContextMenu.init();
        console.log("[ContextMenu] Initialized");
    }
    
    // Initialize keyboard shortcuts (UX-002)
    if (window.KeyboardShortcuts) {
        window.KeyboardShortcuts.init();
        console.log("[KeyboardShortcuts] Initialized");
    }
    
    // Load passive mode setting
    const stored = await browser.storage.local.get('config');
    passiveMode = stored.config?.passiveMode || false;
    
    // Check if onboarding needed
    const onboarding = await browser.storage.local.get('onboarding');
    if (!onboarding.onboarding?.completed) {
        // Open onboarding on first run
        browser.tabs.create({ url: browser.runtime.getURL('onboarding/onboarding.html') });
    }
    
    // Initialize native client
    client = new window.NativeClient(NATIVE_APP_NAME);
    client.connect();
    
    console.log("MailSorter initialized");
}

// Start initialization
initialize();

// ============================================================
// MIME Parsing Utilities (AUDIT-005)
// ============================================================

/**
 * Recursively extract plain text from MIME message parts
 * @param {Object} part - MessagePart object from browser.messages.getFull
 * @returns {string} - Extracted plain text
 */
function extractTextFromPart(part) {
    let text = "";
    
    // Direct body content
    if (part.body) {
        const contentType = (part.contentType || "").toLowerCase();
        
        // Prefer plain text
        if (contentType.includes("text/plain")) {
            text += part.body + "\n";
        } 
        // Fallback: strip HTML tags from text/html
        else if (contentType.includes("text/html")) {
            text += stripHtmlTags(part.body) + "\n";
        }
    }
    
    // Recurse into nested parts (multipart messages)
    if (part.parts && Array.isArray(part.parts)) {
        for (const subPart of part.parts) {
            text += extractTextFromPart(subPart);
        }
    }
    
    return text;
}

/**
 * Strip HTML tags from content (basic implementation)
 * @param {string} html - HTML content
 * @returns {string} - Plain text
 */
function stripHtmlTags(html) {
    if (!html) return "";
    
    // Remove script and style blocks entirely
    let text = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "");
    text = text.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, "");
    
    // Remove HTML tags
    text = text.replace(/<[^>]+>/g, " ");
    
    // Decode common HTML entities
    text = text.replace(/&nbsp;/gi, " ");
    text = text.replace(/&amp;/gi, "&");
    text = text.replace(/&lt;/gi, "<");
    text = text.replace(/&gt;/gi, ">");
    text = text.replace(/&quot;/gi, "\"");
    text = text.replace(/&#39;/gi, "'");
    
    // Collapse whitespace
    text = text.replace(/\s+/g, " ").trim();
    
    return text;
}

/**
 * Extract body text from a message with proper MIME handling
 * @param {number} messageId - Message ID
 * @returns {Promise<string>} - Body text
 */
async function extractBodyText(messageId) {
    // Check if getFull is available
    if (!window.FeatureDetection.supportsGetFull()) {
        window.ErrorHandler.handle(
            "messages.getFull not available - using subject only",
            window.ErrorHandler.SEVERITY.WARNING
        );
        return "";
    }
    
    try {
        const fullMessage = await browser.messages.getFull(messageId);
        
        if (!fullMessage) {
            return "";
        }
        
        // Handle different message structures
        let bodyText = "";
        
        // Modern structure with parts
        if (fullMessage.parts && Array.isArray(fullMessage.parts)) {
            for (const part of fullMessage.parts) {
                bodyText += extractTextFromPart(part);
            }
        }
        // Legacy: direct body property
        else if (fullMessage.body) {
            bodyText = typeof fullMessage.body === "string" 
                ? fullMessage.body 
                : extractTextFromPart(fullMessage);
        }
        
        // Truncate for RGPD compliance
        if (bodyText.length > MAX_BODY_LENGTH) {
            bodyText = bodyText.substring(0, MAX_BODY_LENGTH) + "...";
        }
        
        return bodyText.trim();
        
    } catch (e) {
        window.ErrorHandler.handle(
            "Could not extract body for message " + messageId,
            window.ErrorHandler.SEVERITY.WARNING,
            e
        );
        return "";
    }
}

// ============================================================
// Event Handlers
// ============================================================

// Handle responses from backend
window.addEventListener("native-response", async (e) => {
    const response = e.detail;
    
    if (response.action === "move" && response.target) {
        try {
            // Skip move in passive mode
            if (passiveMode) {
                console.log("[PassiveMode] Would move message " + response.id + " to " + response.target);
                if (stateStore) {
                    stateStore.recordSort({ suggested: true, applied: false });
                }
                return;
            }
            
            await moveMessage(response.id, response.target, { recordUndo: true });
            
            // Record stats
            if (stateStore) {
                stateStore.recordSort({ suggested: true, applied: true });
            }
        } catch (err) {
            window.ErrorHandler.handleMoveError(response.id, response.target, err);
        }
    } else if (response.action === "error") {
        window.ErrorHandler.handleBackendError(
            new Error(response.message || "Unknown backend error"),
            response.context || ""
        );
    }
});

// Listen for messages from popup/options (Phase 5 UI)
browser.runtime.onMessage.addListener(async (message, sender) => {
    switch (message.type) {
        case 'health-check':
            return await handleHealthCheck();
        
        case 'test-connection':
            return await handleTestConnection();
        
        case 'set-passive-mode':
            passiveMode = message.enabled;
            if (stateStore) {
                try {
                    await stateStore.set('config.passiveMode', passiveMode);
                } catch (_) {
                    // ignore
                }
            }
            return { success: true };
        
        case 'get-config':
            const config = await browser.storage.local.get('config');
            return config.config || {};
        
        case 'save-config':
            await browser.storage.local.set({ config: message.config });
            // Apply config changes
            passiveMode = message.config.passiveMode || false;
            return { success: true };
        
        case 'undo-last-action':
            return await handleUndo();
        
        case 'can-undo':
            return { canUndo: undoManager?.canUndo() || false };
        
        case 'get-stats':
            if (stateStore) {
                return stateStore.getStats();
            }
            return { sorted: 0, suggested: 0 };
        
        case 'onboarding-complete':
            // Apply initial config from onboarding
            if (message.config) {
                await browser.storage.local.set({ config: message.config });
                passiveMode = message.config.passiveMode || false;
            }
            return { success: true };
        
        case 'sort-message':
            // Manual sort from context menu or button
            if (message.messageId) {
                try {
                    const msg = await browser.messages.get(message.messageId);
                    await processMessage(msg);
                    return { success: true };
                } catch (e) {
                    return { success: false, error: e.message };
                }
            }
            return { success: false, error: 'No message ID' };
        
        default:
            return { error: 'Unknown message type' };
    }
});

/**
 * Handle health check request
 */
async function handleHealthCheck() {
    const isConnected = client && client.isConnected;
    
    // If connected, do a quick backend ping
    let providerHealthy = false;
    if (isConnected) {
        try {
            // The backend health check would need to be implemented
            providerHealthy = true; // Assume healthy if connected
        } catch (e) {
            providerHealthy = false;
        }
    }
    
    return {
        status: isConnected ? 'ok' : 'error',
        backend: isConnected,
        provider: { healthy: providerHealthy }
    };
}

/**
 * Handle connection test request
 */
async function handleTestConnection() {
    try {
        if (!client || !client.isConnected) {
            client = new window.NativeClient(NATIVE_APP_NAME);
            await client.connect();
        }
        
        // Send a health check to backend
        client.sendMessage({
            type: "health_check",
            payload: {}
        });
        
        // Wait briefly for response
        await new Promise(r => setTimeout(r, 1000));
        
        return {
            success: client.isConnected,
            message: client.isConnected ? 'Connected' : 'Connection failed'
        };
    } catch (e) {
        return {
            success: false,
            message: e.message
        };
    }
}

/**
 * Handle undo request
 */
async function handleUndo() {
    if (!undoManager || !undoManager.canUndo()) {
        return { success: false, error: 'Nothing to undo' };
    }
    
    try {
        await undoManager.undo();
        
        // Update stats
        if (stateStore) {
            const stats = stateStore.getStats();
            stateStore.set('stats', {
                ...stats,
                sorted: Math.max(0, (stats.sorted || 0) - 1)
            });
        }
        
        return { success: true };
    } catch (e) {
        return { success: false, error: e.message };
    }
}

// Listen for new emails
browser.messages.onNewMailReceived.addListener(async (folder, messages) => {
    console.log("New mail received in " + folder.name + ": " + messages.messages.length + " message(s)");
    
    for (let message of messages.messages) {
        // Skip already read messages
        if (message.read) continue;

        try {
            await processMessage(message);
        } catch (err) {
            window.ErrorHandler.handleClassificationError(message.id, err);
        }
    }
});

// ============================================================
// Core Processing
// ============================================================

async function processMessage(messageHeader) {
    // 1. Extract body text with proper MIME parsing
    const bodyText = await extractBodyText(messageHeader.id);

    // 2. Get available folders
    const account = await browser.accounts.get(messageHeader.folder.accountId);
    const folders = await getAllFolders(account);
    const folderNames = folders
        .map(f => f.name)
        .filter(n => !["Inbox", "Trash", "Sent", "Drafts", "Junk", "Templates"].includes(n));

    // 3. Send to backend for classification
    const payload = {
        type: "classify",
        payload: {
            id: messageHeader.id,
            subject: messageHeader.subject || "",
            from: messageHeader.author || "",
            body: bodyText,
            folders: folderNames
        }
    };

    if (!client || !client.isConnected) {
        window.ErrorHandler.handle(
            "Native client not connected, attempting reconnection",
            window.ErrorHandler.SEVERITY.WARNING
        );
        client.connect();
    }
    
    client.sendMessage(payload);
}

async function moveMessage(messageId, targetFolderName, options = {}) {
    const msg = await browser.messages.get(messageId);
    const originalFolder = msg.folder;
    const account = await browser.accounts.get(msg.folder.accountId);
    const folders = await getAllFolders(account);
    
    const targetFolder = folders.find(f => f.name === targetFolderName);
    
    if (targetFolder) {
        console.log("Moving message " + messageId + " to " + targetFolderName);
        await browser.messages.move([messageId], targetFolder);
        
        // Record for undo (UX-005)
        if (options.recordUndo && undoManager) {
            undoManager.recordAction(messageId, originalFolder, targetFolder);
        }
        
        // Show notification
        try {
            browser.notifications.create({
                type: 'basic',
                iconUrl: browser.runtime.getURL('icons/icon-48.png'),
                title: 'Email Sorted',
                message: `Moved to ${targetFolderName}`
            });
        } catch (e) {
            // Notifications may not be available
        }
        
        // Optionally set custom header/tag if supported
        if (window.FeatureDetection.supportsCustomHeaders()) {
            try {
                // Note: The actual API may differ; this is the conceptual approach
                // await browser.messages.update(messageId, { headers: { "X-MailSorter-Category": targetFolderName } });
            } catch (e) {
                // Fallback: use tags if available
                if (window.FeatureDetection.supportsMessageTags()) {
                    // await browser.messages.update(messageId, { tags: ["mailsorter-processed"] });
                }
            }
        }
    } else {
        window.ErrorHandler.handle(
            "Target folder not found: " + targetFolderName,
            window.ErrorHandler.SEVERITY.WARNING
        );
    }
}

// ============================================================
// Helper Functions
// ============================================================

/**
 * Recursively get all folders from an account
 * @param {Object} account - Account object
 * @returns {Promise<Array>} - Array of folder objects
 */
async function getAllFolders(account) {
    let allFolders = [];
    
    async function traverse(folder) {
        allFolders.push(folder);
        if (folder.subFolders && Array.isArray(folder.subFolders)) {
            for (let sub of folder.subFolders) {
                await traverse(sub);
            }
        }
    }

    // Thunderbird/Betterbird compatibility: account.folders is the root
    if (account.folders && Array.isArray(account.folders)) {
        for (let f of account.folders) {
            await traverse(f);
        }
    }
    
    return allFolders;
}
