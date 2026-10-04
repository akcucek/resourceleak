# Edge cases and how they're handled
| Area | Edge case | Handling | Test |
|---|---|---|---|
| Order | zero demand, zero variance, price <= cost | order 0 / order the mean | test_newsvendor_edges |
| Order | budget cap, pack size, shelf capacity | caps in forecast.py; HQ approval above outlet limit | test_newsvendor_edges |
| Order | cold-start outlet, weak twins | twin similarity + low_confidence flag, trial range | test_ledger_and_context_and_llm |
| Order | model wrong (festival, supplier issue) | reject-with-reason feedback | UI |
| Spoilage | expired lot, no stock, humidity, bad input | expired = unsellable; 0 stock = low; ValueError | test_spoilage_edges |
| Detect | LLM misreads photo/voice, wrong unit, absurd qty | schema + range check, confidence threshold, human confirm | test_ledger_and_context_and_llm |
| Detect | mixed Kannada/Hindi/English, duplicate logs | keep raw text + language; dedupe by outlet/sku/time (TODO) | - |
| Rescue | transfer exceeds need or costs more than it earns | cap by need, skip if net <= 0 | test_rescue_no_double_count_and_gates |
| Rescue | same units sold twice | allocation never exceeds unsold | test_rescue_no_double_count_and_gates |
| Rescue | donation without food-safety check | blocked_reason, pickup blocked | test_rescue_no_double_count_and_gates |
| Rescue | partner no-show | fall down the hierarchy (TODO) | - |
| Prove | unmeasured/rejected actions, zero estimate | excluded; ratio None | test_ledger_and_context_and_llm |
| Prove | attribution, seasonality | per-outlet baseline; label estimates | docs |
| Data | privacy | synthetic only; aggregated place types, nothing about people | data/seed.py |
| Ops | secrets, API quota, LLM outage | .env, retries, manual-entry fallback | .env.example |
