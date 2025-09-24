// GitHub API client for managing registrants data
import { CONFIG } from './config.js';

export class GitHubAPI {
    constructor() {
        this.token = localStorage.getItem(CONFIG.STORAGE_KEYS.GITHUB_TOKEN);
        this.baseURL = CONFIG.GITHUB.API_BASE;
        this.owner = CONFIG.GITHUB.OWNER;
        this.repo = CONFIG.GITHUB.REPO;
        this.filePath = CONFIG.GITHUB.FILE_PATH;
    }

    // Check if we have a valid token
    hasValidToken() {
        return !!this.token;
    }

    // Set GitHub token
    setToken(token) {
        this.token = token;
        localStorage.setItem(CONFIG.STORAGE_KEYS.GITHUB_TOKEN, token);
    }

    // Remove token (logout)
    removeToken() {
        this.token = null;
        localStorage.removeItem(CONFIG.STORAGE_KEYS.GITHUB_TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.CACHED_DATA);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.CACHE_TIMESTAMP);
    }

    // Make authenticated request to GitHub API
    async makeRequest(endpoint, options = {}) {
        if (!this.token) {
            throw new Error('No GitHub token available');
        }

        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Authorization': `token ${this.token}`,
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json',
            ...options.headers
        };

        const config = {
            ...options,
            headers
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Invalid GitHub token. Please check your token and try again.');
            } else if (response.status === 404) {
                throw new Error('Repository or file not found. Please check the repository exists.');
            } else if (response.status === 403) {
                throw new Error('Access denied. Please ensure your token has the required permissions.');
            }
            throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
        }

        return response.json();
    }

    // Get the current registrants.json file
    async getRegistrantsFile() {
        try {
            const endpoint = `/repos/${this.owner}/${this.repo}/contents/${this.filePath}`;
            const fileData = await this.makeRequest(endpoint);
            
            // Decode base64 content
            const content = atob(fileData.content.replace(/\s/g, ''));
            const registrants = JSON.parse(content);
            
            return {
                data: registrants,
                sha: fileData.sha
            };
        } catch (error) {
            if (error.message.includes('404')) {
                // File doesn't exist yet, return empty array
                return {
                    data: [],
                    sha: null
                };
            }
            throw error;
        }
    }

    // Update the registrants.json file
    async updateRegistrantsFile(registrants, sha = null) {
        const endpoint = `/repos/${this.owner}/${this.repo}/contents/${this.filePath}`;
        
        // Convert data to base64
        const content = btoa(JSON.stringify(registrants, null, 2));
        
        const body = {
            message: `Update registrants data via web UI - ${new Date().toISOString()}`,
            content: content
        };

        // If we have a SHA (file exists), include it for update
        if (sha) {
            body.sha = sha;
        }

        return await this.makeRequest(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
    }

    // Test the GitHub token by making a simple request
    async testToken() {
        try {
            const endpoint = `/repos/${this.owner}/${this.repo}`;
            await this.makeRequest(endpoint);
            return true;
        } catch (error) {
            return false;
        }
    }

    // Get repository information
    async getRepoInfo() {
        const endpoint = `/repos/${this.owner}/${this.repo}`;
        return await this.makeRequest(endpoint);
    }
}