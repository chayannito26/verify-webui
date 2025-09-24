# Chayannito 26 - Registrants Management UI

A comprehensive **static web application** for managing registrants for Chayannito 26. This application provides a clean, modern interface for handling registration data with complete CRUD operations, intelligent grouping, and GitHub API integration for data persistence. **Perfect for GitHub Pages hosting!**

## 🚀 GitHub Pages Ready

This is a fully static web application that can be hosted on GitHub Pages without any server infrastructure. It uses the GitHub API to read and write data directly to the `registrants.json` file in your repository.

## Features

### 🎯 Core Functionality

- **CRUD Operations**: Complete Create, Read, Update, Delete functionality for registrants
- **GitHub API Integration**: All changes are saved directly to GitHub repository via API
- **Auto-generated IDs**: Registration IDs are automatically generated based on group and gender
- **Live Verification Links**: Direct links to verification pages for each registrant
- **Token-based Authentication**: Secure GitHub Personal Access Token authentication
- **Offline Caching**: Smart caching system for better performance and offline capability

### 📊 Smart Organization

- **Group Classification**: Registrants organized by subject groups:
  - 🎨 **Arts (AR)** - Creative and liberal arts students
  - 🔬 **Science (SC)** - Science and technology students  
  - 💼 **Commerce (CO)** - Business and commerce students
- **Gender Segregation**: Within each group, registrants are separated by gender with visual indicators
- **Statistics Dashboard**: Real-time stats showing totals, payments, and active/revoked counts

### 🎨 Intuitive Design

- **Visual Cues**:
  - Colored dots for gender identification (🔵 Male, 🟣 Female)
  - Group emojis for quick recognition
  - Status indicators for revoked registrations
- **Responsive Layout**: Works seamlessly on desktop and mobile devices
- **Beautiful UI**: Modern design using Tailwind CSS with smooth animations

### 🛡️ Robust Features

- **Form Validation**: Comprehensive client-side and server-side validation
- **Error Handling**: Graceful error handling with user-friendly messages
- **Confirmation Dialogs**: Safety confirmations for destructive actions
- **Auto-preview**: Registration ID preview while filling forms

## Quick Start

### 🌐 GitHub Pages Deployment

1. **Fork or clone this repository**
2. **Enable GitHub Pages** in your repository settings
3. **Set the source** to the main branch
4. **Access your site** at `https://yourusername.github.io/verify-webui`

### 🔑 Setup GitHub Token

1. **Generate a Personal Access Token**:
   - Go to [GitHub Settings > Tokens](https://github.com/settings/tokens)
   - Create a new token with `repo` permissions
   - Copy the token (starts with `ghp_`)

2. **Configure the application**:
   - Open your deployed site
   - Enter your GitHub token when prompted
   - The token is stored securely in your browser's localStorage

### 🏠 Local Development

```bash
# Serve the static files locally
python3 -m http.server 8080
# or
npx serve .
# or use any static file server
```

Then open `http://localhost:8080` in your browser.

## File Structure

```text
├── index.html                       # Main dashboard
├── add.html                        # Add new registrant form  
├── edit.html                       # Edit existing registrant form
├── js/
│   ├── config.js                   # Application configuration
│   ├── github-api.js               # GitHub API client
│   ├── ui-utils.js                 # UI utility functions
│   ├── data-manager.js             # Data management layer
│   ├── app.js                      # Main application logic
│   ├── add-registrant.js           # Add registrant functionality
│   └── edit-registrant.js          # Edit registrant functionality
└── .gitignore                      # Git ignore file
```

## Usage

### Adding Registrants

1. Open the application in your browser
2. Enter your GitHub Personal Access Token when prompted
3. Click "Add Registrant" in the navigation
4. Fill out the comprehensive form with:

- Personal details (name, roll number)
- Group and gender selection  
- Contact information (email, phone)
- Payment details
- Parts availability (T-Shirt, Food, Gift) — selecting T-Shirt reveals a size selector
- T-Shirt size (XS, S, M, L, XL, XXL) when T-Shirt is selected
- Referral information

5. Registration ID is auto-generated based on group and gender
6. Data is immediately saved to GitHub repository via API

### Managing Registrants
 
- **View**: Click "View" to see the live verification page
- **Edit**: Modify any registrant details, including revocation status
- **Delete**: Remove registrants with confirmation prompts
- **Statistics**: Monitor real-time dashboard statistics

### Data Format

Each registrant contains:

```json
{
  "name": "Student Name",
  "roll": "1202425010276",
  "gender": "Male",
  "registration_date": "11 September 2025",
  "registration_id": "SC-B-0001",
  "photo": "",
  "revoked": false,
  "referred_by": "",
  "paid": 1200,
  "email": "student@example.com",
  "phone": "01XXXXXXXXX",
  "parts_available": ["T-Shirt", "Food", "Gift"],
  "tshirt_size": "M"
}
```

## Integration

This management UI integrates seamlessly with the existing verification system:

- **Shared Data**: Uses the same `registrants.json` file in the [chayannito26/verify](https://github.com/chayannito26/verify) repository
- **Compatible URLs**: Verification links use the same ID-to-filename conversion algorithm
- **Consistent Structure**: Maintains all existing data fields and formats
- **GitHub API**: Direct integration with GitHub for real-time data synchronization

## Technical Details

The application is built with modern web technologies:

- **Frontend**: Pure JavaScript (ES6+) with modular architecture
- **Styling**: Tailwind CSS for responsive, modern design
- **Data Storage**: GitHub API for persistent storage
- **Authentication**: GitHub Personal Access Tokens
- **Hosting**: Static files compatible with GitHub Pages, Netlify, Vercel, etc.

### Architecture

- **Modular JavaScript**: Separated concerns with dedicated modules for API, UI, and data management
- **Client-side Routing**: Hash-based navigation between pages
- **Caching Strategy**: LocalStorage caching with configurable TTL
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Form Validation**: Client-side validation with server-side error feedback

## Security Features

- **Token Security**: GitHub tokens stored securely in browser localStorage
- **Input Validation**: Comprehensive form validation and sanitization
- **Error Boundaries**: Graceful handling of API failures and network issues
- **No Server Required**: Eliminates server-side security concerns

## GitHub Pages Setup

1. **Repository Configuration**:
   - Ensure the [chayannito26/verify](https://github.com/chayannito26/verify) repository exists
   - The repository should contain a `registrants.json` file (can be empty `[]` initially)

2. **GitHub Token Permissions**:
   - Create a token with `repo` scope
   - Token needs read/write access to the verify repository

3. **CORS Considerations**:
   - GitHub API supports CORS for browser requests
   - No additional CORS configuration needed

---

Built with ❤️ for Chayannito 26

Notes:

- When generating the master verified list, the "Referred By" column will attempt to resolve the value by registration ID, roll, or name and link to the referer's page. If no matching registrant is found, the original text is shown as plain text (no hyperlink). If the field is empty, an em-dash (—) will be displayed.
