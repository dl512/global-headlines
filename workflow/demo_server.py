"""
Demo Server for Newsletter Generation UI
Provides API endpoints and real-time progress updates via Server-Sent Events
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import threading
import queue
from io import StringIO
from contextlib import contextmanager
from io import StringIO
from contextlib import contextmanager

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_newsletter_config_from_prompt import generate_config_from_prompt, save_user_config
from run_newsletter_pipeline import main as run_pipeline
from common.user_config_manager import load_user_newsletter_config

app = Flask(__name__, 
            template_folder='demo_ui', 
            static_folder='demo_ui',
            static_url_path='/static')
CORS(app)

# Global progress queue for SSE (with max size to prevent memory issues)
progress_queue = queue.Queue(maxsize=1000)


def log_progress(message: str, status: str = "info"):
    """Log progress message to queue for SSE streaming"""
    try:
        # Use non-blocking put to avoid hanging
        progress_queue.put_nowait({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "status": status  # info, success, error, warning
        })
    except queue.Full:
        # If queue is full, try to make space by removing old items
        try:
            # Remove one old item
            progress_queue.get_nowait()
            # Try again
            progress_queue.put_nowait({
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "status": status
            })
        except:
            pass  # If still fails, skip this log entry (don't block)


class PrintCapture:
    """Capture print statements and forward to progress queue"""
    def __init__(self):
        self.buffer = StringIO()
        self.original_stdout = sys.stdout
        
    def write(self, text):
        """Write to buffer and also forward to progress queue"""
        # Write to buffer first
        self.buffer.write(text)
        
        # Process and forward to progress queue
        if text and text.strip():  # Only log non-empty lines
            # Split by newlines to handle multiple lines
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Skip separator lines and very long lines
                if "=" * 80 in line or len(line) > 300:
                    continue
                
                # Determine status based on content
                status = "info"
                line_lower = line.lower()
                if "✓" in line or "complete" in line_lower or "saved" in line_lower or "generated" in line_lower:
                    status = "success"
                elif "ERROR" in line or "✗" in line or "error" in line_lower or "failed" in line_lower:
                    status = "error"
                elif "WARNING" in line or "⚠" in line or "warning" in line_lower:
                    status = "warning"
                elif "processing" in line_lower or "crawling" in line_lower or "fetching" in line_lower or "extracting" in line_lower or "matching" in line_lower:
                    status = "info"
                
                # Clean up common prefixes for better display
                if line.startswith("  ") and not line.startswith("  →"):
                    line = "  → " + line.strip()
                elif line.startswith("    ") and not line.startswith("    →"):
                    line = "    → " + line.strip()
                
                # Use non-blocking put to avoid hanging
                try:
                    log_progress(line, status)
                except:
                    pass  # Don't let logging errors break the crawler
        
    def flush(self):
        self.buffer.flush()
        
    def getvalue(self):
        return self.buffer.getvalue()


@contextmanager
def capture_prints():
    """Context manager to capture print statements"""
    capture = PrintCapture()
    old_stdout = sys.stdout
    sys.stdout = capture
    try:
        yield capture
    finally:
        sys.stdout = old_stdout


async def generate_newsletter_async(user_prompt: str, user_id: str, user_email: str = None):
    """Generate newsletter from prompt with progress logging"""
    try:
        log_progress("Starting newsletter generation...", "info")
        
        # Step 1: Generate config from prompt
        log_progress("Step 1: Parsing your prompt and generating newsletter configuration...", "info")
        try:
            # Capture prints from config generation
            with capture_prints():
                newsletter_config = await generate_config_from_prompt(user_prompt, user_email)
            log_progress("✓ Newsletter configuration generated", "success")
        except Exception as e:
            error_msg = str(e)
            log_progress(f"ERROR in config generation: {error_msg}", "error")
            import traceback
            tb = traceback.format_exc()
            # Log traceback in chunks if too long
            if len(tb) > 500:
                log_progress(f"Traceback (first 500 chars): {tb[:500]}...", "error")
            else:
                log_progress(f"Traceback: {tb}", "error")
            raise
        
        # Step 2: Save user config
        log_progress("Step 2: Saving your newsletter preferences...", "info")
        await save_user_config(user_id, newsletter_config)
        log_progress("✓ Preferences saved", "success")
        
        # Step 3: Run pipeline
        log_progress("Step 3: Starting newsletter pipeline...", "info")
        log_progress("  → Identifying required components...", "info")
        
        # Use the newsletter_config that was just generated (don't reload from file)
        # The newsletter_config from generate_config_from_prompt is a single newsletter dict
        newsletters_config = [newsletter_config]
        
        from run_newsletter_pipeline import get_required_components, extract_component_customizations
        required_components = get_required_components(newsletters_config)
        component_customizations = extract_component_customizations(newsletters_config)
        
        log_progress(f"  → Found {len(newsletters_config)} newsletter(s)", "info")
        requested_components = newsletter_config.get("components", [])
        log_progress(f"  → Newsletter components: {', '.join(requested_components)}", "info")
        log_progress(f"  → Required components: {', '.join(sorted(required_components))}", "info")
        
        # Step 4: Run crawlers with detailed logging
        log_progress("Step 4: Crawling news sources...", "info")
        log_progress("  → Starting crawlers for each component...", "info")
        
        from run_newsletter_pipeline import run_crawlers
        
        # Capture print statements from crawlers
        with capture_prints():
            await run_crawlers(required_components, component_customizations)
        
        log_progress("✓ Crawling complete", "success")
        
        # Step 5: Generate summaries with detailed logging
        log_progress("Step 5: Generating summaries...", "info")
        log_progress("  → Processing summaries for each component...", "info")
        
        from run_newsletter_pipeline import generate_summaries
        
        # Capture print statements from summarizers
        with capture_prints():
            summaries = await generate_summaries(required_components, component_customizations)
        
        log_progress("✓ Summaries generated", "success")
        
        # Step 6: Generate newsletter
        log_progress("Step 6: Compiling newsletter...", "info")
        from run_newsletter_pipeline import generate_newsletter
        newsletter_content_dict = await generate_newsletter(newsletter_config, summaries)
        log_progress("✓ Newsletter compiled", "success")
        
        # Step 7: Get newsletter content
        newsletter_name = newsletter_config.get("name", "newsletter")
        log_progress("Step 7: Finalizing newsletter...", "info")
        
        # newsletter_content_dict should be a dict with language keys
        if not newsletter_content_dict:
            # Try to load from file
            try:
                today = datetime.now().strftime("%Y%m%d")
                newsletter_path = os.path.join("newsletter", newsletter_name, f"newsletter_{today}_en.md")
                if os.path.exists(newsletter_path):
                    with open(newsletter_path, 'r', encoding='utf-8') as f:
                        newsletter_content_dict = {"en": f.read()}
                else:
                    newsletter_content_dict = {"en": "Newsletter generated successfully, but content file not found."}
            except Exception as e:
                log_progress(f"Warning: Could not load newsletter file: {e}", "warning")
                newsletter_content_dict = {"en": f"Newsletter generated, but error loading content: {str(e)}"}
        
        log_progress("✓ Newsletter ready!", "success")
        
        return {
            "success": True,
            "newsletter_name": newsletter_name,
            "content": newsletter_content_dict or {"en": "Newsletter generated successfully, but content not available."},
            "config": newsletter_config
        }
        
    except Exception as e:
        log_progress(f"ERROR: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def run_async_task(coro):
    """Run async coroutine in a new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.route('/')
