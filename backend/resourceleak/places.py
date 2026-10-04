"""Local Context Vector from Google Maps Platform (Places API New, Nearby Search).
Counts places of each type group around an outlet, then divides by the city median.
Works offline: without GOOGLE_MAPS_API_KEY it returns clearly-labelled synthetic data.
Only aggregated place TYPES are used. Nothing about people is read or inferred."""
import json, os, time, urllib.request
from . import context

GROUPS = {
    "stay": ["lodging"],
    "edu": ["university", "school", "secondary_school", "primary_school"],
    "food": ["supermarket", "grocery_store", "restaurant"],
    "office": ["corporate_office"],
    "transit": ["bus_station", "subway_station", "transit_station"],
    "home": ["apartment_building", "apartment_complex", "housing_complex"],
}
# Demo medians. In production compute them by sampling a grid of points across the city (one-off job).
MEDIAN = {"stay": 6, "edu": 5, "food": 10, "office": 6, "transit": 5, "home": 8}
# Synthetic ratios (x city median) used when no API key is set.
SYNTH = {"14": {"stay": 3.4, "edu": 2.8, "food": 2.1, "office": 0.9, "transit": 1.4, "home": 0.6},
         "27": {"stay": 0.4, "edu": 0.8, "food": 1.3, "office": 0.7, "transit": 0.8, "home": 2.6}}
PAGE_CAP = 20          # Nearby Search returns at most 20 places per call, so counts saturate at 20
URL = "https://places.googleapis.com/v1/places:searchNearby"
TTL = 3600
_cache = {}


def _post(url, headers, body, timeout=8):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def valid_location(lat, lng, radius=1100):
    return (isinstance(lat, (int, float)) and isinstance(lng, (int, float)) and -90 <= lat <= 90
            and -180 <= lng <= 180 and 200 <= radius <= 5000)


def fetch_counts(lat, lng, radius, key, post=_post):
    """One request per group. Raises on any API error so the caller can fall back safely."""
    counts = {}
    for group, types in GROUPS.items():
        body = {"includedTypes": types, "maxResultCount": PAGE_CAP,
                "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius)}}}
        res = post(URL, {"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id"}, body)
        counts[group] = len(res.get("places", []))
    return counts


def vector(counts):
    return context.normalise(counts, MEDIAN)


def get_context(outlet, loc, other=None, post=_post):
    """Returns {source, counts, vector, twin}. Cached for TTL seconds (cost control)."""
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    ck = (outlet, loc["lat"], loc["lng"], loc["radius"], bool(key))
    hit = _cache.get(ck)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    source, note = "synthetic", "Synthetic demo data. Set GOOGLE_MAPS_API_KEY for live Google Places counts."
    if key:
        try:
            counts = fetch_counts(loc["lat"], loc["lng"], loc["radius"], key, post)
            vec, source, note = vector(counts), "google_places", "Live from Google Places (counts cap at 20 per type group)."
        except Exception as e:  # network, quota, bad key: degrade, never break the dashboard
            counts, vec = None, None
            note = f"Google Places unavailable ({type(e).__name__}); showing synthetic data."
    if source == "synthetic":
        vec = dict(SYNTH.get(outlet, {k: 1.0 for k in MEDIAN})); counts = {k: round(v * MEDIAN[k]) for k, v in vec.items()}
    out = {"source": source, "note": note, "counts": counts, "vector": {k: round(v, 2) for k, v in vec.items()}}
    if other:
        out["twin_similarity"] = round(context.cosine(vec, other), 2)
    _cache[ck] = (time.time(), out)
    return out
