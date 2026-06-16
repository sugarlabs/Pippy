#!/usr/bin/python3
"""Simple Code Llama server for Pippy integration

This script provides a simple HTTP server that uses Ollama to run Code Llama
and makes it available to Pippy via a REST API.

Requirements:
- Ollama installed and running locally
- Code Llama model pulled in Ollama

Usage:
python3 codellama_server.py [--model MODEL_NAME] [--port PORT] [--ollama-url OLLAMA_URL]
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import argparse
import os
import sys
import urllib.request
import urllib.error
import socket
import logging
import time
from urllib.error import URLError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default Ollama model to use
DEFAULT_MODEL = "codellama:7b-code"
# Default Ollama API URL
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
# Maximum number of retries
MAX_RETRIES = 3
# Retry delay in seconds
RETRY_DELAY = 2
# Default max tokens
DEFAULT_MAX_TOKENS = 100
# Connection timeout in seconds
CONNECTION_TIMEOUT = 120

class CodeLlamaHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Get the server instance
        self.server = args[2]
        # Get model and URL from the server
        self.model_name = self.server.model_name if hasattr(self.server, 'model_name') else DEFAULT_MODEL
        self.ollama_url = self.server.ollama_url if hasattr(self.server, 'ollama_url') else DEFAULT_OLLAMA_URL
        # Call parent constructor with all original arguments
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override to prevent logging of every request"""
        pass
    
    def check_ollama_health(self):
        """Check if Ollama is running and accessible"""
        try:
            test_data = json.dumps({
                "model": self.model_name,
                "prompt": "test",
                "max_tokens": 10
            }).encode('utf-8')
            req = urllib.request.Request(
                self.ollama_url,
                data=test_data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            response = urllib.request.urlopen(req, timeout=10)
            if response.status == 200:
                return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
        return False
    
    def make_ollama_request(self, data_json):
        """Make a request to Ollama with retry logic"""
        if not self.check_ollama_health():
            raise Exception("Ollama is not running or not accessible")
            
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Making request to Ollama (attempt {attempt + 1}/{MAX_RETRIES})")
                req = urllib.request.Request(
                    self.ollama_url,
                    data=data_json,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=CONNECTION_TIMEOUT) as response:
                    if response.status == 200:
                        logger.info("Successfully received response from Ollama")
                        return response.read().decode('utf-8')
                    else:
                        logger.warning(f"Received non-200 status code: {response.status}")
            except (URLError, socket.timeout) as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"All attempts failed. Last error: {str(e)}")
                    raise Exception(f"Request timed out after {MAX_RETRIES} attempts. Ollama may be overloaded or not responding properly.")
        return None
    
    def do_POST(self):
        """Handle POST requests"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            if self.path == "/suggestions":
                # Existing code suggestions endpoint
                code = data.get('code', '')
                max_tokens = min(data.get('max_tokens', DEFAULT_MAX_TOKENS), DEFAULT_MAX_TOKENS)
                
                if not code.strip():
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'No code provided'}).encode())
                    return
                
                prompt = f"""Analyze this Python code:

```python
{code}
```

Provide a concise analysis:
1. What it does (1-2 sentences)
2. Key improvements (2-3 points)
3. Critical issues (if any)"""

                request_data = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                    "stream": False,
                    "num_ctx": 2048,  # Limit context window
                    "num_thread": 4   # Limit CPU threads
                }
                
            elif self.path == "/chat":
                # New chat endpoint
                message = data.get('message', '')
                if not message.strip():
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'No message provided'}).encode())
                    return
                
                request_data = {
                    "model": self.model_name,
                    "prompt": message,
                    "max_tokens": 100,  # Limit chat response length
                    "temperature": 0.7,  # Slightly higher for chat
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                    "stream": False,
                    "num_ctx": 2048,
                    "num_thread": 4
                }
                
            else:
                self.send_response(404)
                self.end_headers()
                return

            logger.info("Generating response...")
            logger.info(f"Using model: {self.model_name}")
            logger.info("Sending request to Ollama...")
            
            data_json = json.dumps(request_data).encode('utf-8')
            response_text = self.make_ollama_request(data_json)
            
            if response_text:
                response_data = json.loads(response_text)
                if self.path == "/suggestions":
                    result = response_data.get('response', '')
                    if not result.strip():
                        result = "No suggestions available at this time."
                    response = {'suggestions': result}
                else:  # /chat endpoint
                    result = response_data.get('response', '')
                    if not result.strip():
                        result = "I couldn't generate a response. Please try again."
                    response = {'response': result}
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                logger.info("Response sent successfully")
            else:
                raise Exception("Failed to get response from Ollama")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid JSON data'}).encode())
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

def run_server(port=8080, model_name=DEFAULT_MODEL, ollama_url=DEFAULT_OLLAMA_URL):
    class CustomHTTPServer(HTTPServer):
        def __init__(self, server_address, RequestHandlerClass, model_name, ollama_url):
            self.model_name = model_name
            self.ollama_url = ollama_url
            super().__init__(server_address, RequestHandlerClass)
    
    server_address = ('', port)
    httpd = CustomHTTPServer(server_address, CodeLlamaHandler, model_name, ollama_url)
    logger.info(f"Starting Code Llama server on port {port}")
    logger.info(f"Using model: {model_name}")
    logger.info(f"Ollama API URL: {ollama_url}")
    logger.info("Press Ctrl+C to stop the server")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nServer stopped")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run a Code Llama server for Pippy integration')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                        help=f'Ollama model to use (default: {DEFAULT_MODEL})')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port to run the server on (default: 8080)')
    parser.add_argument('--ollama-url', type=str, default=DEFAULT_OLLAMA_URL,
                        help=f'Ollama API URL (default: {DEFAULT_OLLAMA_URL})')
    
    args = parser.parse_args()
    run_server(port=args.port, model_name=args.model, ollama_url=args.ollama_url) 