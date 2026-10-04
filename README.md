# ResourceLeak AI
Prevent -> Detect -> Rescue -> Prove. A working demo: real engine behind the UI, no installs needed (Python 3.10+ only).

## Run
    cd backend && python3 -m resourceleak      # then open http://localhost:8000
    cd backend && python3 -m unittest discover -s tests -v

## What actually works
- **Prevent:** order drafts computed live by a newsvendor model (with markdown salvage); edit lines, approve/reject with reason; HQ approval above the outlet limit is enforced server-side; what-if slider calls the backend.
- **Detect:** type/paste/voice-transcript waste logs (English, Kannada, Hindi keywords). Low-confidence and voice entries need confirmation. Confirmed logs remove stock and change spoilage risk and rescue plans. Set `GEMINI_API_KEY` to try Gemini extraction first (rules are the fallback; Gemini path is untested here).
- **Rescue:** per-lot plan down the waste hierarchy. Applying a transfer cuts the receiving outlet's order (no double counting). Donation is blocked until the food-safety check is confirmed.
- **Prove:** "Close the day" measures applied actions and updates the ledger, CO2e, meals. Realized values are simulated (80-105% of estimate); replace `Store.close_day` with POS data.
- State persists in SQLite (`resourceleak.sqlite3`). `POST /api/reset` restores the seed data.

## Not real yet
Seed data is synthetic; the Ask box, event radar, hex maps and new-outlet planner are still static mock content; no auth; BigQuery/Places Insights not connected.

Config (env): PORT, RL_DB, OUTLET_ORDER_LIMIT_INR, CO2E_KG_PER_KG_WASTE, GEMINI_API_KEY, GEMINI_MODEL.
Docs: docs/CLOUD.md (Google Maps + Cloud Run + BigQuery), docs/ARCHITECTURE.md, docs/EDGE_CASES.md, docs/GIT_WORKFLOW.md.
