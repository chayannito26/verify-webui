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

            // Calculate total registrants in this group
            const totalInGroup = Object.values(genders).reduce((sum, registrants) => sum + registrants.length, 0);

            const groupElement = document.createElement('div');
            groupElement.className = 'bg-white rounded-lg shadow overflow-hidden mb-8';
            
            let groupHTML = `
                <div class="px-6 py-4 border-b border-gray-200">
                    <h2 class="text-xl font-semibold text-gray-900 flex items-center">
                        <span class="text-2xl mr-3">${groupInfo.emoji}</span>
                        ${groupInfo.name}
                        <span class="ml-2 text-sm font-normal text-gray-500">(${totalInGroup} registrants)</span>
                    </h2>
                </div>
            `;

            for (const [gender, registrants] of Object.entries(genders)) {
                const genderInfo = CONFIG.GENDER_INFO[gender];
                if (!genderInfo) continue;

                groupHTML += `
                    <div class="px-6 py-4 border-b border-gray-100">
                        <h3 class="text-lg font-medium text-gray-800 mb-4 flex items-center">
                            <span class="gender-dot ${gender.toLowerCase()}-dot"></span>
                            ${gender}
                            <span class="ml-2 text-sm font-normal text-gray-500">(${registrants.length})</span>
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                `;

                for (const registrant of registrants) {
                    const verificationUrl = UIUtils.getVerificationUrl(registrant.registration_id);
                    const isRevoked = registrant.revoked;
                    
                    groupHTML += `
                        <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow ${isRevoked ? 'bg-red-50 border-red-200' : ''}">
                            <div class="flex items-start justify-between">
                                <div class="flex-1">
                                    <h4 class="font-medium text-gray-900 ${isRevoked ? 'line-through text-red-600' : ''}">
                                        ${registrant.name}
                                    </h4>
                                    <p class="text-sm text-gray-600">${registrant.roll}</p>
                                    <p class="text-xs font-mono text-gray-500 mt-1">${registrant.registration_id}</p>
                                    
                                    ${registrant.email ? `
                                    <p class="text-xs text-gray-500 mt-1">
                                        <svg class="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                                        </svg>
                                        ${registrant.email}
                                    </p>` : ''}
                                    
                                    ${registrant.phone ? `
                                    <p class="text-xs text-gray-500">
                                        <svg class="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path>
                                        </svg>
                                        ${registrant.phone}
                                    </p>` : ''}

                                    ${registrant.paid ? `
                                    <p class="text-xs text-green-600 font-medium mt-1">
                                        💰 Paid: ৳${registrant.paid}
                                    </p>` : ''}

                                    ${registrant.tshirt_size ? `
                                    <p class="text-xs text-gray-700 mt-1">
                                        👕 Size: <span class="font-medium">${registrant.tshirt_size}</span>
                                    </p>` : ''}

                                    ${isRevoked ? `
                                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 mt-2">
                                        🚫 Revoked
                                    </span>` : ''}
                                </div>

                                <div class="ml-4 flex flex-col space-y-1">
                                    <!-- Verification Link -->
                                    <a href="${verificationUrl}" 
                                       target="_blank" 
                                       rel="noopener noreferrer"
                                       class="inline-flex items-center px-2 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500"
                                       title="View verification page">
                                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                        </svg>
                                        View
                                    </a>

                                    <!-- Edit Link -->
                                    <button onclick="window.app.editRegistrant('${registrant.registration_id}')" 
                                            class="inline-flex items-center px-2 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500">
                                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                        </svg>
                                        Edit
                                    </button>

                                    <!-- Delete Button -->
                                    <button onclick="window.app.deleteRegistrant('${registrant.registration_id}')" 
                                            class="inline-flex items-center px-2 py-1 border border-red-300 text-xs font-medium rounded text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500">
                                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                        </svg>
                                        Delete
                                    </button>
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