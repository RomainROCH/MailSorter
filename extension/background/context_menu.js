/**
 * MailSorter Context Menu Integration (UX-003)
 * Adds right-click menu options for email sorting
 */

const ContextMenu = {
    /**
     * Initialize context menus
     */
    async init() {
        try {
            // Check if menus API is available
            if (!browser.menus) {
                console.warn('[ContextMenu] browser.menus API not available');
                return;
            }
            
            // Remove existing menus first (in case of reload)
            await browser.menus.removeAll();
            
            // Create "Sort with MailSorter" menu item for messages
            await browser.menus.create({
                id: window.MS_CONSTANTS?.MENU_IDS?.SORT_EMAIL || 'mailsorter-sort-email',
                title: browser.i18n.getMessage('context_menu_sort') || 'Sort with MailSorter',
                contexts: ['message_list'],
                icons: {
                    "16": "icons/icon-16.png",
                    "32": "icons/icon-32.png"
                }
            });
            
            // Create menu item for multiple selected messages
            await browser.menus.create({
                id: window.MS_CONSTANTS?.MENU_IDS?.SORT_SELECTION || 'mailsorter-sort-selection',
                title: browser.i18n.getMessage('context_menu_sort_selection') || 'Sort selected emails',
                contexts: ['message_list'],
                icons: {
                    "16": "icons/icon-16.png",
                    "32": "icons/icon-32.png"
                }
            });
            
            // Listen for menu clicks
            browser.menus.onClicked.addListener(this._handleMenuClick.bind(this));
            
            console.log('[ContextMenu] Initialized successfully');
            
        } catch (e) {
            console.error('[ContextMenu] Failed to initialize:', e);
        }
    },
    
    /**
     * Handle context menu click
     * @param {object} info - Menu click info
     * @param {object} tab - Tab info (not used in Thunderbird)
     */
    async _handleMenuClick(info, tab) {
        const menuId = info.menuItemId;
        
        try {
            // Get selected messages
            const selectedMessages = await this._getSelectedMessages();
            
            if (!selectedMessages || selectedMessages.length === 0) {
                console.warn('[ContextMenu] No messages selected');
                return;
            }
            
            // Check passive mode
            const passiveMode = await this._isPassiveMode();
            
            if (menuId === 'mailsorter-sort-email') {
                // Sort single message (first selected)
                await this._sortMessage(selectedMessages[0], passiveMode);
                
            } else if (menuId === 'mailsorter-sort-selection') {
                // Sort all selected messages
                await this._sortMultipleMessages(selectedMessages, passiveMode);
            }
            
        } catch (e) {
            console.error('[ContextMenu] Error handling menu click:', e);
            
            if (window.ErrorHandler) {
                window.ErrorHandler.handle(
                    'Failed to sort email: ' + e.message,
                    window.ErrorHandler.SEVERITY.ERROR,
                    e,
                    true
                );
            }
        }
    },
    
    /**
     * Get currently selected messages
     * @returns {Promise<Array>}
     */
    async _getSelectedMessages() {
        try {
            // mailTabs API gives us the current tab's selected messages
            if (browser.mailTabs) {
                const tabs = await browser.mailTabs.query({ active: true, currentWindow: true });
                if (tabs.length > 0) {
                    const messages = await browser.mailTabs.getSelectedMessages(tabs[0].id);
                    return messages.messages || [];
                }
            }
            
            // Fallback: try to get from current message
            if (browser.messageDisplay) {
                const displayed = await browser.messageDisplay.getDisplayedMessage();
                if (displayed) {
                    return [displayed];
                }
            }
            
            return [];
            
        } catch (e) {
            console.error('[ContextMenu] Error getting selected messages:', e);
            return [];
        }
    },
    
    /**
     * Check if passive mode is enabled
     * @returns {Promise<boolean>}
     */
    async _isPassiveMode() {
        if (window.StateStore) {
            return window.StateStore.get('config.passiveMode') || false;
        }
        return false;
    },
    
    /**
     * Sort a single message
     * @param {object} message - Message header
     * @param {boolean} passiveMode - Whether to only classify without moving
     */
    async _sortMessage(message, passiveMode) {
        // Update processing state
        if (window.StateStore) {
            await window.StateStore.set('processing.active', true);
            await window.StateStore.set('processing.currentEmail', message.id);
        }
        
        try {
            // Dispatch to background.js processMessage function
            // We emit an event that background.js listens for
            const event = new CustomEvent('mailsorter-classify-request', {
                detail: {
                    messageId: message.id,
                    passiveMode: passiveMode
                }
            });
            window.dispatchEvent(event);
            
        } finally {
            // Processing state will be cleared by the response handler
        }
    },
    
    /**
     * Sort multiple messages (UX-006: Bulk archive sorting)
     * @param {Array} messages - Array of message headers
     * @param {boolean} passiveMode - Whether to only classify without moving
     */
    async _sortMultipleMessages(messages, passiveMode) {
        const total = messages.length;
        let processed = 0;
        
        // Update processing state
        if (window.StateStore) {
            await window.StateStore.set('processing.active', true);
            await window.StateStore.set('processing.queue', messages.map(m => m.id));
        }
        
        // Show progress notification
        this._showProgressNotification(processed, total);
        
        try {
            for (const message of messages) {
                // Check if cancelled
                if (window.StateStore) {
                    const queue = window.StateStore.get('processing.queue');
                    if (!queue || queue.length === 0) {
                        console.log('[ContextMenu] Bulk sort cancelled');
                        break;
                    }
                }
                
                await this._sortMessage(message, passiveMode);
                processed++;
                
                // Update progress
                this._showProgressNotification(processed, total);
                
                // Small delay to avoid overwhelming the LLM
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            // Show completion notification
            this._showCompletionNotification(processed);
            
        } finally {
            if (window.StateStore) {
                await window.StateStore.set('processing.active', false);
                await window.StateStore.set('processing.queue', []);
            }
        }
    },
    
    /**
     * Show progress notification for bulk sort
     * @param {number} current - Current count
     * @param {number} total - Total count
     */
    _showProgressNotification(current, total) {
        try {
            const message = browser.i18n.getMessage('bulk_progress_count', [String(current), String(total)])
                || `${current} of ${total} emails`;
            
            browser.notifications.create('mailsorter-bulk-progress', {
                type: 'basic',
                title: browser.i18n.getMessage('bulk_progress_title') || 'Sorting emails...',
                message: message,
                iconUrl: 'icons/icon-48.png'
            });
        } catch (e) {
            console.warn('[ContextMenu] Could not show progress notification:', e);
        }
    },
    
    /**
     * Show completion notification
     * @param {number} count - Number of emails sorted
     */
    _showCompletionNotification(count) {
        try {
            const message = browser.i18n.getMessage('bulk_complete', [String(count)])
                || `Sorted ${count} emails`;
            
            browser.notifications.create('mailsorter-bulk-complete', {
                type: 'basic',
                title: 'MailSorter',
                message: message,
                iconUrl: 'icons/icon-48.png'
            });
        } catch (e) {
            console.warn('[ContextMenu] Could not show completion notification:', e);
        }
    },
    
    /**
     * Cancel ongoing bulk sort
     */
    async cancelBulkSort() {
        if (window.StateStore) {
            await window.StateStore.set('processing.queue', []);
        }
    }
};

// Export for use in other modules
window.ContextMenu = ContextMenu;
