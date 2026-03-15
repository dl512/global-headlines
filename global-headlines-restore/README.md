# Global Headlines Website - Restored

This folder contains the restored Global Headlines website files that were replaced by the Morning Coffee website.

## Files

- `index.html` - Main HTML file for the Global Headlines website
- `styles.css` - Styling for the website
- `script.js` - JavaScript for loading and displaying headlines

## How to Restore to GitHub Repository

To restore this website to the `dl512/global-headlines` repository:

1. **Clone the global-headlines repository** (if you haven't already):
   ```bash
   git clone https://github.com/dl512/global-headlines.git
   cd global-headlines
   ```

2. **Copy these files to the repository root**:
   ```bash
   cp /path/to/global-headlines-restore/* .
   ```

3. **Commit and push**:
   ```bash
   git add index.html styles.css script.js
   git commit -m "Restore original Global Headlines website"
   git push origin main
   ```

4. **Configure GitHub Pages** (if needed):
   - Go to repository Settings → Pages
   - Select source: "Deploy from a branch"
   - Branch: `main` / `/ (root)`
   - Save

The website will be available at: `https://dl512.github.io/global-headlines/`

## Important: API Key Configuration

⚠️ **SECURITY WARNING**: The `script.js` file contains a placeholder for a Google Sheets API key. 

Before deploying:
1. Open `script.js` and replace `YOUR_API_KEY_HERE` with your actual Google Sheets API key
2. **IMPORTANT**: Use a **restricted API key** for public websites:
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create a new API key
   - Restrict it to:
     - **API restrictions**: Only allow "Google Sheets API"
     - **Application restrictions**: HTTP referrers (web sites)
     - Add your domain: `https://dl512.github.io/*`
3. Never commit API keys to public repositories without restrictions

Alternatively, you can:
- Use the embedded sample data (already in `script.js`)
- Set up a backend proxy to fetch data securely
- Use environment variables (requires a build process)

## Notes

- The Morning Coffee website should remain in the `dl512/morningcoffee` repository
- This restores the original Global Headlines website that displays news headlines from around the world
- The website uses JavaScript to load headlines dynamically from Google Sheets or embedded sample data

