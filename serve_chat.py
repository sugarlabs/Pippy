#!/usr/bin/python3
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class ChatHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/chat.html'
        return SimpleHTTPRequestHandler.do_GET(self)

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, ChatHandler)
    print(f"Starting chat server on port {port}")
    print("Open your browser and navigate to http://localhost:8000")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server() 