"""Application state + orchestration of Prevent -> Detect -> Rescue -> Prove. Stdlib only."""
import json, os, sqlite3, threading, zlib
from . import cloud, forecast, ledger, llm, places, rescue, spoilage

CO2E = float(os.environ.get("CO2E_KG_PER_KG_WASTE", 2.5))
ROUTE_COST = 140.0   # one truck run between the two outlets, charged once per route
MEAL_PER_LOAF = 1.5


def seed():
    P = lambda o, sku, name, unit, cost, price, sal, mu, sd, usual, why: dict(
        outlet=o, sku=sku, name=name, unit=unit, cost=cost, price=price, salvage=sal, mu=mu, sd=sd, usual=usual, why=why)
    return {
        "outlets": {"14": {"lat": 13.0213, "lng": 77.5675, "radius": 1100}, "27": {"lat": 12.9352, "lng": 77.6245, "radius": 1400}},  # demo coordinates
        "limit": float(os.environ.get("OUTLET_ORDER_LIMIT_INR", 9500)),
        "products": [
            P("14", "banana", "Bananas", "kg", 40, 68, 25, 138, 9, 120, "Exam week: evening fruit sales rose 31% in the last exam week."),
            P("14", "tomato", "Tomatoes", "kg", 28, 40, 12, 62, 8, 80, "22% spoiled in the last 14 days; humidity 78% on Mon-Tue."),
            P("14", "spinach", "Spinach", "bn", 12, 30, 10, 18, 3, 30, "Only 54% sold on the last 4 Mondays."),
            P("14", "cups", "Cut-fruit cups", "pc", 30, 55, 15, 75, 10, 60, "Sold out by 7 pm on 3 of the last 5 days."),
            P("27", "onion", "Onions", "kg", 25, 38, 15, 165, 10, 150, "Monday restock: weekend basket size up 12%."),
            P("27", "spinach", "Spinach", "bn", 12, 30, 10, 30, 3, 25, "Sold out on 3 of the last 4 Mondays."),
            P("27", "banana", "Bananas", "kg", 40, 68, 25, 92, 9, 110, "14% spoiled in the last 14 days."),
            P("27", "cups", "Ready-to-eat cups", "pc", 28, 50, 12, 22, 4, 40, "Only 41% sold over 4 weeks."),
        ],
        "lots": [  # stock on the shelf that the spoilage model watches
            dict(id="ba27", outlet="27", sku="banana", name="Bananas", unit="kg", qty=18, daily=3, life=1.0, hum=None, price=68, kind="sell", safe=False),
            dict(id="sp14", outlet="14", sku="spinach", name="Spinach", unit="bn", qty=14, daily=4, life=1.4, hum=78, price=30, kind="sell", safe=False),
            dict(id="pa27", outlet="27", sku="papaya", name="Papaya", unit="kg", qty=9, daily=2, life=1.5, hum=None, price=55, kind="sell", safe=False),
            dict(id="br14", outlet="14", sku="bread", name="Bread", unit="loaf", qty=40, daily=10, life=1.0, hum=78, price=40, kind="donate", safe=False),
        ],
        "history": [["7-13 Sep", 64, 41, 31200, 27900], ["14-20 Sep", 71, 52, 38600, 35100], ["21-27 Sep", 69, 55, 41300, 39800]],
        "week0": dict(recs=58, accepted=47, est=50900, real=48320, kg=312, meals=146),
        "drafts": {"14": {"status": "pending"}, "27": {"status": "pending"}},
        "transfers_in": {}, "actions": {}, "committed": [], "logs": [
            dict(id=1, outlet="14", text="Tomatoes about 6.5 kg overripe", sku="tomato", qty=6.5, unit="kg", reason="overripe",
                 status="logged", confidence=0.86, source="photo", engine="vision", time="07:42"),
        ], "next_log": 2, "closed": False,
    }


