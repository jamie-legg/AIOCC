"""OAuth callback server for handling authentication flows."""

import socket
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any
import webbrowser
import time
from managers.ngrok_manager import NgrokManager

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callbacks."""
    
    def __init__(self, *args, callback_data=None, **kwargs):
        self.callback_data = callback_data
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests (OAuth callbacks)."""
        if self.path.startswith('/callback') or self.path.startswith('/api/oauth/'):
            # Parse query parameters
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # Extract authorization code or error
            if 'code' in query_params:
                code = query_params['code'][0]
                state = query_params.get('state', [None])[0]
                scopes = query_params.get('scopes', [None])[0]
                
                self.callback_data['code'] = code
                self.callback_data['state'] = state
                self.callback_data['scopes'] = scopes
                self.callback_data['error'] = None
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <head><title>Authentication Successful</title></head>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    <script>setTimeout(() => window.close(), 3000);</script>
                </body>
                </html>
                ''')
            elif 'error' in query_params:
                error = query_params['error'][0]
                error_description = query_params.get('error_description', ['Unknown error'])[0]
                self.callback_data['error'] = error
                self.callback_data['error_description'] = error_description
                self.callback_data['code'] = None
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f'''
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Error: {error}</p>
                    <p>Description: {error_description}</p>
                    <p>Please check the terminal for more details.</p>
                </body>
                </html>
                '''.encode())
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <head><title>Invalid Callback</title></head>
                <body>
                    <h1>Invalid Callback</h1>
                    <p>No authorization code or error found in callback.</p>
                </body>
                </html>
                ''')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

class OAuthCallbackServer:
    """Server for handling OAuth callbacks."""
    
    def __init__(self, port: int = 18473, use_ngrok: bool = True, ngrok_domain: Optional[str] = None):
        self.port = port
        self.server = None
        self.thread = None
        self.callback_data = {}
        self.use_ngrok = use_ngrok
        self.ngrok_manager = None
        self.ngrok_domain = ngrok_domain
    
    def start_server(self) -> bool:
        """Start the callback server."""
        try:
            # Find an available port
            self.port = self._find_available_port()
            
            # Create server with custom handler
            def handler(*args, **kwargs):
                return OAuthCallbackHandler(*args, callback_data=self.callback_data, **kwargs)
            
            self.server = HTTPServer(('localhost', self.port), handler)
            
            # Start server in a separate thread
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            print(f"Callback server started on http://localhost:{self.port}")
            
            # Start ngrok tunnel if enabled
            if self.use_ngrok:
                self.ngrok_manager = NgrokManager()
                if self.ngrok_manager.start_tunnel(self.port, domain=self.ngrok_domain):
                    print(f"[NGROK] Public callback URL: {self.ngrok_manager.get_callback_url()}")
                else:
                    print("[WARNING] Failed to start ngrok tunnel, using localhost only")
                    self.use_ngrok = False
            
            return True
            
        except Exception as e:
            print(f"Failed to start callback server: {e}")
            return False
    
    def stop_server(self):
        """Stop the callback server."""
        # Stop ngrok tunnel first
        if self.ngrok_manager:
            self.ngrok_manager.stop_tunnel()
            self.ngrok_manager = None
        
        # Stop HTTP server
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            if self.thread:
                self.thread.join(timeout=1)
    
    def _find_available_port(self) -> int:
        """Find an available port starting from the preferred port."""
        for port in range(self.port, self.port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        raise RuntimeError("No available ports found")
    
    def wait_for_callback(self, timeout: int = 300) -> Dict[str, Any]:
        """Wait for OAuth callback and return the result."""
        if not self.server:
            return {'error': 'Server not started'}
        
        print(f"Waiting for OAuth callback on http://localhost:{self.port}/callback...")
        print("If the browser doesn't open automatically, please visit the URL shown above.")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.callback_data:
                return self.callback_data
            time.sleep(0.1)
        
        return {'error': 'timeout', 'error_description': 'Callback timeout'}
    
    def get_callback_url(self) -> str:
        """Get the callback URL for this server."""
        if self.use_ngrok and self.ngrok_manager and self.ngrok_manager.is_tunnel_active():
            return self.ngrok_manager.get_callback_url()
        else:
            return f"http://localhost:{self.port}/callback"

def handle_oauth_flow(auth_url: str, port: int = 18473, use_ngrok: bool = True, server: Optional[OAuthCallbackServer] = None) -> Dict[str, Any]:
    """Handle complete OAuth flow with callback server."""
    if server is None:
        server = OAuthCallbackServer(port, use_ngrok=use_ngrok)
    
    try:
        # Start callback server if not already started
        if not server.server:
            if not server.start_server():
                return {'error': 'Failed to start callback server'}
        
        # Open browser to auth URL
        print(f"Opening browser to: {auth_url}")
        webbrowser.open(auth_url)
        
        # Wait for callback
        result = server.wait_for_callback()
        
        return result
        
    finally:
        # Don't stop the server here - let the caller handle it
        pass

def test_callback_server():
    """Test the callback server functionality."""
    server = OAuthCallbackServer()
    
    if server.start_server():
        print(f"Test server running on {server.get_callback_url()}")
        print("Visit the URL above to test the callback")
        
        try:
            result = server.wait_for_callback(timeout=30)
            print(f"Callback result: {result}")
        except KeyboardInterrupt:
            print("Test interrupted")
        finally:
            server.stop_server()
    else:
        print("Failed to start test server")

if __name__ == "__main__":
    test_callback_server()
