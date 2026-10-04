import unittest
from resourceleak import context, forecast, ledger, llm, market, rescue, spoilage


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

class MarketData(unittest.TestCase):
    def test_mandi_prices_are_normalized_and_filtered(self):
        from urllib.parse import parse_qs, urlparse
        calls = []
        def fake(url):
            calls.append(parse_qs(urlparse(url).query))
            return {"records": [
                {"Commodity": "Tomato", "Min_Price": "2000", "Max_Price": "3000", "Modal_Price": "2500", "Arrival_Date": "03/10/2026", "Market": "Old market"},
                {"commodity": "Tomato", "min_price": "2100", "max_price": "3100", "modal_price": "2600", "arrival_date": "04/10/2026", "market": "Bengaluru"},
                {"commodity": "Tomato", "min_price": "1900", "max_price": "2900", "modal_price": "2400", "arrival_date": "29/09/2026", "market": "Older market"},
                {"commodity": "Unknown", "min_price": "1", "max_price": "2", "modal_price": "1", "arrival_date": "05/10/2026"},
            ]}
        prices = market.fetch_prices("test-key", get=fake)
        self.assertEqual(prices["tomato"]["modal_price"], 2600)
        self.assertEqual(prices["tomato"]["market"], "Bengaluru")
        self.assertEqual(calls[0]["api-key"], ["test-key"])
        self.assertEqual(calls[0]["filters[state]"], ["Karnataka"])

    def test_market_without_key_is_explicitly_unconfigured(self):
        result = market.market_data(api_key="", get=lambda url: {})
        self.assertEqual(result["source"], "not_configured")
        self.assertIn("POS feed", result["note"])
