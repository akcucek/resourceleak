# Google Cloud + Maps integration
| Need | Service | In this repo |
|---|---|---|
| Place data around each outlet | Places API (New), Nearby Search | `places.py`, `GET /api/context?outlet=14` |
| Exact city-wide place counts (later) | Places Insights in BigQuery | replace the 20-result cap and the demo medians |
| Hosting | Cloud Run | `Dockerfile`, `deploy/cloudrun.sh`, `.github/workflows/deploy.yml` |
| Warehouse for the impact ledger | BigQuery | `cloud.py` (set `BQ_DATASET`, `GOOGLE_CLOUD_PROJECT`) |
| Secrets | Secret Manager | `--set-secrets GOOGLE_MAPS_API_KEY=maps-key:latest` |
| Waste-log extraction / explanations | Gemini (AI Studio key now, Vertex AI later) | `llm.py` |

## Try Maps locally
    export GOOGLE_MAPS_API_KEY=...   # enable "Places API (New)" in your project, restrict the key to it
    cd backend && python3 -m resourceleak
    curl -X POST localhost:8000/api/outlets/14/location -d '{"lat":13.02,"lng":77.57,"radius":1100}'
    curl "localhost:8000/api/context?outlet=14"      # source should say google_places

## Limits to know
- Nearby Search returns at most 20 places per call, so counts saturate at 20 per type group. Fine for a demo; use Places Insights for true counts.
- `MEDIAN` in places.py is a demo constant. Compute it once by sampling a grid across the city.
- Check Google's Maps Platform terms before storing Places content. The app only caches derived counts in memory for 1 hour.
- Cloud Run disk is ephemeral, so the SQLite file resets on redeploy. For real persistence move state to Cloud SQL or Firestore; the ledger already exports to BigQuery.
- The BigQuery and Cloud Run paths could not be tested in this build environment (no network). The Places parsing and failure fallback are unit-tested with a fake client.
