# Morning Coffee Website

A minimalistic landing page for the Morning Coffee project—a personalized daily newsletter service.

## Overview

Morning Coffee delivers tailored daily newsletters to help people start their day informed, without the endless scrolling through social media feeds.

## Features

- **Clean, Minimalistic Design**: Simple and focused user experience
- **Sample Newsletters**: Showcases two example newsletters (Global Headlines and Market Briefing)
- **Sample Prompts**: Demonstrates how users can request personalized newsletters
- **Subscription Link**: Direct link to Google Form for user sign-ups

## Quick Start

Simply open `index.html` in your web browser. No server required!

For a better development experience, use a local server:

```bash
# Using Python
python -m http.server 8000

# Using Node.js (with http-server)
npx http-server

# Using PHP
php -S localhost:8000
```

Then visit `http://localhost:8000` in your browser.

## Customization

### Update Subscription Link

Edit `index.html` and replace the Google Form link:

```html
<a href="https://forms.google.com/your-form-link" class="subscribe-button">
```

### Update Sample Prompts

Edit the sample prompts in `index.html` to match your current newsletter examples.

### Styling

All styles are in `styles.css`. The design uses:
- Inter font family (from Google Fonts)
- Minimal color palette (black, white, grays)
- Responsive design for mobile devices

## File Structure

```
public/
├── index.html      # Main HTML structure
├── styles.css      # All styling and responsive design
└── README.md       # This file
```

## Deployment

### GitHub Pages

1. Create a repository on GitHub
2. Push your code
3. Go to Settings → Pages
4. Select your branch and `/public` folder
5. Your site will be live at `https://username.github.io/repository-name/`

### Netlify

1. Drag and drop the `public` folder to [Netlify Drop](https://app.netlify.com/drop)
2. Your site will be live instantly with a custom URL

### Vercel

1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in your project directory
3. Follow the prompts

---

Built with simplicity in mind ☕
