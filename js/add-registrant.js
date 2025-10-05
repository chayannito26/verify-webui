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

        // Import-from-text parsing (if UI exists on page)
        const importTextarea = document.getElementById('import_text');
        const parseBtn = document.getElementById('parse-text-btn');
        const clearBtn = document.getElementById('clear-import-btn');
        const importFeedback = document.getElementById('import-feedback');

        if (parseBtn && importTextarea) {
            parseBtn.addEventListener('click', () => this.handleParse(importTextarea, importFeedback));
        }
        if (clearBtn && importTextarea) {
            clearBtn.addEventListener('click', () => {
                importTextarea.value = '';
                if (importFeedback) importFeedback.textContent = '';
            });
        }
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

    // --- Parsing helpers ---
    findEmail(text) {
        const re = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/gi;
        const m = text.match(re);
        return m ? m[0].trim() : '';
    }

    findPhone(text) {
        const candidates = text.match(/[0-9\-+\s]{6,20}/g) || [];
        for (const c of candidates) {
            let digits = c.replace(/[^0-9]/g, '');
            if (digits.startsWith('88')) digits = digits.slice(2);
            if (digits.length === 11) return digits;
        }
        const run = text.match(/\b(\d{11})\b/);
        return run ? run[1] : '';
    }

    findTshirtSize(text) {
        const sizes = ['XS','S','M','L','XL','XXL','2XL','3XL','4XL'];
        const re = new RegExp("\\b(" + sizes.join('|') + ")\\b", 'i');
        const m = text.match(re);
        return m ? m[1].toUpperCase().replace(/^2XL$/,'XXL') : '';
    }

    detectGroupFromText(text) {
        const t = text.toLowerCase();
        if (t.includes('science') || t.includes('sc') || t.includes('sci')) return 'SC';
        if (t.includes('arts') || t.includes('art')) return 'AR';
        if (t.includes('commerce') || t.includes('com')) return 'CO';
        return '';
    }

    findRoll(text) {
        // Prefer longer roll patterns first (13 -> 5 -> 3). Also accept common labels like "roll", "roll no", "roll number".
        const labeled = text.match(/roll(?:\s*(?:no|number))?[:\-\s]*?(\d{13}|\d{5}|\d{3})/i);
        if (labeled) return labeled[1];
        const m13 = text.match(/\b(\d{13})\b/);
        if (m13) return m13[1];
        const m5 = text.match(/\b(\d{5})\b/);
        if (m5) return m5[1];
        const m3 = text.match(/\b(\d{3})\b/);
        if (m3) return m3[1];
        return '';
    }

    normalizeRoll(rawRoll) {
        if (!rawRoll) return '';
        if (rawRoll.length === 13) return rawRoll;
        if (rawRoll.length === 5) return '12024250' + rawRoll;
        // For 3-digit we return raw; do not auto-prefix here
        if (rawRoll.length === 3) return rawRoll;
        return rawRoll;
    }

    inferGroupFromRoll(roll) {
        if (!roll || roll.length < 10) return '';
        let code = '';
        if (roll.startsWith('1202425')) {
            code = roll.substring(8);
            if (code.startsWith('1') && !code.startsWith('13')) return 'SC';
            if (code.startsWith('2')) return 'AR';
            if (code.startsWith('3')) return 'CO';
        }
        return '';
    }

    findName(lines, usedPatterns) {
        // Words that indicate the line is a label rather than part of the actual name
        const ignoreWords = ['name', 'roll', 'mail', 'email', 'serial', 'tshirt', 'number', 'phone'];

        for (const l of lines) {
            if (!l) continue;
            let s = l.trim();
            if (!s) continue;

            const lowOrig = s.toLowerCase();
            if (lowOrig === 'you sent' || lowOrig.startsWith('you sent ')) continue;

            // If the line contains a colon, assume it's a label like "Name: John Doe" and take the part after the first colon.
            if (s.includes(':')) {
                // Take the last non-empty token after splitting on ':' that contains letters
                const parts = s.split(':').map(p => p.trim()).filter(Boolean);
                if (parts.length > 1) {
                    const rev = parts.slice().reverse();
                    // Prefer tokens that contain at least 2 letters (avoid single-letter tshirt tokens)
                    let foundToken = rev.find(tok => (tok.match(/[A-Za-z]/g) || []).length > 1);
                    if (!foundToken) {
                        // fallback to any token with at least one letter
                        foundToken = rev.find(tok => /[A-Za-z]/.test(tok));
                    }
                    if (foundToken) {
                        s = foundToken;
                    } else {
                        // fallback to everything after first colon
                        const after = s.split(':').slice(1).join(':').trim();
                        if (after) s = after;
                    }
                } else {
                    const after = s.split(':').slice(1).join(':').trim();
                    if (after) s = after;
                }
            }

            // If the line starts with one of the ignore words followed by space/colon/hyphen, strip that leading label
            for (const w of ignoreWords) {
                const esc = w.replace(/[-\\^$*+?.()|[\]{}]/g, '\\$&');
                const labelRe = new RegExp('^' + esc + '[:\\s\-]+', 'i');
                if (labelRe.test(s)) {
                    s = s.replace(labelRe, '').trim();
                }
            }

            // Remove any stray colons that may remain
            s = s.replace(/:/g, '').trim();
            if (!s) continue;

            // Skip if the cleaned line contains any of the detected patterns (email, phone, tshirt, roll etc.)
            const low = s.toLowerCase();
            const containsUsedPattern = usedPatterns.some(p => {
                if (!p) return false;
                const esc = p.replace(/[-\\^$*+?.()|[\]{}]/g, '\\$&');
                try {
                    const re = new RegExp('\\b' + esc + '\\b', 'i');
                    return re.test(s);
                } catch (e) {
                    return low.includes(p.toLowerCase());
                }
            });
            if (containsUsedPattern) continue;

            // Skip obvious non-name lines
            if (s.includes('@')) continue;
            // Reject lines that are likely obfuscated phone placeholders like 017xxxxxxx
            if (/x{3,}/i.test(s)) continue;
            const digitCount = (s.match(/\d/g) || []).length;
            if (digitCount > 4) continue;

            // Require at least one letter and a reasonable ratio of letters to length
            const letters = (s.match(/[A-Za-z]/g) || []).length;
            if (letters === 0) continue;
            if (letters / s.length < 0.35) continue;

            // If the cleaned line is exactly one of the ignore words, skip it
            if (ignoreWords.includes(low)) continue;

            return s;
        }
        return '';
    }

    // Handler used by add.html import UI
    handleParse(importTextarea, importFeedback) {
        const text = importTextarea.value || '';
        if (!text.trim()) {
            if (importFeedback) importFeedback.textContent = 'No text to parse';
            return;
        }

        const email = this.findEmail(text);
        const phone = this.findPhone(text);
        const tshirt = this.findTshirtSize(text);
        const inferredGroup = this.detectGroupFromText(text);
        const rawRoll = this.findRoll(text);
        const roll = this.normalizeRoll(rawRoll);

        const lines = text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
        const name = this.findName(lines, [email, phone, tshirt, rawRoll]);

        const found = [];
        if (name) {
            const nameInput = document.getElementById('name');
            if (nameInput && !nameInput.value.trim()) {
                nameInput.value = name;
            }
            found.push('name');
        }
        if (email) {
            const emailInput = document.getElementById('email');
            if (emailInput && !emailInput.value.trim()) emailInput.value = email;
            found.push('email');
        }
        if (phone) {
            const phoneInput = document.getElementById('phone');
            if (phoneInput && !phoneInput.value.trim()) phoneInput.value = phone;
            found.push('phone');
        }
        if (tshirt) {
            const tshirtInput = document.getElementById('tshirt_size');
            if (tshirtInput) {
                tshirtInput.value = tshirt;
                document.getElementById('part_tshirt').checked = true;
                const wrapper = document.getElementById('tshirt-size-container');
                if (wrapper) wrapper.style.display = '';
            }
            found.push('tshirt');
        }
        if (roll) {
            const rollInput = document.getElementById('roll');
            if (rollInput) {
                rollInput.value = roll;
            }
            // trigger lookup via existing lookupStudentData behavior
            try {
                this.lookupStudentData();
            } catch (e) {
                console.warn('Lookup after parse failed', e);
            }

            // Group inference only when roll normalized is 13 digits (5-digit input normalized to 13 OR native 13)
            const rawLen = rawRoll ? rawRoll.length : 0;
            const normLen = roll ? roll.replace(/\D/g, '').length : 0;
            if ((rawLen === 5) || (normLen === 13)) {
                const grpFromRoll = this.inferGroupFromRoll(roll);
                if (grpFromRoll) {
                    const groupSelect = document.getElementById('group');
                    if (groupSelect && !groupSelect.value) {
                        groupSelect.value = grpFromRoll;
                        this.updateRegistrationId();
                    }
                }
            } else {
                // don't set group for 3-digit raw rolls
            }

            found.push('roll');
        } else {
            if (inferredGroup) {
                const groupSelect = document.getElementById('group');
                if (groupSelect && !groupSelect.value) {
                    groupSelect.value = inferredGroup;
                    this.updateRegistrationId();
                    found.push('group');
                }
            }
        }

        if (importFeedback) importFeedback.textContent = found.length ? 'Parsed: ' + found.join(', ') : 'No fields detected';
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