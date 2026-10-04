"""Local Context Vector: aggregated place-type counts only; no personal data."""
from math import sqrt
from statistics import median


def normalise(counts, city_median):
    """Scale each place type by the city median. Zero median -> 1.0 (avoid /0)."""
    return {k: counts.get(k, 0) / (city_median.get(k) or 1.0) for k in city_median}


def cosine(a, b):
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na, nb = sqrt(sum(v * v for v in a.values())), sqrt(sum(v * v for v in b.values()))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


def twins(target_id, vectors, k=3, min_sim=0.7):
    """Look-alike outlets, excluding self. Flags low confidence below min_sim."""
    sims = sorted(((cosine(vectors[target_id], v), o) for o, v in vectors.items()
                   if o != target_id), reverse=True)[:k]
    return [{"outlet": o, "similarity": round(s, 2), "low_confidence": s < min_sim}
            for s, o in sims]


def city_median(all_counts):
    keys = {k for c in all_counts for k in c}
    return {k: median(c.get(k, 0) for c in all_counts) for k in keys}
