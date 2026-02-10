from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    # ---------- Common helpers ----------

    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        # CORS for safety and local testing
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _read_json_body(self):
        content_length = self.headers.get("Content-Length")
        if not content_length:
            return None

        try:
            length = int(content_length)
        except ValueError:
            return None

        if length <= 0:
            return None

        raw_body = self.rfile.read(length)
        if not raw_body:
            return None

        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return None

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

    def do_OPTIONS(self):
        # CORS preflight
        self._set_headers(204)
        return

    # ---------- GET /api/notes ----------

    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        example_mode = query_params.get("example", ["false"])[0].lower() == "true"

        if example_mode:
            notes = [
                {
                    "id": "noesis-core",
                    "title": "Noesis: Personal Knowledge OS",
                    "markdown": (
                        "# Noesis

"
                        "Noesis is a personal knowledge operating system focused on **thinking** "
                        "over consumption. One idea per note, connected as a graph."
                    ),
                    "links": ["atomic-knowledge", "graph-thinking"],
                    "domain": "meta"
                },
                {
                    "id": "atomic-knowledge",
                    "title": "Atomic Knowledge",
                    "markdown": (
                        "# Atomic Knowledge

"
                        "Each note captures exactly one idea. This keeps knowledge granular "
                        "and composable."
                    ),
                    "links": ["noesis-core"],
                    "domain": "practice"
                },
                {
                    "id": "graph-thinking",
                    "title": "Thinking in Graphs",
                    "markdown": (
                        "# Thinking in Graphs

"
                        "Ideas connect as a graph rather than folders. Links represent "
                        "relationships between concepts."
                    ),
                    "links": ["noesis-core"],
                    "domain": "theory"
                }
            ]
        else:
            notes = []

        payload = {
            "notes": notes,
            "message": (
                "No server-side persistence in /api/notes. "
                "Use browser storage or an external DB for real data."
            )
        }

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(payload).encode("utf-8"))
        return

    # ---------- POST /api/notes ----------

    def do_POST(self):
        body = self._read_json_body()
        if body is None:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Invalid or missing JSON body"
            }).encode("utf-8"))
            return

        # Expect a single note object
        note = body

        note_id = note.get("id")
        markdown = note.get("markdown")
        title = note.get("title", "")

        if not note_id or not isinstance(note_id, str):
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Field 'id' is required and must be a non-empty string"
            }).encode("utf-8"))
            return

        if not markdown or not isinstance(markdown, str):
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Field 'markdown' is required and must be a non-empty string"
            }).encode("utf-8"))
            return

        if not isinstance(title, str):
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Field 'title' must be a string if provided"
            }).encode("utf-8"))
            return

        payload = {
            "message": "Note creation accepted (stateless). Persist this note on the client.",
            "note": note
        }

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(payload).encode("utf-8"))
        return

    # ---------- PUT /api/notes ----------

    def do_PUT(self):
        body = self._read_json_body()
        if body is None:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Invalid or missing JSON body"
            }).encode("utf-8"))
            return

        note = body
        note_id = note.get("id")
        if not note_id or not isinstance(note_id, str):
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Field 'id' is required and must be a non-empty string"
            }).encode("utf-8"))
            return

        payload = {
            "message": "Note update accepted (stateless). Apply this update on the client.",
            "note": note
        }

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(payload).encode("utf-8"))
        return

    # ---------- DELETE /api/notes ----------

    def do_DELETE(self):
        body = self._read_json_body()
        if body is None:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Invalid or missing JSON body"
            }).encode("utf-8"))
            return

        note_id = body.get("id")
        if not note_id or not isinstance(note_id, str):
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Field 'id' is required and must be a non-empty string"
            }).encode("utf-8"))
            return

        payload = {
            "message": "Note deletion accepted (stateless). Remove this note on the client.",
            "id": note_id
        }

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(payload).encode("utf-8"))
        return
