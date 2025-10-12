# Global Headlines Website

A clean, modern website displaying news headlines from major newspapers around the world.

## Features

- 🌍 **Global Coverage**: Display headlines from newspapers across different countries
- 🔍 **Search Functionality**: Filter headlines by country or newspaper name
- 📱 **Responsive Design**: Beautiful UI that works on desktop, tablet, and mobile
- 🎨 **Modern Interface**: Clean, professional design with smooth animations
- ⚡ **Fast Loading**: Lightweight and optimized for performance

## Quick Start

> **🎉 Google Sheets Integration is READY!** See [QUICK_START.md](QUICK_START.md) for setup instructions.

### Option 1: View Locally

Simply open `index.html` in your web browser. No server required!

### Option 2: Use a Local Server

For a better development experience:

```bash
# Using Python
python -m http.server 8000

# Using Node.js (with http-server)
npx http-server

# Using PHP
php -S localhost:8000
```

Then visit `http://localhost:8000` in your browser.

## Updating Headlines

### Method 1: Manual Update (Easiest)

Edit the `data.json` file with your latest headlines:

```json
{
  "lastUpdated": "2025-10-12T00:00:00Z",
  "headlines": [
    {
      "country": "United Kingdom",
      "newspaper": "The Guardian",
      "website": "https://www.theguardian.com/",
      "headline": "Your headline text here",
      "link": "https://link-to-article.com",
      "flag": "🇬🇧"
    }
  ]
}
```

### Method 2: Update script.js

Alternatively, update the `headlinesData` array directly in `script.js` (lines 3-60).

### Method 3: Google Sheets Integration

To automatically fetch data from your Google Sheet:

1. **Enable Google Sheets API**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Sheets API
   - Create API credentials (API Key)

2. **Make your sheet public** (or use OAuth for private sheets):

   - Open your Google Sheet
   - Click "Share" → "Anyone with the link can view"

3. **Update script.js**:

   - Uncomment the `fetchFromGoogleSheets()` function
   - Replace `YOUR_SHEET_ID` with your actual Sheet ID from the URL
   - Replace `YOUR_API_KEY` with your Google API key
   - Adjust the `RANGE` to match your sheet structure (e.g., `Sheet1!A2:F`)

4. **Modify the init function** to fetch data:

```javascript
async function init() {
  const data = await fetchFromGoogleSheets();
  if (data.length > 0) {
    headlinesData = data;
  }
  renderHeadlines(headlinesData);
  setupSearch();
}
```

## File Structure

```
public/
├── index.html      # Main HTML structure
├── styles.css      # All styling and responsive design
├── script.js       # JavaScript for dynamic content and search
├── data.json       # Optional: Store headlines data
└── README.md       # This file
```

## Customization

### Colors

Edit the CSS variables in `styles.css` (lines 16-26):

```css
:root {
  --primary-color: #2563eb;
  --primary-dark: #1e40af;
  --secondary-color: #f59e0b;
  /* ... other colors */
}
```

### Typography

Change the font by updating the Google Fonts import in `index.html` and the font-family in `styles.css`.

### Adding More Countries

Add flag emojis for new countries in the `countryFlags` object in `script.js`:

```javascript
const countryFlags = {
  "Your Country": "🏁",
  // ... existing entries
};
```

## Browser Support

- ✅ Chrome (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Edge (latest)
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## Deployment

### GitHub Pages

1. Create a repository on GitHub
2. Push your code
3. Go to Settings → Pages
4. Select your branch and `/root` folder
5. Your site will be live at `https://username.github.io/repository-name/`

### Netlify

1. Drag and drop the `public` folder to [Netlify Drop](https://app.netlify.com/drop)
2. Your site will be live instantly with a custom URL

### Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in your project directory
3. Follow the prompts

## Google Sheet Format

Your Google Sheet should have these columns:

| Column | Content                      |
| ------ | ---------------------------- |
| A      | Country name                 |
| B      | Newspaper name               |
| C      | Newspaper website URL        |
| D      | (Optional/unused)            |
| E      | Today's headline             |
| F      | Link to the headline article |

## License

Free to use for personal and commercial projects.

## Support

For issues or questions, please refer to the comments in the code or create an issue in your repository.

---

Built with ❤️ for news enthusiasts worldwide
