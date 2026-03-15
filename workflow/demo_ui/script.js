let eventSource = null;
let isGenerating = false;

function generateNewsletter() {
    if (isGenerating) {
        return;
    }

    const prompt = document.getElementById('promptInput').value.trim();

    if (!prompt) {
        alert('Please enter a prompt');
        return;
    }

    // Reset UI
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('newsletterPlaceholder').style.display = 'block';
    document.getElementById('newsletterContent').style.display = 'none';
    const logContainer = document.getElementById('logContainer');
    logContainer.innerHTML = '';
    // Reset scroll position
    logContainer.scrollTop = 0;
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = 'Starting...';
    document.getElementById('generateBtn').disabled = true;
    isGenerating = true;

    // Start generation
    fetch('/api/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            prompt: prompt,
            user_id: 'demo_user',
            user_email: 'demo@example.com'
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Generation started:', data);
        startProgressStream();
    })
    .catch(error => {
        console.error('Error:', error);
        addLogEntry('ERROR: Failed to start generation', 'error');
        isGenerating = false;
        document.getElementById('generateBtn').disabled = false;
    });
}

function startProgressStream() {
    // Close existing connection if any
    if (eventSource) {
        eventSource.close();
    }

    // Create new EventSource connection
    eventSource = new EventSource('/api/progress');

    let stepCount = 0;
    const totalSteps = 7; // Approximate number of steps

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.status === 'heartbeat') {
            return; // Ignore heartbeat
        }

        if (data.status === 'complete') {
            // Generation complete
            eventSource.close();
            isGenerating = false;
            document.getElementById('generateBtn').disabled = false;
            
            if (data.result && data.result.success) {
                document.getElementById('progressFill').style.width = '100%';
                document.getElementById('progressText').textContent = 'Complete!';
                addLogEntry('✓ Newsletter generation complete!', 'success');
                
                // Show newsletter
                setTimeout(() => {
                    displayNewsletter(data.result);
                }, 500);
            } else {
                addLogEntry(`ERROR: ${data.result?.error || 'Unknown error'}`, 'error');
                document.getElementById('progressText').textContent = 'Generation failed';
            }
            return;
        }

        // Add log entry
        if (data.message) {
            addLogEntry(data.message, data.status || 'info');
        }

        // Update progress
        if (data.message && !data.message.includes('COMPLETE')) {
            stepCount++;
            const progress = Math.min((stepCount / totalSteps) * 100, 95);
            document.getElementById('progressFill').style.width = progress + '%';
            
            // Update progress text
            if (data.message.includes('Step')) {
                document.getElementById('progressText').textContent = data.message;
            }
        }
    };

    eventSource.onerror = function(error) {
        console.error('EventSource error:', error);
        // Try to reconnect if connection is lost
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log('Connection closed, attempting to reconnect...');
            setTimeout(() => {
                if (isGenerating) {
                    startProgressStream();
                }
            }, 2000);
        }
    };
}

function addLogEntry(message, status = 'info') {
    const logContainer = document.getElementById('logContainer');
    const entry = document.createElement('div');
    entry.className = `log-entry ${status}`;
    
    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-timestamp">${timestamp}</span>${escapeHtml(message)}`;
    
    logContainer.appendChild(entry);
    
    // Always auto-scroll to bottom to show latest entry (like Cursor chat)
    // Use instant scroll for real-time updates (smooth scrolling can lag with rapid updates)
    const scrollToBottom = () => {
        // Method 1: Scroll to bottom of container
        logContainer.scrollTop = logContainer.scrollHeight;
        // Method 2: Scroll the entry into view as backup
        entry.scrollIntoView({ behavior: 'auto', block: 'end' });
    };
    
    // Scroll immediately
    scrollToBottom();
    
    // Also scroll after DOM is fully updated (next animation frame)
    requestAnimationFrame(() => {
        scrollToBottom();
    });
    
    // Final scroll after microtask (catches any async layout changes)
    setTimeout(scrollToBottom, 0);
}

function displayNewsletter(result) {
    const newsletterPlaceholder = document.getElementById('newsletterPlaceholder');
    const newsletterContent = document.getElementById('newsletterContent');
    
    // Get newsletter content (prefer English, then any available)
    const content = result.content?.en || result.content?.EN || 
                   result.content?.CN || result.content?.cn ||
                   Object.values(result.content || {})[0] || 
                   'Newsletter content not available.';
    
    // Convert markdown to HTML (simple conversion)
    const htmlContent = convertMarkdownToHTML(content);
    
    newsletterContent.innerHTML = htmlContent;
    newsletterPlaceholder.style.display = 'none';
    newsletterContent.style.display = 'block';
    
    // Scroll to top of newsletter
    newsletterContent.scrollTop = 0;
}

function convertMarkdownToHTML(markdown) {
    let html = markdown;
    
    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Lists
    html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^(\d+)\. (.*$)/gim, '<li>$2</li>');
    
    // Wrap consecutive list items in ul
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // Paragraphs
    html = html.split('\n\n').map(para => {
        if (para.trim() && !para.match(/^<[hul]/)) {
            return '<p>' + para.trim() + '</p>';
        }
        return para;
    }).join('\n');
    
    // Tables
    html = html.replace(/\|(.+)\|/g, function(match) {
        const cells = match.split('|').filter(c => c.trim());
        if (cells.length > 1) {
            const isHeader = cells[0].includes('---') || cells[0].includes('===');
            if (isHeader) {
                return ''; // Skip separator rows
            }
            const cellTag = isHeader ? 'th' : 'td';
            return '<tr>' + cells.map(c => `<${cellTag}>${c.trim()}</${cellTag}>`).join('') + '</tr>';
        }
        return match;
    });
    
    // Wrap table rows in table
    html = html.replace(/(<tr>.*<\/tr>\n?)+/g, '<table>$&</table>');
    
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function resetDemo() {
    // Close event source if open
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    
    // Reset UI
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('newsletterPlaceholder').style.display = 'block';
    document.getElementById('newsletterContent').style.display = 'none';
    document.getElementById('promptInput').value = '';
    document.getElementById('logContainer').innerHTML = '';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('generateBtn').disabled = false;
    isGenerating = false;
}

// Allow Enter key in textarea (but not submit)
document.getElementById('promptInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.ctrlKey) {
        generateNewsletter();
    }
});

