"""One-minute check of every external API Intumwa uses. Run:  python check_apis.py
Prints OK or FAIL for each, with the exact URL, so you know before you present which live features will work on your network."""
import pandas as pd
import apis

ok_all = True
print("1. NISR microdata catalogue (NADA REST API)")
rows, st = apis.fetch_nisr_catalog()
print("  ", "OK  " if st["ok"] and rows else ("EMPTY" if st["ok"] else "FAIL"), st["message"])
for r in rows[:5]:
    print("     -", r["year"], r["title"][:80], "|", r["link"])
ok_all &= st["ok"]

print("2. Open-Meteo forecast API (live rainfall)")
cent = pd.read_csv("data/district_centroids.csv").head(3)
df, st = apis.fetch_open_meteo(cent)
print("  ", "OK  " if st["ok"] else "FAIL", st["message"])
if df is not None:
    print(df[["district", "rain_past_mm", "rain_ahead_mm", "wettest_day_ahead_mm", "dry_run_ahead_days"]].to_string(index=False))
ok_all &= st["ok"]

print("3. NASA POWER monthly API (normals, used by fetch_rainfall.py)")
try:
    import requests
    r = requests.get("https://power.larc.nasa.gov/api/temporal/monthly/point", timeout=40, params={
        "parameters": "PRECTOTCORR", "community": "AG", "latitude": -1.95, "longitude": 30.06, "start": 2023, "end": 2024, "format": "JSON"})
    r.raise_for_status()
    n = len(r.json()["properties"]["parameter"]["PRECTOTCORR"])
    print("   OK  ", n, "monthly values returned")
except Exception as e:
    ok_all = False
    print("   FAIL", type(e).__name__, str(e)[:120])

print("\nAll live APIs reachable." if ok_all else "\nSome APIs failed: the app still works, using bundled data for those parts.")
