"""DETECT input: free text (typed, WhatsApp, voice transcript) -> validated waste entry.
Rules always work offline. If GEMINI_API_KEY is set, Gemini is tried first, and its output is
validated exactly like rule output; any failure falls back to rules. Low confidence -> human confirm."""
import json, os, re, urllib.request

UNIT_TO_KG = {"kg": 1.0, "g": 0.001, "dozen": 1.5, "loaf": 0.4, "bn": 0.25}
SKUS = {"tomato": ["tomato", "tomatoes", "ಟೊಮೆಟೊ", "ಟೊಮೇಟೊ", "टमाटर"], "banana": ["banana", "bananas", "ಬಾಳೆ", "केला"],
        "spinach": ["spinach", "palak", "ಪಾಲಕ್", "पालक"], "papaya": ["papaya", "ಪರಂಗಿ", "पपीता"],
        "onion": ["onion", "onions", "ಈರುಳ್ಳಿ", "प्याज"], "bread": ["bread", "loaves", "ಬ್ರೆಡ್", "ब्रेड"]}
NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "ಒಂದು": 1, "ಎರಡು": 2, "ಮೂರು": 3, "ನಾಲ್ಕು": 4, "ಐದು": 5, "ಆರು": 6, "ಏಳು": 7, "ಎಂಟು": 8, "ಒಂಬತ್ತು": 9, "ಹತ್ತು": 10}
UNITS = {"kg": ["kg", "kgs", "kilo", "kilos", "ಕೆಜಿ", "किलो"], "dozen": ["dozen", "ಡಜನ್", "दर्जन"], "g": ["g", "gm", "gms"],
         "loaf": ["loaf", "loaves"], "bn": ["bunch", "bunches", "bn"]}
REASONS = {"spoiled": ["spoil", "rotten", "bad", "ಹಾಳ", "खराब"], "overripe": ["overripe", "over ripe", "ripe", "ಹಣ್ಣಾ", "पका"],
           "damaged": ["damage", "crushed", "ಒಡೆ"], "expired": ["expir", "best before"]}


def _find(text, table):
    low = text.lower()
    for key, words in table.items():
        if any(w in low for w in words):
            return key
    return None


def parse_rules(text):
    low = text.lower()
    m = re.search(r"(\d+(?:\.\d+)?)", low)
    qty = float(m.group(1)) if m else next((v for w, v in NUM_WORDS.items() if w in low), None)
    sku, unit, reason = _find(text, SKUS), _find(text, UNITS), _find(text, REASONS)
    if sku == "bread" and not unit: unit = "loaf"
    conf = 0.4 + 0.2 * bool(sku) + 0.2 * (qty is not None) + 0.1 * bool(unit) + 0.1 * bool(reason)
    return {"sku": sku or "unknown", "qty": qty if qty is not None else 0, "unit": unit or "", "reason": reason or "unknown",
            "confidence": round(conf, 2)}


def parse_gemini(text, key):
    prompt = ("Extract a retail food-waste log as JSON with keys sku, qty (number), unit (kg|g|dozen|loaf|bn), "
              "reason (spoiled|overripe|damaged|expired|unknown), confidence (0-1). Text may be English, Kannada or Hindi. "
              "Return JSON only.\nText: " + text)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        data=json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        out = json.load(r)["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(out)


def validate(raw):
    """Schema + range checks. Returns entry dict or None."""
    try:
        qty, conf = float(raw["qty"]), float(raw["confidence"])
        sku, unit = str(raw["sku"]).lower(), str(raw["unit"]).lower()
    except (KeyError, TypeError, ValueError):
        return None
    if not (0 < qty <= 1000 and 0 <= conf <= 1) or unit not in UNIT_TO_KG or sku not in SKUS:
        return None
    return {"sku": sku, "qty": qty, "unit": unit, "reason": str(raw.get("reason", "unknown")), "confidence": conf}


def extract(text, source="text", threshold=0.8):
    """Returns (entry|None, status, engine). status: auto_logged | needs_confirmation | needs_review."""
    text = (text or "").strip()
    if not text or len(text) > 500:
        return None, "needs_review", "none"
    raw, engine = None, "rules"
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        try:
            raw, engine = parse_gemini(text, key), "gemini"
        except Exception:
            raw = None
    entry = validate(raw) if raw else None
    if entry is None:
        engine = "rules"; entry = validate(parse_rules(text))
    if entry is None:
        return None, "needs_review", engine
    if source == "voice" or entry["confidence"] < threshold:
        return entry, "needs_confirmation", engine
    return entry, "auto_logged", engine
