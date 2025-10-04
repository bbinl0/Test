from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
import urllib.request
import urllib.error

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse the query string
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        # Get username or identifier from query params
        username = query_params.get('username', [''])[0] or query_params.get('identifier', [''])[0]
        
        if not username:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Please provide username or identifier parameter')
            return
        
        # Forward request to Railway API
        railway_api_url = f'https://web-production-27209.up.railway.app/get_user_info?username={quote(username)}'
        
        try:
            with urllib.request.urlopen(railway_api_url) as response:
                data = response.read()
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                
        except urllib.error.HTTPError as e:
            # Forward error from Railway API
            error_data = e.read()
            self.send_response(e.code)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_data)
            
        except Exception as e:
            # Handle other errors
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f'Error: {str(e)}'.encode())
