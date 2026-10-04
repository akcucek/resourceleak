"""DETECT: 48-hour spoilage risk from stock, demand and shelf life."""
from dataclasses import dataclass


@dataclass
class Risk:
    stock: float
    forecast_demand: float
    shelf_life_days: float
    expected_unsold: float
    window_hours: float
    level: str


def assess(stock, daily_demand, shelf_life_days, *, humidity=None, open_hours_left=14.0):
    """Edge cases: negative inputs rejected; expired lots (<=0 days) cannot be
    sold, so all stock is unsold and window is 0; humid weather shortens life."""
    if stock < 0 or daily_demand < 0:
        raise ValueError("stock and demand must be >= 0")
    life = max(shelf_life_days, 0.0)
    if humidity is not None and humidity > 70:
        life *= 0.85
    sellable_days = life
    demand = daily_demand * sellable_days
    unsold = stock if life == 0 else max(0.0, stock - demand)
    window = min(life * 24, open_hours_left + 24 * max(life - 1, 0)) if life else 0.0
    ratio = unsold / stock if stock else 0.0
    level = "high" if ratio >= 0.5 else "medium" if ratio >= 0.2 else "low"
    return Risk(stock, round(demand, 1), round(life, 2), round(unsold, 1), round(window, 1), level)
