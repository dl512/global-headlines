# Quick Start - Demo UI

## 🚀 Quick Setup (3 steps)

1. **Install dependencies:**
   ```bash
   pip install flask flask-cors
   ```

2. **Start the demo server:**
   ```bash
   cd workflow
   python demo_server.py
   ```

3. **Open in browser:**
   ```
   http://localhost:5000
   ```

## 📹 Recording Tips

1. **Before recording:**
   - Close unnecessary browser tabs
   - Use a clean browser window (incognito mode recommended)
   - Resize browser to a good size (e.g., 1920x1080 or 1280x720)
   - Have your example prompt ready to copy-paste

2. **During recording:**
   - Start recording BEFORE clicking "Generate Newsletter"
   - The UI will show real-time progress updates
   - Wait for the newsletter to appear at the bottom
   - Scroll through the newsletter to show the content

3. **Example prompt to use:**
   ```
   Hi, I'd like to receive a daily newsletter that covers:

   1. Financial news - I want to stay updated on global markets and economic developments
   2. Tech news - Keep me informed about the latest in technology, startups, and innovation
   3. Market snapshot for these specific stocks:
      - Apple (AAPL)
      - Microsoft (MSFT)
      - Tesla (TSLA)
      - Nvidia (NVDA)
      - S&P 500 index

   I prefer English content. Thanks!
   ```

## 🎨 UI Features

- **Gradient background** - Beautiful purple gradient
- **Real-time progress** - Color-coded log entries (blue=info, green=success, orange=warning, red=error)
- **Progress bar** - Visual progress indicator
- **Formatted newsletter** - Markdown converted to beautiful HTML
- **Smooth animations** - Professional transitions

## ⚠️ Troubleshooting

- **Port already in use?** Change port in `demo_server.py` (last line)
- **Module not found?** Make sure you're in the `workflow` directory
- **No progress updates?** Check browser console for errors
- **Newsletter not showing?** Check server logs for errors

