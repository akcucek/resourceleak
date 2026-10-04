"""Google Cloud: stream measured impact rows to BigQuery (REST, stdlib only).
Active only when BQ_DATASET is set. On Cloud Run the access token comes from the metadata server."""
import json, os, threading, urllib.request

META = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"


def _token():
    if os.environ.get("GOOGLE_ACCESS_TOKEN"):      # local dev: gcloud auth print-access-token
        return os.environ["GOOGLE_ACCESS_TOKEN"]
    req = urllib.request.Request(META, headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(req, timeout=3) as r:
        return json.load(r)["access_token"]


def enabled():
    return bool(os.environ.get("BQ_DATASET") and os.environ.get("GOOGLE_CLOUD_PROJECT"))


def build_rows(actions):
    return [{"insertId": a["id"] + ":" + str(a["real"]), "json": {k: a.get(k) for k in ("id", "lot", "route", "qty", "est", "real", "target")}}
            for a in actions]


def export(actions, post=None):
    """Fire-and-forget. Never raises into the app: a cloud outage must not block the store."""
    rows = build_rows(actions)
    if not rows or not enabled():
        return False
    def run():
        try:
            url = (f"https://bigquery.googleapis.com/bigquery/v2/projects/{os.environ['GOOGLE_CLOUD_PROJECT']}/datasets/"
                   f"{os.environ['BQ_DATASET']}/tables/{os.environ.get('BQ_TABLE', 'impact_ledger')}/insertAll")
            req = urllib.request.Request(url, data=json.dumps({"rows": rows}).encode(),
                                         headers={"Authorization": "Bearer " + _token(), "Content-Type": "application/json"})
            (post or urllib.request.urlopen)(req, timeout=8)
        except Exception as e:
            print("BigQuery export failed:", type(e).__name__)
    threading.Thread(target=run, daemon=True).start()
    return True
