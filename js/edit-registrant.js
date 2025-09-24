// Edit registrant page logic
import { CONFIG } from './config.js';
import { GitHubAPI } from './github-api.js';
import { UIUtils } from './ui-utils.js';
import { DataManager } from './data-manager.js';

class EditRegistrantPage {
    constructor() {
        this.dataManager = new DataManager();
        this.githubAPI = new GitHubAPI();
        this.registrant = null;
        this.registrationId = null;
        this.init();
    }

    async init() {
        // Check for GitHub token
        if (!this.githubAPI.hasValidToken()) {
            UIUtils.showFlashMessage('GitHub token not found. Redirecting to dashboard...', 'error');
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
            return;
        }

        // Get registration ID from URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        this.registrationId = urlParams.get('id');
        
        if (!this.registrationId) {
            UIUtils.showFlashMessage('No registrant ID provided. Redirecting to dashboard...', 'error');
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
            return;
        }

        try {
            // Load registrants data
            await this.dataManager.loadRegistrants();
            
            // Find the registrant
            this.registrant = this.dataManager.getRegistrant(this.registrationId);
            
            if (!this.registrant) {
                throw new Error('Registrant not found');
            }

            // Setup UI
            this.setupEventListeners();
            this.populateForm();
            this.showMainContent();

        } catch (error) {
            console.error('Error loading registrant:', error);
            UIUtils.showFlashMessage('Error loading registrant: ' + error.message, 'error');
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 3000);
        }
    }

    setupEventListeners() {
        const form = document.getElementById('edit-registrant-form');
        form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Show/hide T-shirt size based on parts selection
        const tshirtCheckbox = document.getElementById('part_tshirt');
        tshirtCheckbox.addEventListener('change', () => this.toggleTshirtSize());

        // Toggle revoked status
        document.getElementById('toggle-revoked-btn').addEventListener('click', () => this.toggleRevokedStatus());

        // Student data lookup (if available)
        document.getElementById('roll').addEventListener('blur', () => this.lookupStudentData());
    }

    populateForm() {
        // Basic information
        document.getElementById('name').value = this.registrant.name || '';
        document.getElementById('roll').value = this.registrant.roll || '';
        document.getElementById('gender').value = this.registrant.gender || '';
        document.getElementById('registration_id').value = this.registrant.registration_id || '';

        // Contact information
        document.getElementById('email').value = this.registrant.email || '';
        document.getElementById('phone').value = this.registrant.phone || '';

        // Payment and referral
        document.getElementById('paid').value = this.registrant.paid || 0;
        document.getElementById('referred_by').value = this.registrant.referred_by || '';

        // Photo
        document.getElementById('photo').value = this.registrant.photo || '';

        // Registration date
        if (this.registrant.registration_date) {
            try {
                // Try to parse the date and convert to YYYY-MM-DD format
                const date = new Date(this.registrant.registration_date);
                if (!isNaN(date.getTime())) {
                    document.getElementById('registration_date').value = date.toISOString().split('T')[0];
                } else {
                    // If it's already in a different format, try to parse it
                    const dateStr = this.registrant.registration_date;
                    if (dateStr.includes('/')) {
                        const parts = dateStr.split('/');
                        if (parts.length === 3) {
                            // Assume DD/MM/YYYY format
                            const [day, month, year] = parts;
                            document.getElementById('registration_date').value = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
                        }
                    }
                }
            } catch (e) {
                console.warn('Could not parse registration date:', this.registrant.registration_date);
            }
        }

        // Parts available
        const partsAvailable = this.registrant.parts_available || [];
        document.getElementById('part_tshirt').checked = partsAvailable.includes('T-Shirt');
        document.getElementById('part_food').checked = partsAvailable.includes('Food');
        document.getElementById('part_gift').checked = partsAvailable.includes('Gift');

        // T-shirt size
        document.getElementById('tshirt_size').value = this.registrant.tshirt_size || '';
        this.toggleTshirtSize();

        // Update verification link
        const verificationUrl = UIUtils.getVerificationUrl(this.registrant.registration_id);
        document.getElementById('verification-link').href = verificationUrl;

        // Update revoked status button
        this.updateRevokedButton();
    }

    showMainContent() {
        document.getElementById('loading-indicator').style.display = 'none';
        document.getElementById('main-content').style.display = 'block';
    }

    toggleTshirtSize() {
        const tshirtCheckbox = document.getElementById('part_tshirt');
        const tshirtContainer = document.getElementById('tshirt-size-container');
        
        if (tshirtCheckbox.checked) {
            tshirtContainer.style.display = 'block';
        } else {
            tshirtContainer.style.display = 'none';
            document.getElementById('tshirt_size').value = '';
        }
    }

    updateRevokedButton() {
        const button = document.getElementById('toggle-revoked-btn');
        const text = document.getElementById('revoked-text');
        const isRevoked = this.registrant.revoked;

        if (isRevoked) {
            text.textContent = 'Restore';
            button.className = 'inline-flex items-center px-3 py-2 border border-green-300 text-sm font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100';
        } else {
            text.textContent = 'Revoke';
            button.className = 'inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100';
        }
    }

    async toggleRevokedStatus() {
        const currentStatus = this.registrant.revoked;
        const action = currentStatus ? 'restore' : 'revoke';

        if (!confirm(`Are you sure you want to ${action} ${this.registrant.name}?`)) {
            return;
        }

        try {
            const button = document.getElementById('toggle-revoked-btn');
            button.disabled = true;

            await this.dataManager.updateRegistrant(this.registrationId, {
                revoked: !currentStatus
            });

            this.registrant.revoked = !currentStatus;
            this.updateRevokedButton();

            UIUtils.showFlashMessage(
                `${this.registrant.name} has been ${action}d successfully`,
                'success'
            );

        } catch (error) {
            console.error('Error toggling revoked status:', error);
            UIUtils.showFlashMessage('Failed to update status: ' + error.message, 'error');
        } finally {
            document.getElementById('toggle-revoked-btn').disabled = false;
        }
    }

    async lookupStudentData() {
        const rollInput = document.getElementById('roll');
        const statusDiv = document.getElementById('student-status');
        const roll = rollInput.value.trim();

        if (!roll || roll === this.registrant.roll) {
            statusDiv.textContent = '';
            return;
        }

        try {
            statusDiv.textContent = 'Looking up...';
            statusDiv.className = 'mt-1 text-xs text-blue-600 text-center';

            // This would typically call an API endpoint for student data
            // For now, we'll just clear the status after a brief delay
            setTimeout(() => {
                statusDiv.textContent = '';
            }, 1000);

        } catch (error) {
            console.error('Error looking up student:', error);
            statusDiv.textContent = 'Lookup failed';
            statusDiv.className = 'mt-1 text-xs text-red-600 text-center';
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const form = e.target;
        const formData = new FormData(form);
        
        // Convert form data to object
        const updates = {
            name: formData.get('name')?.trim(),
            roll: formData.get('roll')?.trim(),
            gender: formData.get('gender'),
            email: formData.get('email')?.trim(),
            phone: formData.get('phone')?.trim(),
            paid: parseInt(formData.get('paid')) || 0,
            referred_by: formData.get('referred_by')?.trim(),
            photo: formData.get('photo')?.trim(),
            registration_date: formData.get('registration_date'),
            parts_available: formData.getAll('parts_available'),
            tshirt_size: formData.get('tshirt_size')?.trim()
        };

        // Validation
        if (!updates.name || !updates.roll || !updates.gender) {
            UIUtils.showFlashMessage('Please fill in all required fields (Name, Roll, Gender)', 'error');
            return;
        }

        // Remove T-shirt size if T-shirt is not selected
        if (!updates.parts_available.includes('T-Shirt')) {
            updates.tshirt_size = '';
        }

        try {
            UIUtils.setButtonLoading('submit-btn', true);
            UIUtils.clearFlashMessages();

            // Update the registrant
            const updatedRegistrant = await this.dataManager.updateRegistrant(this.registrationId, updates);
            this.registrant = updatedRegistrant;
            
            UIUtils.showFlashMessage(
                `${updatedRegistrant.name} has been updated successfully!`,
                'success'
            );

            // Redirect after a short delay
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);

        } catch (error) {
            console.error('Error updating registrant:', error);
            UIUtils.showFlashMessage('Failed to update registrant: ' + error.message, 'error');
        } finally {
            UIUtils.setButtonLoading('submit-btn', false, 'Update Registrant');
        }
    }
}

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new EditRegistrantPage();
});