"""Karnataka mandi prices from the data.gov.in Agmarknet resource."""
import json, os, time, urllib.parse, urllib.request
from datetime import datetime

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
API_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
CROPS = {"tomato": "Tomato", "onion": "Onion", "watermelon": "Watermelon", "paddy": "Paddy"}
TTL = 1800
_cache = None


def _get(url, timeout=10):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def _number(value):
    try:
        result = float(str(value).replace(",", "").strip())
        return result if result >= 0 else None
    except (TypeError, ValueError):
        return None


def _field(record, name):
    key = name.replace("_", "").casefold()
    return next((value for field, value in record.items() if field.replace("_", "").casefold() == key), None)


def _date_key(value):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return (1, datetime.strptime(value, fmt).date().isoformat())
        except (TypeError, ValueError):
            pass
    return (0, str(value))


def fetch_prices(api_key, get=_get, state="Karnataka"):
    """Fetch latest available state mandi records and retain the requested crops."""
    query = urllib.parse.urlencode({
        "api-key": api_key,
        "format": "json",
        "limit": 1000,
        "filters[state]": state,
    })
    payload = get(f"{API_URL}?{query}")
    records = payload.get("records", [])
    prices = {}
    for record in records:
        commodity = str(_field(record, "commodity") or "").strip().casefold()
        crop = next((key for key, name in CROPS.items() if name.casefold() == commodity), None)
        if not crop:
            continue
        low, high, modal = (_number(_field(record, field)) for field in ("min_price", "max_price", "modal_price"))
        if low is None or high is None or modal is None:
            continue
        date = str(_field(record, "arrival_date") or "")
        row = {
            "min_price": low,
            "max_price": high,
            "modal_price": modal,
            "unit": "INR/quintal",
            "market": str(_field(record, "market") or ""),
            "district": str(_field(record, "district") or ""),
            "date": date,
        }
        if crop not in prices or _date_key(date) > _date_key(prices[crop]["date"]):
            prices[crop] = row
    return prices


def market_data(get=_get, api_key=None, state=None):
    """Return live prices when configured; never imply that demo prices are live."""
    global _cache
    key = api_key if api_key is not None else os.environ.get("DATA_GOV_IN_API_KEY")
    state = state or os.environ.get("MARKET_STATE", "Karnataka")
    if not key:
        return {"source": "not_configured", "state": state, "prices": {},
                "note": "Live mandi prices need DATA_GOV_IN_API_KEY. Buyer demand is illustrative until a POS feed is connected."}
    cache_key = (state, key)
    if get is _get and _cache and _cache[0] == cache_key and time.time() - _cache[1] < TTL:
        return _cache[2]
    try:
        prices = fetch_prices(key, get=get, state=state)
    except Exception as error:
        return {"source": "unavailable", "state": state, "prices": {},
                "note": f"Mandi prices unavailable ({type(error).__name__}). Showing illustrative prices; buyer demand still needs a POS feed."}
    result = {"source": "data.gov.in", "state": state, "prices": prices,
              "note": "Live Agmarknet mandi prices in INR per quintal. Buyer demand is illustrative until a POS feed is connected."}
    if get is _get:
        _cache = (cache_key, time.time(), result)
    return result