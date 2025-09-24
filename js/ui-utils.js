// UI utility functions for managing interface elements
import { CONFIG } from './config.js';

export class UIUtils {
    // Show flash message
    static showFlashMessage(message, type = 'info') {
        const container = document.getElementById('flash-messages');
        if (!container) return;

        const messageId = `flash-${Date.now()}`;
        const bgColor = type === 'error' ? 'bg-red-50 border-red-200 text-red-700' :
                       type === 'success' ? 'bg-green-50 border-green-200 text-green-700' :
                       'bg-blue-50 border-blue-200 text-blue-700';
        
        const iconColor = type === 'error' ? 'text-red-400' :
                         type === 'success' ? 'text-green-400' :
                         'text-blue-400';

        const icon = type === 'error' ? 
            `<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>` :
            type === 'success' ?
            `<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>` :
            `<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>`;

        const messageElement = document.createElement('div');
        messageElement.id = messageId;
        messageElement.className = `flash-message mb-4 p-4 rounded-md ${bgColor}`;
        messageElement.innerHTML = `
            <div class="flex">
                <div class="flex-shrink-0">
                    <svg class="h-5 w-5 ${iconColor}" fill="currentColor" viewBox="0 0 20 20">
                        ${icon}
                    </svg>
                </div>
                <div class="ml-3">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <div class="ml-auto pl-3">
                    <button onclick="document.getElementById('${messageId}').remove()" class="text-sm ${iconColor} hover:opacity-75">
                        ×
                    </button>
                </div>
            </div>
        `;

        container.appendChild(messageElement);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            const element = document.getElementById(messageId);
            if (element) {
                element.style.transition = 'opacity 0.5s';
                element.style.opacity = '0';
                setTimeout(() => element.remove(), 500);
            }
        }, 5000);
    }

    // Clear all flash messages
    static clearFlashMessages() {
        const container = document.getElementById('flash-messages');
        if (container) {
            container.innerHTML = '';
        }
    }

    // Show/hide loading indicator
    static showLoading(show = true) {
        const indicator = document.getElementById('loading-indicator');
        if (indicator) {
            indicator.style.display = show ? 'flex' : 'none';
        }
    }

    // Update statistics
    static updateStats(stats) {
        document.getElementById('total-registrants').textContent = stats.total || 0;
        document.getElementById('active-registrants').textContent = stats.active || 0;
        document.getElementById('revoked-registrants').textContent = stats.revoked || 0;
        document.getElementById('total-payments').textContent = stats.total_payments || 0;
    }

    // Generate verification URL (from original Flask app logic)
    static getVerificationUrl(registrationId) {
        const filename = this.idToFilename(registrationId);
        return `${CONFIG.VERIFICATION_BASE_URL}/${filename}.html`;
    }

    // Convert registration ID to filename (from original Flask app)
    static idToFilename(regId) {
        // Base64 encode
        const b64 = btoa(regId).replace(/=/g, '');
        // ROT13 encode
        const rot = b64.replace(/[a-zA-Z]/g, function(c) {
            return String.fromCharCode((c <= 'Z' ? 90 : 122) >= (c = c.charCodeAt(0) + 13) ? c : c - 26);
        });
        // Reverse
        return rot.split('').reverse().join('');
    }

    // Generate next registration ID
    static getNextRegistrationId(registrants, group, gender) {
        const genderShort = CONFIG.GENDER_INFO[gender]?.short || 'B';
        const prefix = `${group}-${genderShort}-`;
        
        // Find existing IDs with this prefix
        const existingNumbers = [];
        for (const reg of registrants) {
            const regId = reg.registration_id || '';
            if (regId.startsWith(prefix)) {
                try {
                    const number = parseInt(regId.split('-').pop());
                    if (!isNaN(number)) {
                        existingNumbers.push(number);
                    }
                } catch (e) {
                    // Ignore invalid IDs
                }
            }
        }
        
        // Get next number
        const nextNumber = existingNumbers.length > 0 ? Math.max(...existingNumbers) + 1 : 1;
        return `${prefix}${nextNumber.toString().padStart(4, '0')}`;
    }

    // Group registrants by group and gender
    static groupRegistrants(registrants) {
        const grouped = {};
        
        for (const registrant of registrants) {
            const regId = registrant.registration_id || '';
            if (!regId) continue;
            
            // Extract group from registration ID
            const parts = regId.split('-');
            if (parts.length >= 2) {
                const group = parts[0];
                const genderShort = parts[1];
                
                // Convert gender short to full name
                let gender = null;
                for (const [g, info] of Object.entries(CONFIG.GENDER_INFO)) {
                    if (info.short === genderShort) {
                        gender = g;
                        break;
                    }
                }
                
                if (group in CONFIG.GROUP_INFO && gender) {
                    if (!grouped[group]) {
                        grouped[group] = {};
                    }
                    if (!grouped[group][gender]) {
                        grouped[group][gender] = [];
                    }
                    
                    grouped[group][gender].push(registrant);
                }
            }
        }
        
        return grouped;
    }

    // Calculate statistics
    static calculateStats(registrants) {
        const total = registrants.length;
        const active = registrants.filter(r => !r.revoked).length;
        const revoked = total - active;
        const totalPayments = registrants.reduce((sum, r) => sum + (r.paid || 0), 0);
        
        return {
            total,
            active,
            revoked,
            total_payments: totalPayments
        };
    }

    // Format date for display
    static formatDate(dateString) {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        } catch (e) {
            return dateString;
        }
    }

    // Show modal
    static showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    // Hide modal
    static hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    // Set button loading state
    static setButtonLoading(buttonId, loading = true, originalText = null) {
        const button = document.getElementById(buttonId);
        if (!button) return;

        if (loading) {
            button.disabled = true;
            button.dataset.originalText = button.textContent;
            button.innerHTML = `
                <div class="loading-spinner mr-2"></div>
                Loading...
            `;
        } else {
            button.disabled = false;
            button.textContent = originalText || button.dataset.originalText || 'Submit';
        }
    }
}