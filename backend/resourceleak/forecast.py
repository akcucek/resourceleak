"""PREVENT: newsvendor ordering with markdown salvage."""
from math import erf, exp, pi, sqrt
from statistics import NormalDist


def _pdf(z): return exp(-z * z / 2) / sqrt(2 * pi)
def _cdf(z): return 0.5 * (1 + erf(z / sqrt(2)))


def outcome(q, mu, sd, cost, price, salvage):
    """Expected sold, leftover, stock-out probability and margin for order q."""
    if sd <= 0:
        sold = min(q, mu); left = q - sold; out = 1.0 if q < mu else 0.0
    else:
        z = (q - mu) / sd
        lost = sd * _pdf(z) - (q - mu) * (1 - _cdf(z))
        sold = mu - lost; left = q - sold; out = 1 - _cdf(z)
    return {"sold": sold, "waste": left, "stockout": out,
            "margin": sold * price + left * salvage - q * cost}


def optimal_order(mu, sd, cost, price, salvage=0.0, *, budget=None, max_qty=None,
                  min_qty=0.0, pack_size=1.0):
    """Margin-maximising quantity. Edge cases handled:
    unprofitable item -> 0; zero/neg sd -> mu; salvage >= cost clamped;
    budget and shelf capacity caps; rounded down to pack size."""
    if mu <= 0 or price <= cost:
        return 0.0
    salvage = min(max(salvage, 0.0), cost * 0.999)
    sd = max(sd, 0.0)
    cu, co = price - cost, cost - salvage
    q = mu if sd == 0 else mu + NormalDist().inv_cdf(cu / (cu + co)) * sd
    q = max(q, min_qty, 0.0)
    cap = float("inf")
    if max_qty is not None: cap = min(cap, max_qty)
    if budget is not None: cap = min(cap, budget / cost)
    q = min(q, cap)
    lo = float(int(q // pack_size) * pack_size)
    hi = lo + pack_size
    if hi <= cap and hi != lo:  # pick the better of the two neighbouring pack multiples
        m = lambda x: outcome(x, mu, sd, cost, price, salvage)["margin"]
        return hi if m(hi) > m(lo) else lo
    return lo
