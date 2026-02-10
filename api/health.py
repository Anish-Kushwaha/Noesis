from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        # CORS is optional but useful for local testing and multi-origins
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        # CORS preflight support
        self._set_headers(204)
        return

    def do_GET(self):
        payload = {
            "status": "ok",
            "service": "noesis-backend",
            "version": "1.0.0",
            "description": "Noesis Python serverless backend health endpoint",
        }
        body = json.dumps(payload).encode("utf-8")

        self._set_headers(200, "application/json")
        self.wfile.write(body)
        return

    # Explicitly reject non-GET
    def do_POST(self):
        self._method_not_allowed(["GET"])

    def do_PUT(self):
        self._method_not_allowed(["GET"])

    def do_DELETE(self):
        self._method_not_allowed(["GET"])

    def _method_not_allowed(self, allowed_methods):
        self.send_response(405)
        self.send_header("Content-Type", "application/json")
        self.send_header("Allow", ", ".join(allowed_methods))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "error": "Method not allowed",
            "allowed": allowed_methods
        }).encode("utf-8"))
