"""Zero-dependency HTTP server: serves the UI and the JSON API."""
import json, mimetypes, os, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from . import market
from .engine import Store

FRONT = Path(__file__).resolve().parents[2] / "frontend"
PROTO = FRONT.parent / "proto.html"


def make_handler(store):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/api/state": return self._send(200, store.state())
            if u.path == "/api/whatif":
                q = parse_qs(u.query)
                try:
                    qty = float(q["qty"][0])
                    if not 0 <= qty <= 10000: raise ValueError
                    return self._send(200, store.whatif(q.get("outlet", ["14"])[0], q.get("sku", ["tomato"])[0], qty))
                except (KeyError, ValueError, StopIteration): return self._send(400, {"error": "bad parameters"})
            if u.path == "/api/context":
                o = parse_qs(u.query).get("outlet", [""])[0]
                if o not in ("14", "27"): return self._send(400, {"error": "unknown outlet"})
                return self._send(200, store.context(o))
            if u.path == "/api/market": return self._send(200, market.market_data())
            if u.path == "/api/health": return self._send(200, {"ok": True})
            if u.path == "/proto.html" and PROTO.is_file():
                return self._send(200, PROTO.read_bytes(), "text/html; charset=utf-8")
            name = "index.html" if u.path == "/" else u.path.lstrip("/")
            f = (FRONT / name).resolve()
            if FRONT in f.parents and f.is_file():
                return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
            self._send(404, {"error": "not found"})

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}") if n < 20000 else {}
                p = urlparse(self.path).path
                if m := re.fullmatch(r"/api/drafts/(14|27)/approve", p):
                    store.approve(m[1], body.get("role", "outlet"), body.get("overrides", {}))
                elif m := re.fullmatch(r"/api/drafts/(14|27)/reject", p): store.reject(m[1], body.get("reason", "Other"))
                elif p == "/api/logs": return self._send(200, store.log(str(body.get("outlet", "")), str(body.get("text", "")), body.get("source", "text")))
                elif m := re.fullmatch(r"/api/logs/(\d+)/confirm", p): store.confirm_log(int(m[1]))
                elif m := re.fullmatch(r"/api/lots/(\w+)/safety", p): store.safety(m[1])
                elif p == "/api/actions/apply": store.apply(str(body.get("id", "")))
                elif m := re.fullmatch(r"/api/outlets/(14|27)/location", p):
                    store.set_location(m[1], body.get("lat"), body.get("lng"), body.get("radius", 1100))
                elif p == "/api/close-day": store.close_day()
                elif p == "/api/reset": store.reset()
                else: return self._send(404, {"error": "not found"})
                self._send(200, {"ok": True})
            except PermissionError as e: self._send(403, {"error": str(e)})
            except (ValueError, StopIteration, KeyError, json.JSONDecodeError) as e: self._send(400, {"error": str(e) or "bad request"})

    return H


def main():
    port = int(os.environ.get("PORT", 8000))
    srv = ThreadingHTTPServer(("0.0.0.0", port), make_handler(Store()))
    print(f"ResourceLeak AI running at http://localhost:{port}")
    srv.serve_forever()


if __name__ == "__main__": main()
