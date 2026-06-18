#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Test script to directly communicate with a running pylsp server.
This helps verify that the language server is working correctly.
"""

import json
import socket
import time

def send_request(sock, request):
    """Send a request to the pylsp server using the LSP protocol format"""
    content = json.dumps(request)
    header = f"Content-Length: {len(content)}\r\n\r\n"
    message = header.encode('utf-8') + content.encode('utf-8')
    
    print(f"Sending: {message}")
    sock.sendall(message)

def receive_response(sock):
    """Receive and parse a response from the pylsp server"""
    # Read the header
    header = b""
    while b"\r\n\r\n" not in header:
        chunk = sock.recv(1)
        if not chunk:
            break
        header += chunk
    
    if not header:
        return None
    
    print(f"Received header: {header}")
    
    # Parse content length
    content_length = None
    for line in header.split(b"\r\n"):
        if line.startswith(b"Content-Length: "):
            content_length = int(line[16:])
            break
    
    if content_length is None:
        print("No Content-Length header found")
        return None
    
    # Read the content
    content = b""
    while len(content) < content_length:
        chunk = sock.recv(content_length - len(content))
        if not chunk:
            break
        content += chunk
    
    print(f"Received content: {content}")
    
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None

def main():
    """Main function to test LSP completion"""
    # Sample Python code for testing
    sample_code = """
import os
import sys

def test_function():
    os.path.
"""
    
    # Connect to the running pylsp server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 2087))  # Default pylsp port
    
    # Initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": None,
            "rootUri": None,
            "capabilities": {
                "textDocument": {
                    "completion": {
                        "completionItem": {
                            "snippetSupport": False
                        }
                    }
                }
            }
        }
    }
    
    print("Sending initialize request...")
    send_request(sock, init_request)
    init_response = receive_response(sock)
    print("Initialize response:", json.dumps(init_response, indent=2))
    
    # Initialized notification
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    
    print("Sending initialized notification...")
    send_request(sock, initialized_notification)
    time.sleep(1)  # Give server time to process
    
    # Document change notification
    doc_change = {
        "jsonrpc": "2.0",
        "method": "textDocument/didChange",
        "params": {
            "textDocument": {
                "uri": "file:///test.py",
                "version": 1,
                "text": sample_code
            },
            "contentChanges": [
                {
                    "text": sample_code
                }
            ]
        }
    }
    
    print("Sending document change notification...")
    send_request(sock, doc_change)
    time.sleep(1)  # Give server time to process
    
    # Completion request
    completion_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/completion",
        "params": {
            "textDocument": {
                "uri": "file:///test.py"
            },
            "position": {
                "line": 5,  # 0-based line number where "os.path." is
                "character": 12   # 0-based character position after "os.path."
            }
        }
    }
    
    print("Sending completion request...")
    send_request(sock, completion_request)
    completion_response = receive_response(sock)
    print("Completion response:", json.dumps(completion_response, indent=2))
    
    # Close the connection
    sock.close()
    print("Connection closed")

if __name__ == "__main__":
    main() 