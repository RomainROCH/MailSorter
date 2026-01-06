/**
 * MailSorter Stats Dashboard (V5-030)
 */

// State
let stats = {
    sorted: 0,
    suggested: 0,
    categories: {},
    daily: {},
    recent: []
};

// DOM Elements
const elements = {};

/**
 * Initialize stats page
 */
async function init() {
    cacheElements();
    
    // Apply translations
    if (window.I18n) {
        window.I18n.translateDocument();
    }
    
    // Load stats
    await loadStats();
    
    // Render UI
    renderStats();
    
    // Set up event listeners
    setupEventListeners();
    
    console.log('[Stats] Initialized');
}

/**
 * Cache DOM element references
 */
function cacheElements() {
    elements.totalSorted = document.getElementById('total-sorted');
    elements.totalSuggested = document.getElementById('total-suggested');
    elements.accuracyRate = document.getElementById('accuracy-rate');
    elements.timeSaved = document.getElementById('time-saved');
    elements.chartBars = document.querySelector('.chart-bars');
    elements.categoryBreakdown = document.getElementById('category-breakdown');
    elements.recentSorts = document.getElementById('recent-sorts');
    elements.exportStats = document.getElementById('export-stats');
    elements.clearStats = document.getElementById('clear-stats');
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    elements.exportStats.addEventListener('click', exportStats);
    elements.clearStats.addEventListener('click', clearStats);
}

/**
 * Load stats from storage
 */
async function loadStats() {
    try {
        const stored = await browser.storage.local.get('mailsorter_stats');
        if (stored.mailsorter_stats) {
            stats = { ...stats, ...stored.mailsorter_stats };
        }
    } catch (e) {
        console.error('[Stats] Failed to load stats:', e);
    }
}

/**
 * Save stats to storage
 */
async function saveStats() {
    try {
        await browser.storage.local.set({ mailsorter_stats: stats });
    } catch (e) {
        console.error('[Stats] Failed to save stats:', e);
    }
}

/**
 * Render all stats UI
 */
function renderStats() {
    renderSummary();
    renderChart();
    renderCategories();
    renderRecent();
}

/**
 * Render summary cards
 */
function renderSummary() {
    elements.totalSorted.textContent = formatNumber(stats.sorted || 0);
    elements.totalSuggested.textContent = formatNumber(stats.suggested || 0);
    
    // Calculate acceptance rate
    const rate = stats.suggested > 0 
        ? Math.round((stats.sorted / stats.suggested) * 100) 
        : 0;
    elements.accuracyRate.textContent = rate + '%';
    
    // Estimate time saved (assume 5 seconds per email)
    const secondsSaved = (stats.sorted || 0) * 5;
    elements.timeSaved.textContent = formatTimeSaved(secondsSaved);
}

/**
 * Render activity chart
 */
function renderChart() {
    // Get last 7 days of data
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const today = new Date();
    const dayValues = [];
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const key = date.toISOString().split('T')[0];
        dayValues.push(stats.daily?.[key] || 0);
    }
    
    const maxValue = Math.max(...dayValues, 1);
    
    // Generate bars
    elements.chartBars.innerHTML = dayValues.map((value, index) => {
        const height = (value / maxValue) * 100;
        return `
            <div class="chart-bar-container">
                <div class="chart-bar" style="height: ${height}%;" 
                     title="${days[index]}: ${value} emails"
                     role="presentation">
                </div>
                <span class="chart-bar-value">${value}</span>
            </div>
        `;
    }).join('');
}

/**
 * Render category breakdown
 */
function renderCategories() {
    const categories = stats.categories || {};
    const entries = Object.entries(categories).sort((a, b) => b[1] - a[1]);
    
    if (entries.length === 0) {
        elements.categoryBreakdown.innerHTML = `
            <div class="category-empty" data-i18n="stats_no_categories">
                No sorting activity yet
            </div>
        `;
        return;
    }
    
    const total = entries.reduce((sum, [, count]) => sum + count, 0);
    
    elements.categoryBreakdown.innerHTML = entries.map(([category, count]) => {
        const percentage = Math.round((count / total) * 100);
        return `
            <div class="category-row">
                <span class="category-name">${escapeHtml(category)}</span>
                <div class="category-bar-container">
                    <div class="category-bar" style="width: ${percentage}%;"></div>
                </div>
                <span class="category-count">${count}</span>
            </div>
        `;
    }).join('');
}

/**
 * Render recent sorts
 */
function renderRecent() {
    const recent = stats.recent || [];
    
    if (recent.length === 0) {
        elements.recentSorts.innerHTML = `
            <div class="recent-empty" data-i18n="stats_no_recent">
                No recent sorting activity
            </div>
        `;
        return;
    }
    
    elements.recentSorts.innerHTML = recent.slice(0, 10).map(item => `
        <div class="recent-item">
            <span class="recent-subject">${escapeHtml(truncate(item.subject, 40))}</span>
            <span class="recent-category">${escapeHtml(item.category)}</span>
            <span class="recent-time">${formatRelativeTime(item.timestamp)}</span>
        </div>
    `).join('');
}

/**
 * Export stats as JSON
 */
function exportStats() {
    const dataStr = JSON.stringify(stats, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `mailsorter-stats-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
    
    announce('Statistics exported');
}

/**
 * Clear all stats
 */
async function clearStats() {
    if (!confirm('Are you sure you want to clear all statistics? This cannot be undone.')) {
        return;
    }
    
    stats = {
        sorted: 0,
        suggested: 0,
        categories: {},
        daily: {},
        recent: []
    };
    
    await saveStats();
    renderStats();
    
    announce('Statistics cleared');
}

// ============================================================
// Utility Functions
// ============================================================

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatTimeSaved(seconds) {
    if (seconds < 60) {
        return seconds + 's';
    } else if (seconds < 3600) {
        return Math.round(seconds / 60) + ' min';
    } else if (seconds < 86400) {
        return (seconds / 3600).toFixed(1) + ' hrs';
    } else {
        return (seconds / 86400).toFixed(1) + ' days';
    }
}

function formatRelativeTime(timestamp) {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    if (seconds < 604800) return Math.floor(seconds / 86400) + 'd ago';
    
    return new Date(timestamp).toLocaleDateString();
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function announce(message) {
    const liveRegion = document.getElementById('live-region');
    if (liveRegion) {
        liveRegion.textContent = message;
        setTimeout(() => {
            liveRegion.textContent = '';
        }, 1000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
