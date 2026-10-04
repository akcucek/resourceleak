"""RESCUE: allocate a lot along the food-waste hierarchy, never double-counting."""
from dataclasses import dataclass


@dataclass
class Need:
    outlet: str
    qty: float            # unmet demand at the receiving outlet
    transport_cost: float  # total INR to move goods there
    capacity: float = 1e9


@dataclass
class Action:
    route: str
    qty: float
    recovery: float
    target: str | None = None
    blocked_reason: str | None = None


def plan(unsold, unit_price, markdown_pct=25, *, needs=(), markdown_qty=None,
         food_safe_confirmed=False, donate_ok=False, min_net=1.0):
    """Edge cases: transfers only up to receiver need/capacity and only if net
    value > min_net; remaining split: markdown, then donation (blocked until the
    food-safety check is confirmed); total allocated never exceeds unsold."""
    if unsold <= 0:
        return []
    actions, left = [], float(unsold)
    for n in sorted(needs, key=lambda n: -n.qty):
        q = min(left, n.qty, n.capacity)
        net = q * unit_price - n.transport_cost
        if q > 0 and net > min_net:
            actions.append(Action("transfer", q, round(net, 2), n.outlet)); left -= q
    if left > 0:
        q = min(left, markdown_qty) if markdown_qty is not None else left
        if q > 0:
            actions.append(Action("markdown", q, round(q * unit_price * (1 - markdown_pct / 100), 2)))
            left -= q
    if left > 0 and donate_ok:
        actions.append(Action("donate", left, 0.0, blocked_reason=None if food_safe_confirmed
                              else "food-safety check not confirmed"))
        left = 0
    if left > 0:
        actions.append(Action("compost", left, 0.0))
    return actions
