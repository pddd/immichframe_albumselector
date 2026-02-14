import http.server
import socketserver
import urllib.request
import urllib.parse
import sys
import json

PORT = 8000

class ProxyRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/proxy'):
            self.handle_proxy()
        else:
            super().do_GET()

    def handle_proxy(self):
        # Parse URL parameters
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'url' not in params:
            self.send_error(400, "Missing 'url' parameter")
            return

        target_url = params['url'][0]
        
        # Forward headers (specifically x-api-key)
        req_headers = {}
        if 'x-api-key' in self.headers:
            req_headers['x-api-key'] = self.headers['x-api-key']
        
        # Also check for 'apiKey' in query params to support <img> tags
        if 'apiKey' in params:
            req_headers['x-api-key'] = params['apiKey'][0]

        if 'Accept' in self.headers:
             req_headers['Accept'] = self.headers['Accept']

        try:
            # Create request
            req = urllib.request.Request(target_url, headers=req_headers)
            
            # Execute request
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                
                # Copy response headers
                for key, value in response.getheaders():
                    # Skip CORS headers from upstream as we set our own
                    if key.lower() not in ['access-control-allow-origin', 'content-encoding', 'content-length', 'transfer-encoding']:
                        self.send_header(key, value)
                
                # Add CORS headers
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Headers', 'x-api-key')
                self.end_headers()
                
                # Pipe data
                self.wfile.write(response.read())
                
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(500, str(e))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'x-api-key, Content-Type')
        self.end_headers()

if __name__ == "__main__":
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), ProxyRequestHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print(f"Proxy endpoint available at http://localhost:{PORT}/proxy?url=...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
