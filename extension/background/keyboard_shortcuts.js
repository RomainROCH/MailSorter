/**
 * MailSorter Keyboard Shortcuts (UX-002)
 * Handles keyboard command registration and execution
 */

const KeyboardShortcuts = {
    /**
     * Initialize keyboard shortcuts
     */
    init() {
        try {
            // Check if commands API is available
            if (!browser.commands) {
                console.warn('[KeyboardShortcuts] browser.commands API not available');
                return;
            }
            
            // Listen for command execution
            browser.commands.onCommand.addListener(this._handleCommand.bind(this));
            
            console.log('[KeyboardShortcuts] Initialized successfully');
            
            // Log registered commands for debugging
            this._logCommands();
            
        } catch (e) {
            console.error('[KeyboardShortcuts] Failed to initialize:', e);
        }
    },
    
    /**
     * Log registered commands
     */
    async _logCommands() {
        try {
            const commands = await browser.commands.getAll();
            console.log('[KeyboardShortcuts] Registered commands:', commands);
        } catch (e) {
            console.warn('[KeyboardShortcuts] Could not get commands:', e);
        }
    },
    
    /**
     * Handle command execution
     * @param {string} command - Command name from manifest
     */
    async _handleCommand(command) {
        console.log('[KeyboardShortcuts] Command triggered:', command);
        
        try {
            switch (command) {
                case 'classify-selected':
                    await this._classifySelectedEmail();
                    break;
                    
                default:
                    console.warn('[KeyboardShortcuts] Unknown command:', command);
            }
        } catch (e) {
            console.error('[KeyboardShortcuts] Error handling command:', e);
            
            if (window.ErrorHandler) {
                window.ErrorHandler.handle(
                    'Keyboard shortcut failed: ' + e.message,
                    window.ErrorHandler.SEVERITY.ERROR,
                    e,
                    true
                );
            }
        }
    },
    
    /**
     * Classify the currently selected email
     */
    async _classifySelectedEmail() {
        // Get the currently displayed/selected message
        let message = null;
        
        try {
            // Try messageDisplay API first (when viewing a message)
            if (browser.messageDisplay) {
                message = await browser.messageDisplay.getDisplayedMessage();
            }
            
            // If no displayed message, try selected messages
            if (!message && browser.mailTabs) {
                const tabs = await browser.mailTabs.query({ active: true, currentWindow: true });
                if (tabs.length > 0) {
                    const selected = await browser.mailTabs.getSelectedMessages(tabs[0].id);
                    if (selected.messages && selected.messages.length > 0) {
                        message = selected.messages[0];
                    }
                }
            }
            
        } catch (e) {
            console.warn('[KeyboardShortcuts] Could not get selected message:', e);
        }
        
        if (!message) {
            // No message selected - show notification
            try {
                browser.notifications.create('mailsorter-no-selection', {
                    type: 'basic',
                    title: 'MailSorter',
                    message: 'Please select an email to classify',
                    iconUrl: 'icons/icon-48.png'
                });
            } catch (e) {
                console.warn('[KeyboardShortcuts] Could not show notification:', e);
            }
            return;
        }
        
        // Check passive mode
        let passiveMode = false;
        if (window.StateStore) {
            passiveMode = window.StateStore.get('config.passiveMode') || false;
        }
        
        // Dispatch classification request
        const event = new CustomEvent('mailsorter-classify-request', {
            detail: {
                messageId: message.id,
                passiveMode: passiveMode
            }
        });
        window.dispatchEvent(event);
        
        console.log('[KeyboardShortcuts] Classification requested for message:', message.id);
    },
    
    /**
     * Update shortcut binding (for options page)
     * @param {string} commandName - Command to update
     * @param {string} shortcut - New shortcut (e.g., "Ctrl+Shift+M")
     * @returns {Promise<boolean>} - Success status
     */
    async updateShortcut(commandName, shortcut) {
        try {
            await browser.commands.update({
                name: commandName,
                shortcut: shortcut
            });
            console.log('[KeyboardShortcuts] Updated shortcut:', commandName, '->', shortcut);
            return true;
        } catch (e) {
            console.error('[KeyboardShortcuts] Failed to update shortcut:', e);
            return false;
        }
    },
    
    /**
     * Reset shortcut to default
     * @param {string} commandName - Command to reset
     * @returns {Promise<boolean>} - Success status
     */
    async resetShortcut(commandName) {
        try {
            await browser.commands.reset(commandName);
            console.log('[KeyboardShortcuts] Reset shortcut:', commandName);
            return true;
        } catch (e) {
            console.error('[KeyboardShortcuts] Failed to reset shortcut:', e);
            return false;
        }
    },
    
    /**
     * Get current shortcut for a command
     * @param {string} commandName - Command name
     * @returns {Promise<string|null>} - Current shortcut or null
     */
    async getShortcut(commandName) {
        try {
            const commands = await browser.commands.getAll();
            const command = commands.find(c => c.name === commandName);
            return command?.shortcut || null;
        } catch (e) {
            console.error('[KeyboardShortcuts] Failed to get shortcut:', e);
            return null;
        }
    }
};

// Export for use in other modules
window.KeyboardShortcuts = KeyboardShortcuts;
