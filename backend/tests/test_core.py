import unittest
from resourceleak import context, forecast, ledger, llm, rescue, spoilage


class Core(unittest.TestCase):
    def test_newsvendor(self):
        self.assertEqual(forecast.optimal_order(62, 8, 28, 40, 12), 61)
        self.assertEqual(forecast.optimal_order(50, 5, 40, 30), 0)
        self.assertEqual(forecast.optimal_order(50, 0, 10, 20), 50)
        self.assertLessEqual(forecast.optimal_order(50, 5, 10, 20, budget=200), 20)

    def test_spoilage(self):
        r = spoilage.assess(14, 4, 1.0)
        self.assertEqual((r.expected_unsold, r.level), (10, "high"))
        self.assertEqual(spoilage.assess(10, 5, 0).expected_unsold, 10)
        with self.assertRaises(ValueError): spoilage.assess(-1, 1, 1)

    def test_rescue(self):
        a = rescue.plan(10, 30, needs=[rescue.Need("27", 7, 0)], markdown_qty=3)
        self.assertEqual([x.route for x in a], ["transfer", "markdown"])
        self.assertEqual(rescue.plan(5, 30, needs=[rescue.Need("27", 5, 500)])[0].route, "markdown")
        d = rescue.plan(40, 10, markdown_qty=0, donate_ok=True)[0]
        self.assertTrue(d.route == "donate" and d.blocked_reason)

    def test_ledger_context(self):
        es = [ledger.Entry("a", 100, 90), ledger.Entry("b", 50, None), ledger.Entry("c", 50, 0, accepted=False)]
        self.assertEqual(ledger.realized_ratio(es), 0.9)
        v = {"a": {"x": 1}, "b": {"x": 1, "y": .1}, "c": {"y": 1}}
        self.assertEqual(context.twins("a", v, k=1)[0]["outlet"], "b")

    def test_llm(self):
        self.assertEqual(llm.extract("5 kg tomatoes spoiled")[1], "auto_logged")
        e, s, _ = llm.extract("ಐದು ಕೆಜಿ ಟೊಮೆಟೊ ಹಾಳಾಗಿದೆ", source="voice")
        self.assertEqual((e["sku"], e["qty"], e["unit"], s), ("tomato", 5, "kg", "needs_confirmation"))
        self.assertEqual(llm.extract("hello world")[1], "needs_review")
        self.assertEqual(llm.extract("5000 kg tomatoes")[1], "needs_review")  # absurd qty rejected
        self.assertEqual(llm.extract("")[1], "needs_review")


if __name__ == "__main__": unittest.main()


class PlacesCloud(unittest.TestCase):
    def test_places_live_and_fallback(self):
        import os
        from resourceleak import places, cloud
        places._cache.clear()
        loc = {"lat": 13.0, "lng": 77.5, "radius": 1000}
        os.environ["GOOGLE_MAPS_API_KEY"] = "k"
        calls = []
        def fake(url, headers, body, timeout=8):
            calls.append((headers["X-Goog-Api-Key"], body["includedTypes"]))
            return {"places": [{"id": str(i)} for i in range(12 if "lodging" in body["includedTypes"] else 3)]}
        c = places.get_context("t1", loc, post=fake)
        self.assertEqual((c["source"], c["counts"]["stay"], len(calls)), ("google_places", 12, 6))
        self.assertEqual(c["vector"]["stay"], 2.0)                      # 12 / median 6
        places._cache.clear()
        def boom(*a, **k): raise OSError("quota")
        c = places.get_context("14", loc, post=boom)                      # API failure degrades to labelled synthetic
        self.assertEqual(c["source"], "synthetic"); self.assertIn("unavailable", c["note"])
        del os.environ["GOOGLE_MAPS_API_KEY"]; places._cache.clear()
        self.assertEqual(places.get_context("27", loc)["source"], "synthetic")
        self.assertFalse(places.valid_location(95, 0)); self.assertFalse(places.valid_location(1, 1, 10)); self.assertFalse(places.valid_location("a", 1))
        self.assertFalse(cloud.export([{"id": "a", "real": 1}]))          # disabled without BQ_DATASET
        self.assertEqual(cloud.build_rows([{"id": "a", "real": 5, "lot": "x"}])[0]["json"]["real"], 5)
