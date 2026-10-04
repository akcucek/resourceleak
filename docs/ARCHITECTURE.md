# Architecture
Frontend (static HTML now, React/Vite later) -> stdlib HTTP server (server.py) -> engine.py (state, orchestration) -> pure-Python domain modules
(`forecast`, `spoilage`, `rescue`, `ledger`, `context`, `llm`) -> SQLite (single JSON state doc; fine at demo scale).

| Stage | Module | Tech |
|---|---|---|
| Prevent | forecast.py, context.py | Newsvendor with markdown salvage, H3 place-type vectors, cosine twins |
| Detect | llm.py, spoilage.py | Gemini extraction + schema validation; rule-based risk |
| Rescue | rescue.py | Waste-hierarchy allocator |
| Prove | ledger.py | Estimated vs realized vs baseline |

Design rule: the LLM extracts and explains; deterministic code decides money and quantities.
