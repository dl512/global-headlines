# Morning Coffee - Demo UI

A beautiful, interactive demo interface for the Morning Coffee newsletter generator.

## Features

- **Natural Language Input**: Users can describe their newsletter needs in plain English
- **Real-Time Progress**: Watch the newsletter generation process step-by-step
- **Live Updates**: Server-Sent Events (SSE) provide real-time progress updates
- **Beautiful UI**: Modern, gradient design perfect for video demonstrations

## Setup

1. Install dependencies:
```bash
pip install -r demo_requirements.txt
```

2. Make sure you have all the required environment variables set (OPENAI_API_KEY, etc.)

3. Run the demo server:
```bash
cd workflow
python demo_server.py
```

4. Open your browser to:
```
http://localhost:5000
```

## Usage

1. Enter a natural language prompt describing your newsletter needs
2. Optionally enter your email address
3. Click "Generate Newsletter"
4. Watch the real-time progress as the system:
   - Parses your prompt
   - Generates newsletter configuration
   - Crawls news sources
   - Generates summaries
   - Compiles your personalized newsletter
5. View your completed newsletter

## Example Prompt

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

## Recording Tips

- Use a clean browser window (no extensions visible)
- Start recording before clicking "Generate Newsletter"
- The UI is designed to be visually appealing for demonstrations
- Progress updates are color-coded (blue=info, green=success, orange=warning, red=error)
- The final newsletter displays in a scrollable, formatted view

## File Structure

```
workflow/
├── demo_server.py          # Flask backend with SSE
├── demo_ui/
│   ├── index.html          # Main UI
│   ├── styles.css          # Beautiful styling
│   └── script.js           # Frontend logic
└── demo_requirements.txt   # Python dependencies
```

