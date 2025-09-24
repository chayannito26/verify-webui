// Main application logic
import { CONFIG } from './config.js';
import { GitHubAPI } from './github-api.js';
import { UIUtils } from './ui-utils.js';
import { DataManager } from './data-manager.js';

class App {
    constructor() {
        this.dataManager = new DataManager();
        this.githubAPI = new GitHubAPI();
        this.currentPage = 'dashboard';
        this.init();
    }

    async init() {
        console.log('Initializing Chayannito 26 Management App...');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Check for GitHub token
        if (!this.githubAPI.hasValidToken()) {
            this.showTokenModal();
        } else {
            await this.loadDashboard();
        }
    }

    setupEventListeners() {
        // Token modal
        document.getElementById('save-token').addEventListener('click', () => this.saveToken());
        document.getElementById('github-token').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.saveToken();
        });

        // Navigation
        document.getElementById('add-registrant-btn').addEventListener('click', () => this.showAddRegistrantForm());
        document.getElementById('sync-github-btn').addEventListener('click', () => this.syncWithGitHub());
        document.getElementById('settings-btn').addEventListener('click', () => this.showSettings());

        // Close modal when clicking outside
        document.getElementById('token-modal').addEventListener('click', (e) => {
            if (e.target.id === 'token-modal') {
                // Don't allow closing if no token is set
                if (this.githubAPI.hasValidToken()) {
                    UIUtils.hideModal('token-modal');
                }
            }
        });
    }

    showTokenModal() {
        UIUtils.showModal('token-modal');
        document.getElementById('github-token').focus();
    }

    async saveToken() {
        const tokenInput = document.getElementById('github-token');
        const token = tokenInput.value.trim();
        
        if (!token) {
            UIUtils.showFlashMessage('Please enter a GitHub token', 'error');
            return;
        }

        UIUtils.setButtonLoading('save-token', true);

        try {
            // Test the token
            this.githubAPI.setToken(token);
            const isValid = await this.githubAPI.testToken();
            
            if (!isValid) {
                throw new Error('Invalid token or insufficient permissions');
            }

            UIUtils.hideModal('token-modal');
            UIUtils.showFlashMessage('GitHub token saved successfully!', 'success');
            
            // Load dashboard
            await this.loadDashboard();
            
        } catch (error) {
            console.error('Token validation error:', error);
            UIUtils.showFlashMessage('Failed to validate token: ' + error.message, 'error');
            this.githubAPI.removeToken();
        } finally {
            UIUtils.setButtonLoading('save-token', false, 'Save Token');
        }
    }

    async loadDashboard() {
        try {
            UIUtils.showLoading(true);
            UIUtils.clearFlashMessages();

            // Load registrants data
            await this.dataManager.loadRegistrants();
            
            // Update UI
            this.renderDashboard();
            
        } catch (error) {
            console.error('Error loading dashboard:', error);
            UIUtils.showFlashMessage('Error loading data: ' + error.message, 'error');
            
            if (error.message.includes('Invalid GitHub token')) {
                this.githubAPI.removeToken();
                this.showTokenModal();
            }
        } finally {
            UIUtils.showLoading(false);
        }
    }

    renderDashboard() {
        const registrants = this.dataManager.getRegistrants();
        const grouped = this.dataManager.getGroupedRegistrants();
        const stats = this.dataManager.getStatistics();

        // Update statistics
        UIUtils.updateStats(stats);

        // Render registrants groups
        this.renderRegistrantsGroups(grouped);
    }

    renderRegistrantsGroups(grouped) {
        const container = document.getElementById('registrants-container');
        container.innerHTML = '';

        if (Object.keys(grouped).length === 0) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                    <h3 class="mt-2 text-sm font-medium text-gray-900">No registrants</h3>
                    <p class="mt-1 text-sm text-gray-500">Get started by adding a new registrant.</p>
                    <div class="mt-6">
                        <button onclick="window.app.showAddRegistrantForm()" class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-emerald-600 hover:bg-emerald-700">
                            <svg class="-ml-1 mr-2 h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"></path>
                            </svg>
                            Add Registrant
                        </button>
                    </div>
                </div>
            `;
            return;
        }

        // Render groups
        for (const [groupCode, genders] of Object.entries(grouped)) {
            const groupInfo = CONFIG.GROUP_INFO[groupCode];
            if (!groupInfo) continue;

            const groupElement = document.createElement('div');
            groupElement.className = 'bg-white rounded-lg shadow overflow-hidden';
            
            let groupHTML = `
                <div class="bg-gray-50 px-6 py-4 border-b border-gray-200">
                    <h2 class="text-lg font-medium text-gray-900 flex items-center">
                        <span class="mr-2">${groupInfo.emoji}</span>
                        ${groupInfo.name} (${groupCode})
                    </h2>
                </div>
            `;

            for (const [gender, registrants] of Object.entries(genders)) {
                const genderInfo = CONFIG.GENDER_INFO[gender];
                if (!genderInfo) continue;

                groupHTML += `
                    <div class="px-6 py-4">
                        <h3 class="text-md font-medium text-gray-800 mb-4 flex items-center">
                            <span class="gender-dot ${gender.toLowerCase()}-dot"></span>
                            ${gender} (${registrants.length})
                        </h3>
                        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                `;

                for (const registrant of registrants) {
                    const verificationUrl = UIUtils.getVerificationUrl(registrant.registration_id);
                    const isRevoked = registrant.revoked;
                    
                    groupHTML += `
                        <div class="bg-gray-50 rounded-lg p-4 ${isRevoked ? 'opacity-60' : ''}">
                            <div class="flex items-start justify-between">
                                <div class="flex-1 min-w-0">
                                    <h4 class="text-sm font-medium text-gray-900 truncate">
                                        ${registrant.name}
                                        ${isRevoked ? '<span class="text-red-500 text-xs ml-1">(Revoked)</span>' : ''}
                                    </h4>
                                    <p class="text-xs text-gray-500 mt-1">
                                        ID: ${registrant.registration_id}
                                    </p>
                                    <p class="text-xs text-gray-500">
                                        Roll: ${registrant.roll}
                                    </p>
                                    ${registrant.paid ? `<p class="text-xs text-green-600 font-medium">Paid: ৳${registrant.paid}</p>` : ''}
                                </div>
                                <div class="flex-shrink-0 ml-2">
                                    <div class="flex items-center space-x-1">
                                        <button onclick="window.app.editRegistrant('${registrant.registration_id}')" 
                                                class="text-blue-600 hover:text-blue-800 text-xs">
                                            Edit
                                        </button>
                                        <span class="text-gray-300">|</span>
                                        <a href="${verificationUrl}" target="_blank" 
                                           class="text-emerald-600 hover:text-emerald-800 text-xs">
                                            View
                                        </a>
                                        <span class="text-gray-300">|</span>
                                        <button onclick="window.app.deleteRegistrant('${registrant.registration_id}')" 
                                                class="text-red-600 hover:text-red-800 text-xs">
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }

                groupHTML += `
                        </div>
                    </div>
                `;
            }

            groupElement.innerHTML = groupHTML;
            container.appendChild(groupElement);
        }
    }

    async syncWithGitHub() {
        const syncBtn = document.getElementById('sync-github-btn');
        const syncText = document.getElementById('sync-text');
        
        try {
            syncBtn.disabled = true;
            syncText.textContent = 'Syncing...';
            
            // Force refresh from GitHub
            await this.dataManager.loadRegistrants(true);
            this.renderDashboard();
            
            UIUtils.showFlashMessage('Successfully synced with GitHub!', 'success');
        } catch (error) {
            console.error('Sync error:', error);
            UIUtils.showFlashMessage('Sync failed: ' + error.message, 'error');
        } finally {
            syncBtn.disabled = false;
            syncText.textContent = 'Sync';
        }
    }

    showAddRegistrantForm() {
        // Navigate to add.html
        window.location.href = 'add.html';
    }

    editRegistrant(registrationId) {
        // Navigate to edit.html with ID parameter
        window.location.href = `edit.html?id=${encodeURIComponent(registrationId)}`;
    }

    async deleteRegistrant(registrationId) {
        const registrant = this.dataManager.getRegistrant(registrationId);
        if (!registrant) {
            UIUtils.showFlashMessage('Registrant not found', 'error');
            return;
        }

        if (!confirm(`Are you sure you want to delete ${registrant.name} (${registrationId})?`)) {
            return;
        }

        try {
            await this.dataManager.deleteRegistrant(registrationId);
            UIUtils.showFlashMessage(`${registrant.name} has been deleted successfully`, 'success');
            this.renderDashboard();
        } catch (error) {
            console.error('Delete error:', error);
            UIUtils.showFlashMessage('Failed to delete registrant: ' + error.message, 'error');
        }
    }

    showSettings() {
        const currentToken = this.githubAPI.token;
        const maskedToken = currentToken ? currentToken.substring(0, 8) + '...' : 'Not set';
        
        if (confirm(`Current GitHub token: ${maskedToken}\n\nClick OK to change the token, or Cancel to keep the current one.`)) {
            // Clear current token and show modal
            document.getElementById('github-token').value = '';
            this.showTokenModal();
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});

// Export for global access
window.App = App;