"""Generate synthetic outlets/sales/waste so no real retailer data is ever committed."""
import csv, pathlib, random
random.seed(7)
out = pathlib.Path(__file__).parent / "generated"; out.mkdir(exist_ok=True)
with open(out / "sales.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["outlet", "day", "sku", "sold", "wasted"])
    for o in (14, 27):
        for d in range(28):
            for sku, base in (("tomato", 62), ("spinach", 20), ("banana", 120)):
                sold = max(0, int(random.gauss(base, base * 0.13)))
                w.writerow([o, d, sku, sold, int(random.random() * base * 0.2)])
print("wrote", out / "sales.csv")