def index():
    """Serve the demo UI"""
    return render_template('index.html')


@app.route('/script.js')
def script_js():
    """Serve JavaScript file"""
    from flask import send_from_directory
    return send_from_directory('demo_ui', 'script.js')


@app.route('/styles.css')
def styles_css():
    """Serve CSS file"""
    from flask import send_from_directory
    return send_from_directory('demo_ui', 'styles.css')


@app.route('/api/generate', methods=['POST'])
def generate_newsletter():
    """Generate newsletter from prompt"""
    data = request.json
    user_prompt = data.get('prompt', '')
    user_id = data.get('user_id', 'demo_user')
    user_email = data.get('user_email', 'demo@example.com')  # Not used for display, but needed for config
    
    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400
    
    # Clear progress queue
    while not progress_queue.empty():
        try:
            progress_queue.get_nowait()
        except queue.Empty:
            break
    
    # Run async task in background thread
    def run_generation():
        try:
            result = run_async_task(generate_newsletter_async(user_prompt, user_id, user_email))
            # Use non-blocking put for completion message
            try:
                progress_queue.put_nowait({
                    "timestamp": datetime.now().isoformat(),
                    "message": "COMPLETE",
                    "status": "complete",
                    "result": result
                })
            except queue.Full:
                # If queue is full, clear it and add completion
                while not progress_queue.empty():
                    try:
                        progress_queue.get_nowait()
                    except:
                        break
                progress_queue.put_nowait({
                    "timestamp": datetime.now().isoformat(),
                    "message": "COMPLETE",
                    "status": "complete",
                    "result": result
                })
        except Exception as e:
            # Ensure error is logged even if something goes wrong
            try:
                progress_queue.put_nowait({
                    "timestamp": datetime.now().isoformat(),
                    "message": f"ERROR: {str(e)}",
                    "status": "error",
                    "result": {"success": False, "error": str(e)}
                })
            except:
                pass
    
    thread = threading.Thread(target=run_generation)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started", "message": "Newsletter generation started"})


@app.route('/api/progress')
def progress():
    """Server-Sent Events stream for progress updates"""
    def generate():
        last_heartbeat = datetime.now()
        while True:
            try:
                # Get message from queue (with shorter timeout for responsiveness)
                try:
                    message = progress_queue.get(timeout=0.5)
                    yield f"data: {json.dumps(message)}\n\n"
                    last_heartbeat = datetime.now()
                    
                    # If complete, break
                    if message.get("status") == "complete":
                        break
                except queue.Empty:
                    # Send heartbeat every 3 seconds to keep connection alive
                    now = datetime.now()
                    if (now - last_heartbeat).total_seconds() > 3:
                        yield f"data: {json.dumps({'status': 'heartbeat', 'timestamp': now.isoformat()})}\n\n"
                        last_heartbeat = now
            except GeneratorExit:
                # Client disconnected
                break
            except Exception as e:
                # Log error but continue - don't break the stream
                try:
                    yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"
                except:
                    break
                # Continue the loop to keep connection alive
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


if __name__ == '__main__':
    print("Starting Demo Server...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000, threaded=True)

