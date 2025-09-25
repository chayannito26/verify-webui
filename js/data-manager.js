// Data management layer for registrants
import { CONFIG } from './config.js';
import { GitHubAPI } from './github-api.js';
import { UIUtils } from './ui-utils.js';

export class DataManager {
    constructor() {
        this.githubAPI = new GitHubAPI();
        this.registrants = [];
        this.fileSHA = null;
    }

    // Load registrants from GitHub or cache
    async loadRegistrants(forceRefresh = false) {
        try {
            // Check cache first if not forcing refresh
            if (!forceRefresh) {
                const cached = this.getCachedData();
                if (cached) {
                    this.registrants = cached.data;
                    this.fileSHA = cached.sha;
                    return this.registrants;
                }
            }

            // Load from GitHub
            const result = await this.githubAPI.getRegistrantsFile();
            this.registrants = result.data;
            this.fileSHA = result.sha;

            // Cache the data
            this.setCachedData({
                data: this.registrants,
                sha: this.fileSHA,
                timestamp: Date.now()
            });

            return this.registrants;
        } catch (error) {
            console.error('Error loading registrants:', error);
            
            // Try to load from cache as fallback
            const cached = this.getCachedData();
            if (cached) {
                UIUtils.showFlashMessage('Using cached data. ' + error.message, 'error');
                this.registrants = cached.data;
                this.fileSHA = cached.sha;
                return this.registrants;
            }
            
            throw error;
        }
    }

    // Save registrants to GitHub
    async saveRegistrants() {
        try {
            const result = await this.githubAPI.updateRegistrantsFile(this.registrants, this.fileSHA);
            
            // Update SHA for next save
            this.fileSHA = result.content.sha;
            
            // Update cache
            this.setCachedData({
                data: this.registrants,
                sha: this.fileSHA,
                timestamp: Date.now()
            });

            return result;
        } catch (error) {
            console.error('Error saving registrants:', error);
            throw error;
        }
    }

    // Add new registrant
    async addRegistrant(registrantData) {
        try {
            // Validate required fields
            if (!registrantData.name || !registrantData.roll || !registrantData.gender || !registrantData.group) {
                throw new Error('Name, roll number, gender, and group are required.');
            }

            // Check for duplicate roll number
            if (this.registrants.some(r => r.roll === registrantData.roll)) {
                throw new Error(`Roll number ${registrantData.roll} is already registered.`);
            }

            // Generate registration ID if not provided
            if (!registrantData.registration_id) {
                registrantData.registration_id = UIUtils.getNextRegistrationId(
                    this.registrants,
                    registrantData.group,
                    registrantData.gender
                );
            } else {
                // Check for duplicate registration ID
                if (this.registrants.some(r => r.registration_id === registrantData.registration_id)) {
                    throw new Error(`Registration ID ${registrantData.registration_id} is already in use.`);
                }
            }

            // Set default values
            const registrationDate = registrantData.registration_date || new Date().toISOString().split('T')[0];
            
            const newRegistrant = {
                name: registrantData.name,
                roll: registrantData.roll,
                gender: registrantData.gender,
                group: registrantData.group,  // Add group to registrant data
                registration_date: new Date(registrationDate).toLocaleDateString('en-GB'),
                registration_id: registrantData.registration_id,
                photo: registrantData.photo || '',
                revoked: false,
                referred_by: registrantData.referred_by || '',
                paid: parseInt(registrantData.paid) || 0,
                email: registrantData.email || '',
                phone: registrantData.phone || '',
                parts_available: registrantData.parts_available || [],
                tshirt_size: registrantData.tshirt_size || ''
            };

            // Add to local array
            this.registrants.push(newRegistrant);

            // Save to GitHub
            await this.saveRegistrants();

            // Add revenue entry
            try {
                await this.githubAPI.addRevenueEntry(
                    newRegistrant.name,
                    newRegistrant.group,
                    newRegistrant.gender,
                    registrationDate
                );
            } catch (revenueError) {
                console.error('Error adding revenue entry:', revenueError);
                // Don't throw error for revenue tracking failure - continue with successful registration
            }

            return newRegistrant;
        } catch (error) {
            console.error('Error adding registrant:', error);
            throw error;
        }
    }

    // Update existing registrant
    async updateRegistrant(registrationId, updates) {
        try {
            const index = this.registrants.findIndex(r => r.registration_id === registrationId);
            if (index === -1) {
                throw new Error('Registrant not found.');
            }

            // Check for duplicate roll if changed
            if (updates.roll && updates.roll !== this.registrants[index].roll) {
                if (this.registrants.some(r => r.roll === updates.roll)) {
                    throw new Error(`Roll number ${updates.roll} is already registered.`);
                }
            }

            // Update registrant
            this.registrants[index] = {
                ...this.registrants[index],
                ...updates,
                paid: parseInt(updates.paid) || this.registrants[index].paid
            };

            // Save to GitHub
            await this.saveRegistrants();

            return this.registrants[index];
        } catch (error) {
            console.error('Error updating registrant:', error);
            throw error;
        }
    }

    // Delete registrant
    async deleteRegistrant(registrationId) {
        try {
            const index = this.registrants.findIndex(r => r.registration_id === registrationId);
            if (index === -1) {
                throw new Error('Registrant not found.');
            }

            // Remove from local array
            const deletedRegistrant = this.registrants.splice(index, 1)[0];

            // Save to GitHub
            await this.saveRegistrants();

            return deletedRegistrant;
        } catch (error) {
            console.error('Error deleting registrant:', error);
            throw error;
        }
    }

    // Get registrant by registration ID
    getRegistrant(registrationId) {
        return this.registrants.find(r => r.registration_id === registrationId);
    }

    // Get registrant by roll number
    getRegistrantByRoll(roll) {
        return this.registrants.find(r => r.roll === roll);
    }

    // Get all registrants
    getRegistrants() {
        return this.registrants;
    }

    // Get grouped registrants
    getGroupedRegistrants() {
        return UIUtils.groupRegistrants(this.registrants);
    }

    // Get statistics
    getStatistics() {
        return UIUtils.calculateStats(this.registrants);
    }

    // Cache management
    getCachedData() {
        try {
            const cached = localStorage.getItem(CONFIG.STORAGE_KEYS.CACHED_DATA);
            const timestamp = localStorage.getItem(CONFIG.STORAGE_KEYS.CACHE_TIMESTAMP);
            
            if (cached && timestamp) {
                const cacheAge = Date.now() - parseInt(timestamp);
                if (cacheAge < CONFIG.CACHE_DURATION) {
                    return JSON.parse(cached);
                }
            }
        } catch (e) {
            console.warn('Error reading cache:', e);
        }
        return null;
    }

    setCachedData(data) {
        try {
            localStorage.setItem(CONFIG.STORAGE_KEYS.CACHED_DATA, JSON.stringify(data));
            localStorage.setItem(CONFIG.STORAGE_KEYS.CACHE_TIMESTAMP, data.timestamp.toString());
        } catch (e) {
            console.warn('Error setting cache:', e);
        }
    }

    clearCache() {
        localStorage.removeItem(CONFIG.STORAGE_KEYS.CACHED_DATA);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.CACHE_TIMESTAMP);
    }

    // Test GitHub connection
    async testConnection() {
        return await this.githubAPI.testToken();
    }

    // Get repository info
    async getRepoInfo() {
        return await this.githubAPI.getRepoInfo();
    }
}