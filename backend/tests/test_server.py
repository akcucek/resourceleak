import json, threading, unittest, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from resourceleak.engine import Store
from resourceleak.server import make_handler


class Api(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Store(":memory:")))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}"

    def tearDown(self): self.srv.shutdown()

    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.load(r)
        except urllib.error.HTTPError as e: return e.code, json.load(e)

    def line(self, st, o, sku): return next(l for d in st["drafts"] if d["outlet"] == o for l in d["lines"] if l["sku"] == sku)

    def test_state_and_ui(self):
        _, st = self.call("/api/state")
        self.assertEqual(self.line(st, "14", "tomato")["order"], 61)
        self.assertTrue(st["strip"]["at_risk"] > 0 and st["strip"]["recover"] > 0)
        with urllib.request.urlopen(self.base + "/") as r: self.assertIn(b"ResourceLeak", r.read())

    def test_market_api_and_prototype_route(self):
        data = {"source": "not_configured", "state": "Karnataka", "prices": {}, "note": "demo"}
        with patch("resourceleak.server.market.market_data", return_value=data):
            status, result = self.call("/api/market")
        self.assertEqual((status, result["source"]), (200, "not_configured"))
        with urllib.request.urlopen(self.base + "/proto.html") as response:
            self.assertIn(b"Local crop demand", response.read())

    def test_hq_gate_and_validation(self):
        _, st = self.call("/api/state")
        big = next(d for d in st["drafts"] if d["needs_hq"])["outlet"]
        self.assertEqual(self.call(f"/api/drafts/{big}/approve", {"role": "outlet"})[0], 403)
        self.assertEqual(self.call(f"/api/drafts/{big}/approve", {"role": "hq", "overrides": {"banana": -5}})[0], 400)
        self.assertEqual(self.call(f"/api/drafts/{big}/approve", {"role": "hq"})[0], 200)
        self.assertEqual(self.call(f"/api/drafts/{big}/approve", {"role": "hq"})[0], 400)  # already approved
        self.assertEqual(self.call("/api/whatif?qty=abc")[0], 400)

    def test_closed_loop(self):
        _, st = self.call("/api/state")
        before = self.line(st, "14", "banana")["order"]
        tr = next(a for p in st["plans"].values() for a in p if a["route"] == "transfer" and a["lot"] == "ba27")
        self.assertEqual(self.call("/api/actions/apply", {"id": tr["id"]})[0], 200)
        _, st = self.call("/api/state")
        self.assertEqual(self.line(st, "14", "banana")["order"], before - tr["qty"])  # no double count
        self.assertEqual(self.call("/api/actions/apply", {"id": tr["id"]})[0], 400)
        don = "br14:donate"
        self.assertEqual(self.call("/api/actions/apply", {"id": don})[0], 403)  # food-safety gate
        self.call("/api/lots/br14/safety", {})
        self.assertEqual(self.call("/api/actions/apply", {"id": don})[0], 200)
        self.call("/api/close-day", {})
        _, st = self.call("/api/state")
        self.assertTrue(st["lotrows"] and st["carry"]["meals"] > 146)
        self.assertTrue(all(r["real"] >= 0 for r in st["lotrows"]))

    def test_logs_change_risk(self):
        _, st = self.call("/api/state")
        stock = next(l for l in st["lots"] if l["id"] == "ba27")["stock"]
        s, rec = self.call("/api/logs", {"outlet": "27", "text": "3 kg banana overripe"})
        self.assertEqual((s, rec["status"]), (200, "logged"))
        _, st = self.call("/api/state")
        self.assertEqual(next(l for l in st["lots"] if l["id"] == "ba27")["stock"], stock - 3)
        s, rec = self.call("/api/logs", {"outlet": "14", "text": "five kg tomato spoiled", "source": "voice"})
        self.assertEqual(rec["status"], "needs_confirmation")
        self.assertEqual(self.call(f"/api/logs/{rec['id']}/confirm", {})[0], 200)
        self.assertEqual(self.call("/api/logs", {"outlet": "99", "text": "x"})[0], 400)


if __name__ == "__main__": unittest.main()


class ContextApi(Api):
    def test_context_and_location(self):
        s, c = self.call("/api/context?outlet=14")
        self.assertEqual((s, c["source"]), (200, "synthetic")); self.assertGreater(c["vector"]["stay"], 3)
        self.assertEqual(self.call("/api/context?outlet=99")[0], 400)
        self.assertEqual(self.call("/api/outlets/14/location", {"lat": 12.97, "lng": 77.59, "radius": 900})[0], 200)
        self.assertEqual(self.call("/api/outlets/14/location", {"lat": 999, "lng": 0})[0], 400)
