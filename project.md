# ResourceLeak AI: Project Brief

## Problem Statement
Food waste and poorly matched supply and demand are environmental and community challenges. Retailers and hotels can over-order perishable food, leading to avoidable waste, financial loss, and emissions. At the same time, farmers may make planting decisions without timely visibility into buyer requirements, mandi prices, or advice grounded in their soil and local growing conditions.

ResourceLeak AI addresses this challenge through resource optimization, sustainable agriculture, and waste reduction. The intended outcome is less surplus food, better-informed crop planning, and stronger local connections between growers and buyers.

## Proposed Solution
The product has two user roles:
- **Retail buyer or hotel:** shares crop requirements and uses sales and waste history to plan purchasing quantities.
- **Farmer:** provides farm and soil information, sees relevant buyer needs and mandi-price context, and receives a locally reviewed crop procedure and skills checklist.

The existing retail workflow supports the same environmental goal: **Prevent** over-ordering, **Detect** spoilage risk and waste, **Rescue** surplus through sale, transfer, or donation, and **Prove** results using measured outcomes.

The farmer-to-buyer workflow should combine actual buyer demand, current public market information, and farm conditions. It should explain its sources and uncertainty. A mandi price is not a purchase commitment or guaranteed farmer income.

## How It Solves the Problem
1. Collect crop, quantity, timing, and delivery-area requirements from participating buyers' POS or purchasing records.
2. Retrieve dated mandi prices for matching commodities and markets.
3. Collect farmer soil-test results, farm location, season, and water availability with the farmer's permission.
4. Compare buyer needs with locally validated crop and soil requirements; recommend only suitable options and show confidence, source, and date.
5. Give the farmer practical guidance from planting through pest monitoring, harvest, grading, and delivery.
6. Track buyer acceptance, fulfillment, farmer outcomes, and food saved. Use measured results to evaluate impact and improve future planning.

Start with deterministic, reviewable agronomy rules and a small local pilot. Add predictive models only after sufficient, consented, good-quality outcome data exists. Measure outcomes such as kilograms of food waste avoided, buyer demand fulfilled, and farmer revenue after costs against a stated baseline.

## Users and Pilot Area
The prototype is scoped to Bengaluru and Karnataka. The buyer and farmer are separate roles in the UI, but authentication and saved accounts are not implemented. Expand to other states only when their data, crop calendars, and agronomy guidance are validated.

## Data: Sources and Status
| Data needed | Where to get it | Status in this project |
|---|---|---|
| Mandi prices and arrivals | [data.gov.in Agmarknet daily-price resource](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi), resource ID `9ef84268-d588-465a-a308-a864a43d0070` | Backend route `GET /api/market` is implemented. It needs `DATA_GOV_IN_API_KEY`, a working network connection, and optionally `MARKET_STATE`. The UI shows no live quote when real records are unavailable. |
| Local buyer demand | Retailer/hotel POS or procurement exports, or a partner-approved API. Useful fields: crop/SKU, quantity, date, price, delivery area, stockouts, and waste. | Prototype demand and trends are synthetic. No POS connection or importer exists. Obtain partner permission; do not scrape private sales data. |
| Soil and farm conditions | Farmer-provided soil test or Soil Health Card, farm location, season, and water availability | Prototype only has a manual selector for four soil textures. Soil-test upload, profiles, and measured nutrient interpretation are not implemented. |
| Weather and environmental conditions | A trusted weather source; geospatial layers may come from Google Earth Engine where relevant | Not connected. Add only when the data improves a validated recommendation. |
| Nearby retail context | Google Places counts around an outlet | Optional business-location context only. It does not provide sales, crop prices, or demand. |
| Crop and skill guidance | Locally reviewed KVK/ICAR and agricultural-extension guidance | Prototype checklists are examples and require local expert review before operational use. |
| Waste and impact outcomes | Buyer inventory, waste logs, transfers, donation receipts, and measured sales outcomes | Existing waste workflow is a demo. Some seed values and end-of-day outcomes are illustrative. |

Never commit API keys or put them in frontend code. Keep credentials in environment variables or Secret Manager. Collect only data needed for the service, obtain permission, and avoid customer personal information in buyer-demand data.

## Google Cloud Technology Plan
| Technology | Role in this solution | Project status |
|---|---|---|
| Gemini on Vertex AI | Natural-language questions, structured waste-log extraction, and explanations grounded in app data | Waste-log extraction currently supports the Gemini API through `GEMINI_API_KEY`; Vertex AI migration and grounded data Q&A are future work. Gemini does not replace the data.gov.in API for original mandi records. |
| BigQuery | Analyse aggregated demand, mandi, soil, waste, and impact records across locations and time | `cloud.py` can export measured impact rows when configured. A complete analytics model and dashboards are not implemented. |
| Vertex AI predictive models | Forecast demand, spoilage risk, or crop outcomes after enough representative and validated data is available | Current order forecasting is deterministic Python; Vertex AI models are not implemented. |
| Earth Engine | Optional geospatial climate, land, or vegetation signals for location-aware recommendations | Not integrated. Use only if a specific recommendation needs those layers and the source is appropriate. |
| Cloud Storage | Store consented soil reports, crop images, and approved datasets with access controls and retention policies | Not integrated. No farmer report or image upload exists. |
| Vision AI / image analysis | Optional crop-quality or damage assessment from farmer/buyer images | Not integrated; current waste logging is text-oriented and image-analysis claims should not be treated as implemented. |
| Cloud Run | Deploy the HTTP application as a managed service | Deployment configuration exists; production deployment is not verified here. |
| Pub/Sub | Send asynchronous alerts for buyer matches, spoilage risk, and workflow events | Not integrated; consider after real users and event needs are established. |

## Current Prototype
- The Buyer / Hotel view lists four crops. Demand quantities and trends are labeled as demo values.
- The server requests Agmarknet records through `/api/market`; only returned records are displayed as mandi quotes.
- The Farmer view maps a manual soil-texture selection to an example crop and static checklist. It is not a personalized agronomy recommendation.
- Buyer-to-farmer buttons and the share confirmation are frontend demonstrations; no request or order is saved or sent.
- The original outlet dashboard demonstrates order planning, waste logging, rescue actions, and impact reporting with mostly synthetic seed data.

## Run and Test
From the repository root:

```sh
cd backend
python3 -m resourceleak
```

Open `http://localhost:8000/proto.html`. Set `DATA_GOV_IN_API_KEY` and optionally `MARKET_STATE` in the backend environment before starting the server to request mandi records.

```sh
cd backend
python3 -m unittest discover -s tests -v
```

## Key Risks and Boundaries
- Public mandi data gives market context, not local buyer demand or a guaranteed farm-gate price.
- Buyer demand remains synthetic until a buyer shares records through an agreed, permissioned integration.
- Crop suitability, yield assumptions, and procedures require locally reviewed soil and agronomy data before advising planting decisions.
- Forecasts and impact claims must identify estimates and use measured outcomes wherever possible.
