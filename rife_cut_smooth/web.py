"""Web interface for RIFE Cut Smooth on Railway."""

import os
import sys
from pathlib import Path
from flask import Flask, request, send_file, render_template_string, jsonify
import tempfile
import shutil
import traceback

from .config import Config

# Try to import pipeline - if it fails, the app will still start
PIPELINE_AVAILABLE = False
Pipeline = None
IMPORT_ERROR = None
try:
    from .pipeline import Pipeline
    PIPELINE_AVAILABLE = True
except Exception as e:
    IMPORT_ERROR = str(e)
    print(f"[ERROR] Failed to import Pipeline: {e}")
    print(traceback.format_exc())

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max file size
app.config['UPLOAD_FOLDER'] = '/app/uploads'
app.config['OUTPUT_FOLDER'] = '/app/outputs'

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>RIFE Cut Smooth</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .upload-form {
            margin: 20px 0;
        }
        .form-group {
            margin: 15px 0;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        input[type="file"],
        input[type="number"],
        select {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input[type="number"] {
            width: 200px;
        }
        button {
            background: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            background: #45a049;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .progress {
            display: none;
            margin: 20px 0;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #f0f0f0;
            border-radius: 5px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: #4CAF50;
            width: 0%;
            transition: width 0.3s;
        }
        .log {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 20px;
        }
        .debug-panel {
            background: #fff3cd;
            border: 2px solid #ffc107;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .debug-panel h3 {
            margin-top: 0;
            color: #856404;
        }
        .debug-log {
            background: #1e1e1e;
            color: #00ff00;
            padding: 10px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            margin: 10px 0;
        }
        .debug-buttons {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .debug-buttons button {
            background: #ffc107;
            color: #000;
            padding: 8px 16px;
            font-size: 14px;
        }
        .debug-buttons button:hover {
            background: #e0a800;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            background: #e8f5e9;
            border-left: 4px solid #4CAF50;
            border-radius: 5px;
            display: none;
        }
        .error {
            background: #ffebee;
            border-left-color: #f44336;
            color: #c62828;
        }
        .info-box {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #2196F3;
        }
        .help-text {
            font-size: 13px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 RIFE Cut Smooth</h1>
        <p>Upload a video with hard cuts, and this tool will smooth them using RIFE optical flow interpolation.</p>

        <div class="info-box">
            <strong>How it works:</strong>
            <ul>
                <li>Detects hard cuts in your video automatically</li>
                <li>Replaces each cut with a smooth RIFE-interpolated transition</li>
                <li>Preserves original video length (length-preserving algorithm)</li>
                <li>Keeps audio in perfect sync</li>
            </ul>
        </div>

        <form id="uploadForm" class="upload-form" enctype="multipart/form-data" onsubmit="return false;">
            <div class="form-group">
                <label for="video">Video File:</label>
                <input type="file" id="video" name="video" accept="video/*" required>
                <div class="help-text">Supports MP4, MOV, AVI, MKV, etc. Max 2GB.</div>
            </div>

            <div class="form-group">
                <label for="fps">Target FPS:</label>
                <input type="number" id="fps" name="fps" value="30" min="15" max="120" step="1">
                <div class="help-text">Output frame rate (default: 30fps)</div>
            </div>

            <div class="form-group">
                <label for="threshold">Scene Threshold:</label>
                <input type="number" id="threshold" name="threshold" value="0.30" min="0.1" max="0.9" step="0.05">
                <div class="help-text">Cut detection sensitivity. Lower = more cuts detected (default: 0.30)</div>
            </div>

            <div class="form-group">
                <label for="bridge">Bridge Duration (seconds):</label>
                <input type="number" id="bridge" name="bridge" value="0.5" min="0.1" max="2.0" step="0.1">
                <div class="help-text">Length of smooth transition (default: 0.5s)</div>
            </div>

            <div class="form-group">
                <label for="audio">Audio Mode:</label>
                <select id="audio" name="audio">
                    <option value="keep-original">Keep Original (recommended)</option>
                    <option value="stretch-audio">Stretch to Match</option>
                    <option value="no-audio">No Audio</option>
                </select>
                <div class="help-text">How to handle audio in output</div>
            </div>

            <button type="submit" id="submitBtn">🚀 Process Video</button>
        </form>

        <div class="progress" id="progress">
            <p>Processing... <span id="statusText">Starting...</span></p>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
        </div>

        <div class="log" id="log"></div>

        <div class="result" id="result"></div>

        <div class="debug-panel">
            <h3>🐛 Debug Console (Persistent)</h3>
            <div class="debug-log" id="debugLog">WAITING FOR JAVASCRIPT TO LOAD...</div>
            <div class="debug-buttons">
                <button type="button" onclick="copyDebugLogs()">📋 Copy Logs</button>
                <button type="button" onclick="clearDebugLogs()">🗑️ Clear Logs</button>
            </div>
            <p style="margin-top: 10px; font-size: 12px; color: #856404;">
                <strong>Script Status:</strong> <span id="scriptStatus">NOT LOADED</span>
            </p>
        </div>
    </div>

    <script>
        document.getElementById('scriptStatus').textContent = 'LOADING...';
        // Persistent debug logging system
        const DEBUG_KEY = 'rife-debug-logs';

        function debugLog(message, data) {
            const timestamp = new Date().toISOString();
            const logEntry = '[' + timestamp + '] ' + message;
            const fullEntry = data ? logEntry + '\n' + JSON.stringify(data, null, 2) : logEntry;

            console.log(message, data || '');

            // Get existing logs
            let logs = localStorage.getItem(DEBUG_KEY) || '';
            logs += fullEntry + '\n\n';
            localStorage.setItem(DEBUG_KEY, logs);

            // Update UI
            updateDebugDisplay();
        }

        function updateDebugDisplay() {
            const debugLogEl = document.getElementById('debugLog');
            if (debugLogEl) {
                debugLogEl.textContent = localStorage.getItem(DEBUG_KEY) || 'No logs yet...';
                debugLogEl.scrollTop = debugLogEl.scrollHeight;
            }
        }

        function copyDebugLogs() {
            const logs = localStorage.getItem(DEBUG_KEY) || 'No logs available';
            navigator.clipboard.writeText(logs).then(function() {
                alert('Logs copied to clipboard!');
            }).catch(function(err) {
                alert('Failed to copy: ' + err);
            });
        }

        function clearDebugLogs() {
            localStorage.removeItem(DEBUG_KEY);
            updateDebugDisplay();
            debugLog('Logs cleared');
        }

        // Make functions global
        window.copyDebugLogs = copyDebugLogs;
        window.clearDebugLogs = clearDebugLogs;

        (function() {
            debugLog('=== PAGE LOAD ===');
            debugLog('Script execution started');
            debugLog('User Agent', {userAgent: navigator.userAgent});
            debugLog('Page URL', {url: window.location.href});

            const form = document.getElementById('uploadForm');
            const submitBtn = document.getElementById('submitBtn');
            const progress = document.getElementById('progress');
            const progressFill = document.getElementById('progressFill');
            const statusText = document.getElementById('statusText');
            const log = document.getElementById('log');
            const result = document.getElementById('result');

            debugLog('DOM elements found', {
                form: !!form,
                submitBtn: !!submitBtn,
                progress: !!progress,
                result: !!result
            });

            if (!form) {
                debugLog('ERROR: Form element not found!');
                return;
            }

            debugLog('Attaching form submit listener');

            form.addEventListener('submit', function(e) {
                debugLog('=== FORM SUBMIT EVENT ===');
                debugLog('Event object', {
                    type: e.type,
                    target: e.target.id,
                    defaultPrevented: e.defaultPrevented
                });

                e.preventDefault();
                debugLog('preventDefault() called', {nowDefaultPrevented: e.defaultPrevented});

                try {
                    handleSubmit(e);
                } catch (err) {
                    debugLog('ERROR in handleSubmit', {
                        message: err.message,
                        stack: err.stack
                    });
                }
            });

            debugLog('Form listener attached successfully');

            async function handleSubmit(e) {
                debugLog('handleSubmit() started');

                // Validate file is selected
                const fileInput = document.getElementById('video');
                debugLog('File input check', {
                    found: !!fileInput,
                    hasFiles: !!(fileInput && fileInput.files),
                    fileCount: fileInput ? fileInput.files.length : 0
                });

                if (!fileInput.files || fileInput.files.length === 0) {
                    debugLog('No file selected - showing error');
                    result.innerHTML = '<h3>❌ Error</h3><p>Please select a video file first.</p>';
                    result.classList.add('error');
                    result.style.display = 'block';
                    return;
                }

                const selectedFile = fileInput.files[0];
                debugLog('File selected', {
                    name: selectedFile.name,
                    size: selectedFile.size,
                    type: selectedFile.type
                });

                const formData = new FormData(form);
                debugLog('FormData created');

                submitBtn.disabled = true;
                progress.style.display = 'block';
                log.style.display = 'block';
                log.innerHTML = '';
                result.style.display = 'none';
                result.classList.remove('error');
                debugLog('UI updated for processing');

                try {
                    debugLog('Starting fetch to /process');
                    const response = await fetch('/process', {
                        method: 'POST',
                        body: formData
                    });

                    debugLog('Response received', {
                        status: response.status,
                        statusText: response.statusText,
                        ok: response.ok,
                        headers: Object.fromEntries(response.headers.entries())
                    });

                if (!response.ok) {
                    debugLog('Response not OK, throwing error');
                    throw new Error('Server error: ' + response.status + ' ' + response.statusText);
                }

                debugLog('Starting to read response stream');
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let chunkCount = 0;

                while (true) {
                    const { value, done } = await reader.read();
                    chunkCount++;

                    if (done) {
                        debugLog('Stream complete', {totalChunks: chunkCount});
                        break;
                    }

                    const chunk = decoder.decode(value);
                    debugLog('Chunk ' + chunkCount + ' received', {length: chunk.length, preview: chunk.substring(0, 100)});

                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (!line.trim()) continue;

                        if (line.startsWith('data: ')) {
                            const data = JSON.parse(line.substring(6));

                            if (data.type === 'log') {
                                log.innerHTML += data.message + '<br>';
                                log.scrollTop = log.scrollHeight;
                            } else if (data.type === 'progress') {
                                statusText.textContent = data.message;
                                if (data.percent) {
                                    progressFill.style.width = data.percent + '%';
                                }
                            } else if (data.type === 'complete') {
                                result.innerHTML = '<h3>✅ Success!</h3>' +
                                    '<p>' + data.message + '</p>' +
                                    '<a href="/download/' + data.filename + '" download>' +
                                        '<button>⬇️ Download Processed Video</button>' +
                                    '</a>';
                                result.style.display = 'block';
                                progress.style.display = 'none';
                            } else if (data.type === 'error') {
                                result.innerHTML = '<h3>❌ Error</h3><p>' + data.message + '</p>';
                                result.classList.add('error');
                                result.style.display = 'block';
                                progress.style.display = 'none';
                            }
                        }
                    }
                }
            } catch (error) {
                debugLog('ERROR during processing', {
                    message: error.message,
                    stack: error.stack,
                    name: error.name
                });
                result.innerHTML = '<h3>❌ Error</h3><p>' + error.message + '</p>';
                result.classList.add('error');
                result.style.display = 'block';
                progress.style.display = 'none';
            } finally {
                submitBtn.disabled = false;
                debugLog('Processing complete - submit button re-enabled');
            }
            }

            // Check health on page load
            debugLog('Fetching health check');
            fetch('/health')
                .then(function(r) {
                    debugLog('Health check response', {status: r.status});
                    return r.json();
                })
                .then(function(data) {
                    debugLog('Health check data', data);
                })
                .catch(function(err) {
                    debugLog('Health check ERROR', {message: err.message, stack: err.stack});
                });

            debugLog('Script initialization complete');
            updateDebugDisplay();
            document.getElementById('scriptStatus').textContent = 'LOADED ✓';
        })();
    </script>
</body>
</html>
'''

@app.route('/health')
def health():
    """Health check endpoint."""
    rife_available = False
    rife_error = None

    if PIPELINE_AVAILABLE:
        try:
            from .rife_bridge import check_rife_available
            rife_available = check_rife_available()
        except Exception as e:
            rife_error = str(e)
    else:
        rife_error = IMPORT_ERROR

    return jsonify({
        'status': 'ok',
        'pipeline_available': PIPELINE_AVAILABLE,
        'rife_available': rife_available,
        'error': rife_error
    })

@app.route('/')
def index():
    """Render upload page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/process', methods=['POST'])
def process():
    """Process uploaded video."""
    import json
    from flask import Response

    def generate():
        try:
            # Check if pipeline is available
            if not PIPELINE_AVAILABLE:
                error_msg = f"Pipeline not available. Error: {IMPORT_ERROR}"
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return

            # Get uploaded file
            if 'video' not in request.files:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No video file uploaded'})}\n\n"
                return

            video = request.files['video']
            if video.filename == '':
                yield f"data: {json.dumps({'type': 'error', 'message': 'No file selected'})}\n\n"
                return

            # Get parameters
            fps = float(request.form.get('fps', 30))
            threshold = float(request.form.get('threshold', 0.30))
            bridge = float(request.form.get('bridge', 0.5))
            audio_mode = request.form.get('audio', 'keep-original')

            # Save uploaded file
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], video.filename)
            video.save(input_path)

            yield f"data: {json.dumps({'type': 'log', 'message': f'Uploaded: {video.filename}'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Uploaded file', 'percent': 5})}\n\n"

            # Create output path
            output_filename = Path(video.filename).stem + '__rife_smooth.mp4'
            output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

            # Create config
            config = Config(
                fps=fps,
                scene_threshold=threshold,
                bridge_duration=bridge,
                audio_mode=audio_mode,
            )

            yield f"data: {json.dumps({'type': 'log', 'message': 'Starting pipeline...'})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Initializing', 'percent': 10})}\n\n"

            # Progress callback
            def progress_callback(msg):
                yield f"data: {json.dumps({'type': 'log', 'message': msg})}\n\n"

            # Run pipeline
            pipeline = Pipeline(config, progress_callback=progress_callback)

            yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing video', 'percent': 20})}\n\n"

            result_path = pipeline.run(input_path, output_path)

            yield f"data: {json.dumps({'type': 'progress', 'message': 'Complete!', 'percent': 100})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Video processed successfully!', 'filename': output_filename})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/download/<filename>')
def download(filename):
    """Download processed video."""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
