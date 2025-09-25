// Configuration file for the application
export const CONFIG = {
    // GitHub repository information
    GITHUB: {
        OWNER: 'chayannito26',
        REPO: 'verify',
        FILE_PATH: 'registrants.json',
        API_BASE: 'https://api.github.com'
    },
    
    // Income repository information
    INCOME: {
        OWNER: 'chayannito26',
        REPO: 'income',
        FILE_PATH: 'revenues.json',
        API_BASE: 'https://api.github.com'
    },
    
    // Verification system
    VERIFICATION_BASE_URL: 'https://chayannito26.github.io/verify',
    
    // Local storage keys
    STORAGE_KEYS: {
        GITHUB_TOKEN: 'chayannito26_github_token',
        CACHED_DATA: 'chayannito26_cached_registrants',
        CACHE_TIMESTAMP: 'chayannito26_cache_timestamp'
    },
    
    // Cache settings
    CACHE_DURATION: 5 * 60 * 1000, // 5 minutes in milliseconds
    
    // Group and gender mappings (from original Flask app)
    GROUP_INFO: {
        'AR': { name: 'Arts', emoji: '🎨', color: 'blue' },
        'SC': { name: 'Science', emoji: '🔬', color: 'red' },
        'CO': { name: 'Commerce', emoji: '💼', color: 'green' }
    },
    
    GENDER_INFO: {
        'Male': { short: 'B', color: 'blue', dot: '🔵' },
        'Female': { short: 'G', color: 'pink', dot: '🟣' }
    },
    
    // Client mappings for revenue tracking
    CLIENT_MAPPINGS: {
        'SC': {  // Science
            'Male': 'Arian Mollik Wasi',
            'Female': 'Marzia Mittika'
        },
        'AR': {  // Arts
            'Male': 'Sahariar Nafiz',
            'Female': 'Nafiza Tanzim Hafsa'
        },
        'CO': {  // Commerce
            'Male': 'Tanvir Hossain Chowdhury',
            'Female': 'Mehbuba'
        }
    },
    
    // T-shirt size options
    TSHIRT_SIZES: ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
    
    // Parts available options
    PARTS_AVAILABLE: ['T-Shirt', 'Food', 'Gift']
};