class Store:
    def __init__(self, path=None):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path or os.environ.get("RL_DB", "resourceleak.sqlite3"), check_same_thread=False)
        self.db.execute("create table if not exists kv(k text primary key, v text)")
        row = self.db.execute("select v from kv where k='state'").fetchone()
        self.s = json.loads(row[0]) if row else seed()
        self.save()

    def save(self):
        self.db.execute("insert or replace into kv values('state', ?)", (json.dumps(self.s),)); self.db.commit()

    def reset(self):
        with self.lock: self.s = seed(); self.save()

    # ---------- PREVENT ----------
    def _prod(self, o, sku):
        return next(p for p in self.s["products"] if p["outlet"] == o and p["sku"] == sku)

    def _draft(self, o):
        s, lines, value, saving = self.s, [], 0.0, 0.0
        final = s["drafts"][o].get("final", {})
        for p in (p for p in s["products"] if p["outlet"] == o):
            rec = int(forecast.optimal_order(p["mu"], p["sd"], p["cost"], p["price"], p["salvage"]))
            tin = int(s["transfers_in"].get(f'{o}:{p["sku"]}', 0))
            order = int(final.get(p["sku"], max(0, rec - tin)))
            m = lambda q: forecast.outcome(q, p["mu"], p["sd"], p["cost"], p["price"], p["salvage"])["margin"]
            saving += m(rec) - m(p["usual"]); value += order * p["cost"]
            why = p["why"] + (f' {tin} {p["unit"]} arrive by transfer (see Rescue).' if tin else "")
            lines.append(dict(sku=p["sku"], name=p["name"], unit=p["unit"], usual=p["usual"], need=rec, transfer_in=tin, order=order,
                              cost=p["cost"], why=why, conf="High" if p["sd"] / p["mu"] < 0.1 else "Medium", pm=int(p["sd"])))
        d = s["drafts"][o]
        return dict(outlet=o, status=d["status"], reason=d.get("reason"), value=round(value), saving=round(saving), lines=lines,
                    needs_hq=value > s["limit"])

    def whatif(self, o, sku, q):
        p = self._prod(o, sku)
        f = lambda x: forecast.outcome(x, p["mu"], p["sd"], p["cost"], p["price"], p["salvage"])
        a, u = f(q), f(p["usual"])
        best = int(forecast.optimal_order(p["mu"], p["sd"], p["cost"], p["price"], p["salvage"]))
        return dict(qty=q, cost=q * p["cost"], waste=a["waste"], stockout=a["stockout"], margin=a["margin"], best=best,
                    d_cost=q * p["cost"] - p["usual"] * p["cost"], d_waste=a["waste"] - u["waste"],
                    d_stockout=a["stockout"] - u["stockout"], d_margin=a["margin"] - u["margin"])

    def approve(self, o, role, overrides):
        with self.lock:
            d = self.s["drafts"][o]
            if d["status"] != "pending": raise ValueError("draft already " + d["status"])
            final = {}
            for ln in self._draft(o)["lines"]:
                q = overrides.get(ln["sku"], ln["order"])
                if not isinstance(q, (int, float)) or q < 0 or q > ln["need"] * 3: raise ValueError(f'invalid quantity for {ln["name"]}')
                final[ln["sku"]] = int(q)
            d["final"] = final
            if self._draft(o)["needs_hq"] and role != "hq": d.pop("final"); raise PermissionError("Above the outlet limit: HQ must approve")
            d["status"] = "approved"; self.save()

    def reject(self, o, reason):
        with self.lock:
            d = self.s["drafts"][o]
            if d["status"] != "pending": raise ValueError("draft already " + d["status"])
            d["status"], d["reason"] = "rejected", str(reason)[:80]; self.save()

    # ---------- DETECT ----------
    def _lot_view(self, lot):
        r = spoilage.assess(lot["qty"], lot["daily"], lot["life"], humidity=lot.get("hum"))
        unsold = int(r.expected_unsold)
        return dict(id=lot["id"], outlet=lot["outlet"], name=lot["name"], unit=lot["unit"], stock=lot["qty"], forecast=r.forecast_demand,
                    life=r.shelf_life_days, unsold=unsold, window=r.window_hours, level=r.level, kind=lot["kind"],
                    safe=lot["safe"], value_at_risk=round(unsold * lot["price"]) if lot["kind"] == "sell" else 0)

    def log(self, outlet, text, source="text"):
        with self.lock:
            if outlet not in ("14", "27"): raise ValueError("unknown outlet")
            e, status, engine = llm.extract(text, source)
            rec = dict(id=self.s["next_log"], outlet=outlet, text=text[:200], source=source, engine=engine, time="now",
                       status={"auto_logged": "logged"}.get(status, status), **(e or dict(sku="unknown", qty=0, unit="", reason="unknown", confidence=0)))
            self.s["next_log"] += 1; self.s["logs"].insert(0, rec)
            if rec["status"] == "logged": self._apply_log(rec)
            self.save(); return rec

    def confirm_log(self, lid):
        with self.lock:
            rec = next((l for l in self.s["logs"] if l["id"] == lid), None)
            if not rec or rec["status"] != "needs_confirmation": raise ValueError("nothing to confirm")
            rec["status"] = "logged"; self._apply_log(rec); self.save()

    def _apply_log(self, rec):  # a confirmed waste log removes that stock, which changes spoilage risk and rescue plans
        kg = rec["qty"] * llm.UNIT_TO_KG.get(rec["unit"], 1)
        for lot in self.s["lots"]:
            if lot["outlet"] == rec["outlet"] and lot["sku"] == rec["sku"]:
                same_unit = lot["unit"] == rec["unit"]
                lot["qty"] = max(0, lot["qty"] - (rec["qty"] if same_unit else kg))

    # ---------- RESCUE ----------
    def _plans(self):
        """Plan every lot. Committed lots keep their stored actions; others are recomputed live."""
        s, out, paid = self.s, {}, set()
        for lot in s["lots"]:
            v = self._lot_view(lot)
            if lot["id"] in s["committed"]:
                out[lot["id"]] = [dict(a, blocked=(None if (a["route"] != "donate" or lot["safe"]) else "food-safety check not confirmed"))
                                  for a in s["actions"].values() if a["lot"] == lot["id"]]
                continue
            needs = []
            for p in s["products"]:
                if p["sku"] == lot["sku"] and p["outlet"] != lot["outlet"]:
                    q = next(l for l in self._draft(p["outlet"])["lines"] if l["sku"] == p["sku"])["order"]
                    rk = "-".join(sorted((lot["outlet"], p["outlet"])))
                    needs.append(rescue.Need(p["outlet"], q, 0 if rk in paid else ROUTE_COST))
                    if q > 0 and v["unsold"] * lot["price"] - (0 if rk in paid else ROUTE_COST) > 1: paid.add(rk)
            acts = rescue.plan(v["unsold"], lot["price"], 25, needs=needs, markdown_qty=0 if lot["kind"] == "donate" else None,
                               food_safe_confirmed=lot["safe"], donate_ok=lot["kind"] == "donate")
            out[lot["id"]] = [dict(id=f'{lot["id"]}:{a.route}', lot=lot["id"], route=a.route, qty=int(a.qty), est=a.recovery, target=a.target,
                                   blocked=a.blocked_reason, status="planned", meals=round(a.qty * MEAL_PER_LOAF) if a.route == "donate" else 0)
                              for a in acts if int(a.qty) > 0]
        return out

    def safety(self, lot_id):
        with self.lock:
            lot = next(l for l in self.s["lots"] if l["id"] == lot_id); lot["safe"] = True; self.save()

    def apply(self, action_id):
        with self.lock:
            lot_id = action_id.split(":")[0]
            plans = self._plans()
            if lot_id not in plans: raise ValueError("unknown lot")
            act = next((a for a in plans[lot_id] if a["id"] == action_id), None)
            if not act: raise ValueError("unknown action")
            if act["blocked"]: raise PermissionError(act["blocked"])
            if act["status"] != "planned": raise ValueError("already " + act["status"])
            if lot_id not in self.s["committed"]:
                self.s["committed"].append(lot_id)
                for a in plans[lot_id]: self.s["actions"][a["id"]] = a
            act = self.s["actions"][action_id]; act["status"] = "applied"
            if act["route"] == "transfer":
                lot = next(l for l in self.s["lots"] if l["id"] == lot_id)
                k = f'{act["target"]}:{lot["sku"]}'; self.s["transfers_in"][k] = self.s["transfers_in"].get(k, 0) + act["qty"]
            self.save()

    # ---------- PROVE ----------
    def close_day(self):
        """Simulated end of day: realized = estimate x a deterministic 0.80-1.05 factor (replace with real POS data)."""
        with self.lock:
            for a in self.s["actions"].values():
                if a["status"] == "applied":
                    f = 0.80 + (zlib.crc32(a["id"].encode()) % 26) / 100
                    a["real"] = round(a["est"] * f); a["status"] = "measured"
            self.save()
            cloud.export([a for a in self.s["actions"].values() if a["status"] == "measured"])

    def outlet_loc(self, o):
        return self.s.get("outlets", seed()["outlets"])[o]

    def set_location(self, o, lat, lng, radius=1100):
        with self.lock:
            if o not in ("14", "27") or not places.valid_location(lat, lng, radius): raise ValueError("invalid location")
            self.s.setdefault("outlets", seed()["outlets"])[o] = {"lat": lat, "lng": lng, "radius": radius}; self.save()

    def context(self, o):
        other = "27" if o == "14" else "14"
        ov = places.get_context(other, self.outlet_loc(other))["vector"]
        return dict(places.get_context(o, self.outlet_loc(o), ov), outlet=o, location=self.outlet_loc(o))

    def state(self):
        with self.lock:
            s = self.s
            lots = [self._lot_view(l) for l in s["lots"]]
            plans = self._plans()
            acts = [a for p in plans.values() for a in p]
            sell = [a for a in acts if a["route"] in ("transfer", "markdown")]
            measured = [a for a in s["actions"].values() if a["status"] == "measured"]
            live = [a for a in s["actions"].values() if a["status"] in ("applied", "measured")]
            w0 = s["week0"]
            approved = sum(1 for d in s["drafts"].values() if d["status"] == "approved")
            est = w0["est"] + sum(a["est"] for a in live)
            real = w0["real"] + sum(a["real"] for a in measured)
            kg = w0["kg"] + sum(a["qty"] for a in measured if a["route"] != "donate")
            meals = w0["meals"] + sum(a["meals"] for a in measured if a["route"] == "donate")
            ratio = lambda e, r: round(100 * r / e) if e else None
            rows = [dict(week=h[0], recs=h[1], acc=h[2], est=h[3], real=h[4], pct=ratio(h[3], h[4])) for h in s["history"]]
            rows.append(dict(week="28 Sep - 4 Oct (to date)", recs=w0["recs"] + len(s["actions"]) + 2, acc=w0["accepted"] + len(live) + approved,
                             est=est, real=real, pct=ratio(est, real)))
            return dict(
                limit=s["limit"], drafts=[self._draft(o) for o in ("14", "27")], lots=lots, plans=plans, logs=s["logs"][:8],
                whatif=dict(self._prod("14", "tomato"), best=self.whatif("14", "tomato", 61)["best"], outlet="14"),
                strip=dict(at_risk=sum(l["value_at_risk"] for l in lots), recover=round(sum(a["est"] for a in sell)),
                           meals=sum(a["meals"] for a in acts if a["route"] == "donate")),
                carry=dict(real=real, kg=kg, co2e_t=round(kg * CO2E / 1000, 2), meals=meals,
                           pending=sum(1 for d in s["drafts"].values() if d["status"] == "pending")),
                ledger=rows, lotrows=[dict(lot=a["lot"], route=a["route"], qty=a["qty"], est=a["est"], real=a["real"]) for a in measured],
                applied=sum(1 for a in s["actions"].values() if a["status"] == "applied"))
