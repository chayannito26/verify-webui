// Add registrant page logic
import { CONFIG } from './config.js';
import { GitHubAPI } from './github-api.js';
import { UIUtils } from './ui-utils.js';
import { DataManager } from './data-manager.js';

class AddRegistrantPage {
    constructor() {
        this.dataManager = new DataManager();
        this.githubAPI = new GitHubAPI();
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

        // Setup event listeners
        this.setupEventListeners();
        
        // Set default registration date
        document.getElementById('registration_date').value = this.getCurrentDate();

        try {
            // Load existing registrants for ID generation
            await this.dataManager.loadRegistrants();
        } catch (error) {
            console.error('Error loading registrants:', error);
            UIUtils.showFlashMessage('Warning: Could not load existing data. ' + error.message, 'error');
        }
    }

    setupEventListeners() {
        const form = document.getElementById('add-registrant-form');
        form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Auto-generate registration ID when group or gender changes
        document.getElementById('group').addEventListener('change', () => this.updateRegistrationId());
        document.getElementById('gender').addEventListener('change', () => this.updateRegistrationId());

        // Auto-infer group from roll number
        document.getElementById('roll').addEventListener('input', () => this.updateGroupFromRoll());

        // Show/hide T-shirt size based on parts selection
        const tshirtCheckbox = document.getElementById('part_tshirt');
        tshirtCheckbox.addEventListener('change', () => this.toggleTshirtSize());

        // Student data lookup (if available)
        document.getElementById('roll').addEventListener('blur', () => this.lookupStudentData());
    }

    getCurrentDate() {
        const now = new Date();
        return now.toISOString().split('T')[0];
    }

    updateRegistrationId() {
        const group = document.getElementById('group').value;
        const gender = document.getElementById('gender').value;
        const registrationIdInput = document.getElementById('registration_id');

        if (group && gender) {
            const registrants = this.dataManager.getRegistrants();
            const nextId = UIUtils.getNextRegistrationId(registrants, group, gender);
            registrationIdInput.value = nextId;
        } else {
            registrationIdInput.value = '';
        }
    }

    updateGroupFromRoll() {
        const rollInput = document.getElementById('roll');
        const groupSelect = document.getElementById('group');
        const roll = rollInput.value.trim();

        // Auto-infer group from roll number pattern
        if (roll && roll.length >= 10) {
            let inferredGroup = '';
            if (roll.startsWith('1202425')) {
                const code = roll.substring(7);
                if (code.startsWith('01') && !code.startsWith('013')) {
                    inferredGroup = 'SC'; // Science
                } else if (code.startsWith('02')) {
                    inferredGroup = 'AR'; // Arts
                } else if (code.startsWith('03')) {
                    inferredGroup = 'CO'; // Commerce
                }
            }

            if (inferredGroup && !groupSelect.value) {
                groupSelect.value = inferredGroup;
                this.updateRegistrationId();
            }
        }
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

    async lookupStudentData() {
        const rollInput = document.getElementById('roll');
        const statusDiv = document.getElementById('student-status');
        const roll = rollInput.value.trim();

        if (!roll) {
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
        const registrantData = {
            name: formData.get('name')?.trim(),
            roll: formData.get('roll')?.trim(),
            gender: formData.get('gender'),
            group: formData.get('group'),
            email: formData.get('email')?.trim(),
            phone: formData.get('phone')?.trim(),
            paid: parseInt(formData.get('paid')) || 0,
            referred_by: formData.get('referred_by')?.trim(),
            photo: formData.get('photo')?.trim(),
            registration_date: formData.get('registration_date'),
            registration_id: formData.get('registration_id')?.trim(),
            parts_available: formData.getAll('parts_available'),
            tshirt_size: formData.get('tshirt_size')?.trim()
        };

        // Validation
        if (!registrantData.name || !registrantData.roll || !registrantData.gender || !registrantData.group) {
            UIUtils.showFlashMessage('Please fill in all required fields (Name, Roll, Gender, Group)', 'error');
            return;
        }

        // Remove T-shirt size if T-shirt is not selected
        if (!registrantData.parts_available.includes('T-Shirt')) {
            registrantData.tshirt_size = '';
        }

        try {
            UIUtils.setButtonLoading('submit-btn', true);
            UIUtils.clearFlashMessages();

            // Add the registrant
            const newRegistrant = await this.dataManager.addRegistrant(registrantData);
            
            UIUtils.showFlashMessage(
                `${newRegistrant.name} has been added successfully! Registration ID: ${newRegistrant.registration_id}`,
                'success'
            );

            // Reset form and redirect after a short delay
            form.reset();
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);

        } catch (error) {
            console.error('Error adding registrant:', error);
            UIUtils.showFlashMessage('Failed to add registrant: ' + error.message, 'error');
        } finally {
            UIUtils.setButtonLoading('submit-btn', false, 'Add Registrant');
        }
    }
}

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AddRegistrantPage();
});