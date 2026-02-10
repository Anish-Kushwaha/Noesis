from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    # ---------- Common helpers ----------

    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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

    def _build_graph_from_notes(self, notes):
        """Convert a list of notes into D3-ready nodes and edges."""
        nodes = []
        edges = []

        # Node map to avoid duplicates by id
        seen_ids = set()

        for note in notes:
            node_id = note.get("id")
            if not node_id or not isinstance(node_id, str):
                continue

            if node_id in seen_ids:
                continue

            seen_ids.add(node_id)

            node = {
                "id": node_id,
                "title": note.get("title", node_id),
                "domain": note.get("domain", "default")
            }
            nodes.append(node)

        for note in notes:
            source_id = note.get("id")
            if not source_id or not isinstance(source_id, str):
                continue

            links = note.get("links", [])
            if not isinstance(links, list):
                continue

            for target_id in links:
                if not isinstance(target_id, str):
                    continue
                edges.append({
                    "source": source_id,
                    "target": target_id
                })

        return {
            "nodes": nodes,
            "edges": edges
        }

    def do_OPTIONS(self):
        self._set_headers(204)
        return

    # ---------- GET /api/graph ----------

    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        example_mode = query_params.get("example", ["false"])[0].lower() == "true"

        if example_mode:
            notes = [
                {
                    "id": "noesis-core",
                    "title": "Noesis: Personal Knowledge OS",
                    "domain": "meta",
                    "links": ["atomic-knowledge", "graph-thinking", "questions-first"]
                },
                {
                    "id": "atomic-knowledge",
                    "title": "Atomic Knowledge",
                    "domain": "practice",
                    "links": ["noesis-core"]
                },
                {
                    "id": "graph-thinking",
                    "title": "Thinking in Graphs",
                    "domain": "theory",
                    "links": ["noesis-core"]
                },
                {
                    "id": "questions-first",
                    "title": "Questions as First-Class Citizens",
                    "domain": "principle",
                    "links": ["noesis-core"]
                }
            ]
            graph = self._build_graph_from_notes(notes)
            message = "Example graph for Noesis core concepts."
        else:
            graph = {"nodes": [], "edges": []}
            message = (
                "No server-side graph persistence. "
                "Send notes via POST /api/graph to compute a graph."
            )

        payload = {
            "graph": graph,
            "message": message
        }

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(payload).encode("utf-8"))
        return

    # ---------- POST /api/graph ----------

    def do_POST(self):
        body = self._read_json_body()
        if body is None:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "Invalid or missing JSON body"
            }).encode("utf-8"))
            return

        notes = body.get("notes")
        if notes is None or not isinstance(notes, list):
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "error": "'notes' must be a list of note objects"
            }).encode("utf-8"))
            return

        graph = self._build_graph_from_notes(notes)
        payload = {
            "graph": graph,
            "message": "Graph computed from provided notes (stateless)."
        }

        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(payload).encode("utf-8"))
        return
