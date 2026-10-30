"""Download monthly rainfall for each district centre and write data/rainfall_anomaly.csv.

Source: NASA POWER monthly API (PRECTOTCORR, mm/day). Needs internet.
Also writes data/rainfall_normals.csv (district, month, normal_mm) for the live forecast mode.
Output columns of rainfall_anomaly.csv: district,
  anomaly_pct            latest 3 complete months vs the 1991-2020 average of the same months,
  rain_anom_2024_pct     calendar 2024 vs the 1991-2020 average annual total,
  rain_anom_ahsyear_pct  Sept 2023 to Aug 2024 (the AHS survey year) vs the same average.

Usage:
  python fetch_rainfall.py --test    # one district only: check the output before the full run
  python fetch_rainfall.py           # all districts (about 1 minute)
"""
import argparse
import calendar
import sys
import time

import pandas as pd
import requests

URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"


def ahs_year_anomaly(s, annual_norm):
    """Rainfall Sept 2023 to Aug 2024 (the AHS 2023/24 agricultural year) vs the 1991-2020 annual normal, in %.
    Returns None unless all 12 months are present."""
    w = s[(s.index >= "2023-09-01") & (s.index <= "2024-08-31")]
    return round((w.sum() / annual_norm - 1) * 100, 1) if len(w) == 12 else None


def parse_series(raw):
    """NASA JSON {YYYYMM: mm/day} -> monthly totals in mm. Drops the YYYY13 annual rows and -999 missing values."""
    m = {k: v * calendar.monthrange(int(k[:4]), int(k[4:]))[1] for k, v in raw.items() if k[4:] != "13" and v != -999}
    s = pd.Series(m)
    s.index = pd.to_datetime(s.index, format="%Y%m")
    return s.sort_index()


def summarise(s):
    """One district's anomaly figures from its monthly series."""
    base = s[(s.index.year >= 1991) & (s.index.year <= 2020)]
    latest = s.iloc[-3:]
    norm = base.groupby(base.index.month).mean()
    expected = sum(norm[d.month] for d in latest.index)
    annual_norm = base.groupby(base.index.year).sum().mean()
    row = {"anomaly_pct": round((latest.sum() / expected - 1) * 100, 1),
           "rain_anom_2024_pct": round((s[s.index.year == 2024].sum() / annual_norm - 1) * 100, 1),
           "rain_anom_ahsyear_pct": ahs_year_anomaly(s, annual_norm)}
    return row, norm


def fetch(lat, lon, tries=3):
    last = None
    for k in range(tries):
        try:
            r = requests.get(URL, params={"parameters": "PRECTOTCORR", "community": "AG", "latitude": lat, "longitude": lon,
                                          "start": 1991, "end": 2026, "format": "JSON"}, timeout=60)
            r.raise_for_status()
            return parse_series(r.json()["properties"]["parameter"]["PRECTOTCORR"])
        except Exception as e:  # network or format problem: wait and retry
            last = e
            time.sleep(2 * (k + 1))
    raise RuntimeError(last)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="fetch one district only and print the result")
    args = ap.parse_args(argv)
    cent = pd.read_csv("data/district_centroids.csv")
    if args.test:
        cent = cent.head(1)
    rows, normals, failed = [], [], []
    for i, c in enumerate(cent.itertuples(), 1):
        try:
            row, norm = summarise(fetch(c.lat, c.lon))
            rows.append({"district": c.district, **row})
            normals += [{"district": c.district, "month": int(m), "normal_mm": round(float(v), 1)} for m, v in norm.items()]
            print(f"[{i}/{len(cent)}] {c.district}: ok", flush=True)
        except Exception as e:
            failed.append(c.district)
            print(f"[{i}/{len(cent)}] {c.district}: FAILED ({e})", flush=True)
        time.sleep(1)
    out = pd.DataFrame(rows)
    if args.test:
        print(out.to_string(index=False))
        print("Test only: nothing written. If the numbers look plausible (roughly -40 to +40), run without --test.")
        return 0
    if len(out) < 25:
        print(f"Only {len(out)} districts succeeded ({len(failed)} failed): file NOT written. Check your internet and run again.")
        return 1
    out.to_csv("data/rainfall_anomaly.csv", index=False)
    pd.DataFrame(normals).to_csv("data/rainfall_normals.csv", index=False)   # used by the live Open-Meteo mode
    print(f"Wrote data/rainfall_normals.csv (1991-2020 monthly normals) and data/rainfall_anomaly.csv with {len(out)} districts." + (f" Failed: {', '.join(failed)}" if failed else ""))
    print(out.describe().round(1).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
