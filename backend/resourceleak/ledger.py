"""PROVE: estimated vs realized, measured against a baseline."""
from dataclasses import dataclass


@dataclass
class Entry:
    action_id: str
    estimated: float
    realized: float | None = None  # None until measured
    accepted: bool = True


def realized_ratio(entries):
    """Edge cases: rejected or unmeasured entries excluded; zero estimate -> None."""
    done = [e for e in entries if e.accepted and e.realized is not None]
    est = sum(e.estimated for e in done)
    return None if est <= 0 else round(sum(e.realized for e in done) / est, 3)


def co2e_kg(kg_prevented, factor=2.5):
    if kg_prevented < 0: raise ValueError("kg must be >= 0")
    return kg_prevented * factor
