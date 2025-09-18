import json, os, subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

# Define your services and (optional) hardware mapping:
from config_loader import get_config

config = get_config()

SERVICES = config.get('status_server.services', [])

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            data = []
            for svc in SERVICES:
                # get systemd state
                try:
                    s = subprocess.run(
                      ['systemctl', 'is-active', svc['unit']],
                      capture_output=True, text=True, check=False
                    ).stdout.strip()
                except Exception:
                    s = 'unknown'
                data.append({
                    'name': svc['name'],
                    'status': s,
                    'hardware': svc['hardware']
                })
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            return

        # serve static files (index.html, style.css)
        path = self.path.lstrip('/') or 'index.html'
        full = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(full) and os.path.isfile(full):
            ext = os.path.splitext(full)[1]
            ctype = {
              '.html':'text/html',
              '.css':'text/css',
              '.js':'application/javascript'
            }.get(ext, 'application/octet-stream')
            self.send_response(200)
            self.send_header('Content-Type',ctype)
            self.end_headers()
            with open(full, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    addr = (config.get('status_server.host', '0.0.0.0'), config.get('status_server.port', 9000))
    print(f"Serving status page on http://{addr[0]}:{addr[1]}")
    HTTPServer(addr, Handler).serve_forever()
