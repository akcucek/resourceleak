# ResourceLeak AI

ResourceLeak AI is an environmental resource-optimization prototype focused on food waste and sustainable agriculture. It aims to help retail buyers and hotels plan purchases, connect local demand with farmers, and help farmers make informed crop choices using soil information and market context.

The product direction is **Prevent -> Detect -> Rescue -> Prove**: prevent over-ordering, detect spoilage risk, rescue surplus through markdowns/transfers/donations, and measure outcomes. A separate buyer/farmer prototype explores demand sharing and soil-to-crop guidance for a Bengaluru/Karnataka pilot.

## Challenge and Approach

Over-ordering perishable food creates avoidable waste, cost, and emissions. Farmers may also lack timely buyer requirements, market-price context, and crop guidance based on their soil and local conditions. ResourceLeak aims to improve resource efficiency and sustainable decision-making across this local food chain.

The intended workflow is:

1. Participating retailers and hotels share crop, quantity, timing, and delivery-area needs from permissioned purchasing records.
2. The app retrieves dated Agmarknet mandi-price records for market context.
3. Farmers provide soil-test information, farm location, season, and water availability.
4. Locally reviewed rules compare buyer requirements with crop and farm conditions, showing data sources and uncertainty.
5. Farmers receive crop-specific skills and growing guidance and can express interest in supplying a buyer.
6. The pilot measures fulfilled demand, farmer outcomes, and food waste avoided against a stated baseline.

Mandi prices are not buyer demand or a guaranteed sale. The initial pilot is scoped to Bengaluru/Karnataka; expand only with validated local crop, market, and agronomy data.

### Users and Impact

- **Retail buyer or hotel:** shares crop requirements and uses purchasing and waste history to plan orders.
- **Farmer:** provides farm and soil information, reviews buyer and mandi signals, and receives locally reviewed crop and skill guidance.

Start with deterministic, reviewable rules; add predictive models only after enough permissioned, representative outcome data is available. Evaluate the pilot against a baseline using food waste avoided, buyer demand fulfilled, and farmer revenue after costs. Recommendations must show their source and uncertainty.

## Run

Requires Python 3.10+; the backend uses the standard library.

```sh
cd backend
python3 -m resourceleak
```

Open <http://localhost:8000/> for the retail food-waste demo or <http://localhost:8000/proto.html> for the buyer/farmer prototype.

Run backend tests:

```sh
cd backend
python3 -m unittest discover -s tests -v
```

## Current Features

- **Prevent:** newsvendor-based order drafts with markdown salvage; edit and approve/reject drafts; server-side HQ approval limits; backend-powered what-if analysis.
- **Detect:** enter typed, WhatsApp-style, or voice-transcribed waste logs in English, Kannada, or Hindi. Confirmation is required for uncertain entries. Confirmed logs update stock and spoilage risk. Gemini-assisted extraction is optional; rule-based extraction is the fallback.
- **Rescue:** per-lot markdown, transfer, donation, and compost/biogas routes. Transfers reduce the receiving outlet's order; food donations require a safety check.
- **Prove:** impact ledger for estimated and realized outcomes. End-of-day realized values are simulated in this demo and must be replaced with measured POS/partner data for real impact reporting.
- **Buyer/farmer prototype:** buyer demand examples and farmer soil-category examples, crop procedure checklists, and a buyer-to-farmer view. The demand figures and crop guidance are illustrative; the share button does not create a real order.
- State for the waste-reduction demo is stored in SQLite. `POST /api/reset` restores synthetic seed data.

## Data Sources and Trust

| Data | Source and purpose | Current status |
|---|---|---|
| Mandi prices and arrivals | [data.gov.in Agmarknet daily-price resource](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi), resource ID `9ef84268-d588-465a-a308-a864a43d0070` | `GET /api/market` is implemented. Configure `DATA_GOV_IN_API_KEY` and optionally `MARKET_STATE` (defaults to Karnataka). The UI shows no quote if live records are unavailable. |
| Buyer demand | Permissioned hotel/retailer POS or procurement export/API: crop or SKU, quantity, date, price, delivery area, stockouts, and waste | Prototype quantities and trends are synthetic. No POS integration or CSV import exists. Do not scrape private sales data. |
| Soil and farm conditions | Farmer-provided soil test or Soil Health Card, farm location, growing season, and water availability | Four-option soil-texture selector only. Uploads, farm profiles, and nutrient interpretation are not implemented. |
| Weather and environmental conditions | A trusted weather source; Earth Engine geospatial layers where relevant to a validated recommendation | Not connected. |
| Crop skills | Locally reviewed KVK/ICAR or agricultural-extension guidance | Current crop checklists are static examples and need local review. |
| Nearby business context | Google Places counts around retail outlets | Optional context only; does not reveal sales, crop prices, or buyer demand. |
| Waste and impact outcomes | Inventory, waste logs, transfer/donation records, and measured sales outcomes | Waste workflow is a demo; some seed data and close-of-day outcomes are illustrative. |

Keep credentials in backend environment variables or Secret Manager. Never commit API keys or collect customer personal data that is not needed for the service. Obtain permission for buyer and farmer data.

## Google Cloud Status

| Technology | Intended use | Status |
|---|---|---|
| Gemini on Vertex AI | Natural-language questions and explanations grounded in app data; structured waste-log extraction | Waste-log extraction optionally uses the Gemini API via `GEMINI_API_KEY`. Vertex AI migration and grounded Q&A are future work. Gemini does not fetch official mandi records. |
| BigQuery | Analyse aggregated buyer, mandi, soil, waste, and impact data | `cloud.py` can export measured impact rows when configured; a full analytics model is not implemented. |
| Vertex AI predictive models | Forecast buyer demand, spoilage risk, or crop outcomes after collecting representative validated data | Current order forecasts use deterministic Python; Vertex AI models are not implemented. |
| Earth Engine | Optional location-based climate, land, or vegetation data for crop suitability | Not integrated; use only when relevant and validated. |
| Cloud Storage | Store consented soil reports, crop photos, and approved datasets with access controls | Not integrated; no farmer upload exists. |
| Vision AI / image analysis | Assess crop quality or damage from images | Not integrated; do not treat the current text-based waste logging as image analysis. |
| Cloud Run | Host the application | Deployment configuration exists; production deployment is not verified here. |
| Pub/Sub | Send asynchronous buyer-match, spoilage, or workflow alerts | Not integrated. |

Additional docs: [architecture](docs/ARCHITECTURE.md), [cloud setup](docs/CLOUD.md), [edge cases](docs/EDGE_CASES.md), and [Git workflow](docs/GIT_WORKFLOW.md). The expanded project brief is also retained in [project.md](project.md).

Environment variables: `PORT`, `RL_DB`, `OUTLET_ORDER_LIMIT_INR`, `CO2E_KG_PER_KG_WASTE`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GOOGLE_MAPS_API_KEY`, `DATA_GOV_IN_API_KEY`, `MARKET_STATE`, `BQ_DATASET`, and `GOOGLE_CLOUD_PROJECT`.
