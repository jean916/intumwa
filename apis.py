"""Live data sources for Intumwa. Every function returns (result, status) and never raises, so the app can always fall back
to its bundled data.

- Open-Meteo forecast API (no key): daily rainfall for the last 30 days and the next 14 days at each district centre.
  Docs: https://open-meteo.com/en/docs  (free for non-commercial use)
- NISR microdata catalogue (NADA REST API): looks up the Agriculture Household Survey record so the app can show where its
  data comes from. NISR's catalogue is a NADA installation: https://microdata.statistics.gov.rw
"""
import calendar
import os
import time

import numpy as np
import pandas as pd
import requests

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
NADA_SEARCH = "https://microdata.statistics.gov.rw/index.php/api/catalog/search"
NADA_STUDY = "https://microdata.statistics.gov.rw/index.php/catalog/"
HEADERS = {"User-Agent": "Intumwa-hackathon/1.0 (NISR 2026 Big Data Hackathon)", "Accept": "application/json"}


def _status(ok, message, **kw):
    return {"ok": ok, "message": message, "fetched_at": time.strftime("%H:%M"), **kw}


def expected_window_mm(normals_for_district, dates):
    """Normal rainfall (mm) over a list of dates: each day gets its month's normal divided by the days in that month.
    normals_for_district: Series indexed by month 1-12 (monthly normal total in mm)."""
    return float(sum(normals_for_district[d.month] / calendar.monthrange(d.year, d.month)[1] for d in dates))


def longest_dry_run(values, threshold=1.0):
    """Longest run of consecutive days with less than `threshold` mm."""
    best = run = 0
    for v in values:
        run = run + 1 if (not np.isnan(v) and v < threshold) else 0
        best = max(best, run)
    return best


def parse_open_meteo(payload, coords, normals, today):
    """Turn an Open-Meteo JSON payload (list for several locations) into one row per district."""
    items = payload if isinstance(payload, list) else [payload]
    if len(items) != len(coords):
        raise ValueError(f"expected {len(coords)} locations, got {len(items)}")
    rows = []
    for c, it in zip(coords.itertuples(), items):
        daily = it["daily"]
        s = pd.Series(daily["precipitation_sum"], index=pd.to_datetime(daily["time"]), dtype="float64")
        past, ahead = s[s.index < today], s[s.index >= today]
        missing = int(s.isna().sum())
        row = {"district": c.district, "rain_past_mm": round(float(past.sum()), 1), "rain_ahead_mm": round(float(ahead.sum()), 1),
               "wettest_day_ahead_mm": round(float(ahead.max()), 1) if len(ahead) and not ahead.isna().all() else np.nan,
               "dry_run_ahead_days": longest_dry_run(ahead.values), "missing_days": missing}
        if normals is not None and c.district in normals.index.get_level_values(0):
            exp = expected_window_mm(normals.loc[c.district]["normal_mm"], list(s.index))
            row["expected_mm"] = round(exp, 1)
            row["anomaly_pct"] = round((float(s.sum()) / exp - 1) * 100, 1) if exp > 5 and missing <= 0.2 * len(s) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_open_meteo(coords, normals=None, past=30, ahead=14, timeout=25):
    """coords: DataFrame with district, lat, lon. normals: DataFrame (district, month, normal_mm) or None.
    Returns (DataFrame or None, status)."""
    try:
        r = requests.get(OPEN_METEO, headers=HEADERS, timeout=timeout, params={
            "latitude": ",".join(f"{x:.4f}" for x in coords["lat"]), "longitude": ",".join(f"{x:.4f}" for x in coords["lon"]),
            "daily": "precipitation_sum", "past_days": past, "forecast_days": ahead, "timezone": "Africa/Kigali"})
        r.raise_for_status()
        today = pd.Timestamp.now(tz="Africa/Kigali").normalize().tz_localize(None)
        nm = normals.set_index(["district", "month"]) if normals is not None else None
        df = parse_open_meteo(r.json(), coords, nm, today)
        n_bad = int(df["anomaly_pct"].isna().sum()) if "anomaly_pct" in df else len(df)
        return df, _status(True, f"Open-Meteo: {len(df)} districts" + (f" ({n_bad} without a usable anomaly)" if n_bad else ""),
                           window=f"last {past} days + next {ahead} days")
    except Exception as e:  # network, rate limit or format problem: the caller falls back to the scenario
        return None, _status(False, f"Live rainfall (Open-Meteo) is not reachable from this network ({type(e).__name__})")


def fetch_nisr_catalog(query="agricultural household survey", limit=8, timeout=20):
    """Search NISR's microdata catalogue (NADA REST API). Returns (list of dicts, status)."""
    try:
        r = requests.get(NADA_SEARCH, headers=HEADERS, timeout=timeout, params={"sk": query, "ps": limit})
        r.raise_for_status()
        j = r.json()
        if not isinstance(j, dict):
            raise ValueError("unexpected (non-JSON) reply")
        res = j.get("result", j)
        rows = res.get("rows") or res.get("studies") or []
        out = [{"title": x.get("title", ""), "year": x.get("year_start") or x.get("year") or "", "idno": x.get("idno", ""),
                "link": NADA_STUDY + str(x.get("id", ""))} for x in rows if x.get("title")]
        if not out:
            return [], _status(True, "NISR catalogue answered but returned no matching studies")
        return out, _status(True, f"NISR microdata catalogue: {len(out)} matching studies")
    except Exception as e:
        return [], _status(False, f"NISR catalogue not reachable from this network ({type(e).__name__})")


def load_normals(path="data/rainfall_normals.csv"):
    return pd.read_csv(path) if os.path.exists(path) else None
