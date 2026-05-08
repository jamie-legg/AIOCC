"""Ngrok manager for creating public tunnels for OAuth callbacks."""

import os
import time
import threading
from typing import Optional, Dict, Any
from pyngrok import ngrok, conf
from pyngrok.exception import PyngrokError

class NgrokManager:
    """Manages ngrok tunnels for OAuth callbacks."""
    
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token or os.getenv("NGROK_AUTH_TOKEN")
        self.tunnel = None
        self.public_url = None
        self._setup_ngrok()
    
    def _setup_ngrok(self):
        """Set up ngrok with authentication token if provided."""
        if self.auth_token:
            try:
                ngrok.set_auth_token(self.auth_token)
                print("[SUCCESS] Ngrok authenticated successfully")
            except PyngrokError as e:
                print(f"[WARNING] Ngrok authentication failed: {e}")
                print("You can still use ngrok without authentication (with limitations)")
        else:
            print("[WARNING] No NGROK_AUTH_TOKEN found. Using ngrok without authentication.")
            print("For better reliability, get a free token at https://dashboard.ngrok.com/get-started/your-authtoken")
    
    def start_tunnel(self, port: int = 18473, domain: Optional[str] = None) -> Optional[str]:
        """Start an ngrok tunnel for the specified port."""
        try:
            # Kill any existing ngrok processes first
            self._kill_existing_ngrok()
            
            # Create tunnel with optional domain
            if domain:
                self.tunnel = ngrok.connect(port, "http", domain=domain)
            else:
                self.tunnel = ngrok.connect(port, "http")
            
            self.public_url = self.tunnel.public_url
            
            print(f"[SUCCESS] Ngrok tunnel started successfully")
            print(f"[NGROK] Public URL: {self.public_url}")
            print(f"🔗 Callback URL: {self.public_url}/callback")
            
            return self.public_url
            
        except PyngrokError as e:
            error_msg = str(e)
            if "simultaneous ngrok agent sessions" in error_msg:
                print("[WARNING]  Another ngrok session is running. Attempting to kill it...")
                self._kill_existing_ngrok()
                try:
                    # Try again after killing existing sessions
                    if domain:
                        self.tunnel = ngrok.connect(port, "http", domain=domain)
                    else:
                        self.tunnel = ngrok.connect(port, "http")
                    self.public_url = self.tunnel.public_url
                    print(f"[SUCCESS] Ngrok tunnel started successfully after cleanup")
                    print(f"[NGROK] Public URL: {self.public_url}")
                    print(f"🔗 Callback URL: {self.public_url}/callback")
                    return self.public_url
                except PyngrokError as e2:
                    print(f"[ERROR] Still failed after cleanup: {e2}")
                    return None
            else:
                print(f"[ERROR] Failed to start ngrok tunnel: {e}")
                return None
        except Exception as e:
            print(f"[ERROR] Unexpected error starting ngrok: {e}")
            return None
    
    def _kill_existing_ngrok(self):
        """Kill any existing ngrok processes."""
        import subprocess
        import os
        
        try:
            # Kill ngrok processes
            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/f', '/im', 'ngrok.exe'], 
                             capture_output=True, check=False)
            else:  # Unix-like systems
                subprocess.run(['pkill', '-f', 'ngrok'], 
                             capture_output=True, check=False)
            
            # Give it a moment to clean up
            import time
            time.sleep(1)
            
        except Exception as e:
            print(f"[WARNING]  Could not kill existing ngrok processes: {e}")
    
    def stop_tunnel(self):
        """Stop the ngrok tunnel."""
        if self.tunnel:
            try:
                ngrok.disconnect(self.tunnel.public_url)
                print("[SUCCESS] Ngrok tunnel stopped")
            except PyngrokError as e:
                print(f"[WARNING]  Error stopping ngrok tunnel: {e}")
            finally:
                self.tunnel = None
                self.public_url = None
    
    def get_callback_url(self) -> Optional[str]:
        """Get the callback URL for OAuth."""
        if self.public_url:
            return f"{self.public_url}/callback"
        return None
    
    def is_tunnel_active(self) -> bool:
        """Check if the tunnel is currently active."""
        return self.tunnel is not None and self.public_url is not None
    
    def get_tunnel_info(self) -> Dict[str, Any]:
        """Get information about the current tunnel."""
        if not self.is_tunnel_active():
            return {"active": False}
        
        return {
            "active": True,
            "public_url": self.public_url,
            "callback_url": self.get_callback_url(),
            "tunnel_name": self.tunnel.name if self.tunnel else None
        }

def create_oauth_tunnel(port: int = 18473, auth_token: Optional[str] = None) -> Optional[NgrokManager]:
    """Create an ngrok tunnel for OAuth callbacks."""
    manager = NgrokManager(auth_token)
    
    if manager.start_tunnel(port):
        return manager
    else:
        return None

def test_ngrok():
    """Test ngrok functionality."""
    print("Testing ngrok functionality...")
    
    manager = NgrokManager()
    
    if manager.start_tunnel():
        print("[SUCCESS] Ngrok test successful!")
        print(f"Tunnel info: {manager.get_tunnel_info()}")
        
        # Keep tunnel open for a few seconds to test
        print("Tunnel will stay open for 10 seconds for testing...")
        time.sleep(10)
        
        manager.stop_tunnel()
        print("[SUCCESS] Test completed")
    else:
        print("[ERROR] Ngrok test failed")

if __name__ == "__main__":
    test_ngrok()
