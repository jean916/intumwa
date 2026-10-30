# Intumwa: district early warning for Rwanda's farmers

**Intumwa** ("the messenger") turns NISR survey data and a rainfall signal into a risk tier for each of Rwanda's 30 districts,
then into plain-language alerts in Kinyarwanda and English for farmers (SMS and USSD, simulated), plus dashboards for district
officers. Built for the NISR 2026 Big Data Hackathon, Track 1: Agricultural Productivity.

> **A risk signal, not a forecast.** One survey year cannot support a trained forecasting model, and the app says so.

**Live app:** `https://intumwa.streamlit.app/` (public, no login needed) · **Demo video:** [`demo/video.webm.mp4`](demo/) (under 3 minutes) · **Full documentation:** [`DOCUMENTATION_EN.md`](DOCUMENTATION_EN.md) and the Kinyarwanda PDF

## What it communicates and how to use it
Intumwa shows, for each of Rwanda's 30 districts, how risky a dry spell or heavy rain is for farmers, *because* of how vulnerable they are (NISR survey data). Users can:
- pick **Drought** or **Heavy rain** and a rainfall input in the sidebar (scenario slider, real NASA POWER rainfall, or live Open-Meteo forecast);
- read the **risk map** and top-10 list, then open **Alerts (SMS)** to see the Kinyarwanda/English message for any district and its reason;
- add a **Rift Valley fever movement restriction** in the Livestock tab to see the alert change;
- try the **USSD** phone menu (type 1, 2 or 3) and the field-report form (simulated).

## Alignment with national priorities
Intumwa supports the **National Strategy for Transformation (NST2)** goals of agricultural transformation, climate resilience and food security, and **Vision 2050** by turning NISR statistics into early, local, actionable information for farmers, cooperatives and district officers. Gaps it targets, from AHS 2024: only 8.6% of farming households received weather information, and only 0.9% of those via phone messages.

## Data
| Data | Source / link | In this repo |
|---|---|---|
| Agriculture Household Survey 2024 (3,724 households) | NISR microdata portal: https://microdata.statistics.gov.rw/index.php/catalog (register, then "Get Microdata") | District-level tables only: `data/district_vulnerability.csv`, `data/district_yields.csv` (household microdata is licensed and **not** redistributed; rebuild with `build_vulnerability.py`) |
| AHS 2024 report tables (province level) | NISR AHS 2024 report, Aug 2025 | `data/ahs_report_*.csv` (transcribed, table numbers listed) |
| Rainfall | NASA POWER and Open-Meteo (see APIs below) | `data/rainfall_*.csv` once `fetch_rainfall.py` has been run |
| District centres | Approximate, for map display | `data/district_centroids.csv` |

## Team
- Kwizera Dieudonne, Software Engineering student, Adventist University of Central Africa (AUCA)
- Ukwizagira Jean Bosco, Software Engineering student, Adventist University of Central Africa (AUCA)

## Declaration
We declare that this submission is our own work and that all sources of reference are acknowledged in full (see Sources below). We understand that by entering we assign the intellectual property rights in this work to the National Institute of Statistics of Rwanda (NISR), as stated in the hackathon rules.

## Run it
Python 3.10 or newer. From inside this folder:

```
python -m venv .venv
.venv\Scripts\activate            # Mac/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Open http://localhost:8501. The `.streamlit/config.toml` file already skips the email prompt and applies the theme.
It works immediately in **scenario** mode (no internet needed). To unlock real and live rainfall, run `python check_apis.py` (1 minute) and then `python fetch_rainfall.py --test` and `python fetch_rainfall.py`. See `DEPLOY.md` to publish it online.

## How it works
1. **Hazard (0-100):** rainfall change vs normal. 0 at normal, 100 at a 50% deficit (drought) or excess (heavy rain). Three inputs, chosen in the sidebar:
   **Scenario** (slider, simulated), **Rainfall data file** (NASA POWER, latest 3 months vs 1991-2020), or **Live forecast** (Open-Meteo: the last 30 days plus the 14-day forecast vs the 1991-2020 normal for the same 44 days; refreshed hourly; falls back to Scenario if the API is unreachable).
2. **Vulnerability (0-100):** the average of seven weaknesses from the NISR Agriculture Household Survey 2024, each rescaled 0-1 across
   districts: poverty, extreme poverty, no extension advice, no bank or mobile-money account, no improved seed, land under 0.5 ha,
   not in a cooperative.
3. **Risk = hazard / 100 x vulnerability.** Low below 15, Elevated 15 to 30, High 30 or more. Districts with fewer than 30 survey households get no tier.
4. **Livestock risk = hazard / 100 x average of (vulnerability, cattle exposure)**, where cattle exposure is the share of households keeping cattle.
5. **Alerts** are written templates naming the biggest reason. Every Kinyarwanda alert fits one SMS (160 characters) unless a movement-restriction notice is added.

## APIs used
| API | Used for | Access | Tested how |
|---|---|---|---|
| **NISR microdata catalogue (NADA REST API)**, `microdata.statistics.gov.rw/index.php/api/catalog/search` | Looks up the AHS survey record shown in Method & validation | Public, no key | Parsing tested against the documented response format; **the live call has not been run from the build environment**: run `python check_apis.py` |
| **Open-Meteo forecast API**, `api.open-meteo.com/v1/forecast` | Live rainfall: last 30 days + 14-day forecast, all 30 districts in one call | Free, no key (non-commercial) | Parsing, missing values, errors and timeouts tested with responses built to the documented format; live call not run from the build environment |
| **NASA POWER monthly API** | 1991-2020 rainfall normals and the survey-year anomaly (`fetch_rainfall.py`) | Free, no key | Pipeline tested with a mocked response; live call not run from the build environment |

Every API call is wrapped so that a failure never breaks the app: the sidebar says what failed and the scenario mode takes over. `python check_apis.py` prints OK or FAIL for each endpoint on your network.
The AHS microdata itself is licensed and is processed offline; only district-level tables are included in this repository.

## Language and theme
The sidebar has **Language / Ururimi** (English or Kinyarwanda) and **Theme** (Light or Dark) switches. The Kinyarwanda switch translates the interface: header, sidebar, tab names, key labels, buttons, tier names and the main headings. SMS alerts and the USSD menu are always available in both languages. Long explanatory paragraphs (method, validation notes, chart captions) are still in English. The interface strings are in `i18n.py` and need native-speaker review: see `KINYARWANDA_UI_REVIEW.csv`. In dark mode the charts follow the dark theme; data tables keep Streamlit's own colours.

## What is in the app (8 tabs)
Risk map and top-10 list; Alerts (SMS preview, outbox, CSV of High-tier alerts); Crop context (district yields); Livestock (risk map, NISR monthly milk series);
Institutions (counts, weather-information gap); Analytics & forecast (nine charts, a yield-prediction test, a forecast demo); USSD and field reports (simulated menu, issue form);
Method & validation (formula, live comparison with NISR's published figures, limits, next steps).

## Validation against NISR's published figures
The district tables are weighted up by estimated households and compared live (Method & validation tab) with the AHS 2024 report, for five provinces plus the national figure:

| Indicator | Result |
|---|---|
| Improved seed, extension, cooperative, bank account, farm under 0.5 ha | **30 of 30 comparisons within 0.25 points** (Tables 14, 19, 27, 30, 32) |
| Farming households (estimated) | 2,163,581 vs 2,164,000 |
| Poverty (Table 2) | 22.6% vs 25.9% nationally; lower by about 13% in **every** province |

**The poverty gap, tested.** The consistent proportion suggests a different poverty variable or definition, not sampling noise. Forcing poverty to NISR's
provincial values changes the vulnerability index by at most 0.3 points, leaves the district ranking essentially unchanged (rank correlation 0.999) and moves no district to a different tier.
To find the cause, run `build_vulnerability.py` on the microdata: it now prints every poverty variable in the land file, its weighted mean and the missing-value count.

## Analytics and prediction: what is real and what is demo
- **Charts:** real data (district tables; province tables transcribed from the AHS 2024 report, Tables 14, 19, 26, 27, 29, 30, 32, 50-53).
- **Prediction 1 (real data):** ridge regression of district median yield on the survey indicators, tested leave-one-district-out. Cross-validated R-squared: maize 0.15, bush bean 0.23, cassava 0.03, sweet potato 0.06
  (about 25 districts). That is **weak to no predictive power**, reported as such.
- **Prediction 2 (demo):** seasonal regression with a backtest against "same as last year". The default series is **synthetic** and labelled DEMO. Upload a CSV (`date,value`, at least 36 months) to run it on real data.
- NISR's Table 26 rows add to 100 only with the irrigated share included, so the 25.5% "no water available" is a share of all plots.

## Limits
- No disease, pest or crop-price data. Movement restrictions are entered from RAB notices (a preset reproduces the June 2026 notice; check the current one).
- Rainfall is a scenario until `fetch_rainfall.py` has been run. Forecast rainfall beyond about 7 days is uncertain, and the live hazard is a transparent heuristic (44-day window, same 50% cap), not a drought index validated against crop losses. SMS and USSD are simulated; a launch needs a telecom partner.
- Kinyarwanda texts need native-speaker review: see `KINYARWANDA_REVIEW.csv`.
- The latest-quarter rainfall anomaly in `rainfall_anomaly.csv` (`anomaly_pct`) is strongly negative in almost every district (dry season or provisional data), so the "Rainfall data file" option uses the survey-year anomaly (`rain_anom_ahsyear_pct`, Sept 2023 to Aug 2024) instead. The live forecast option uses Open-Meteo rainfall against the 1991-2020 normals.
- District positions on the map are approximate centres.

## Files
`app.py` (app) - `apis.py` (live API calls with fallbacks) - `check_apis.py` (tests every API on your network) - `build_vulnerability.py` (rebuilds district tables from the AHS microdata, with validation printout) - `fetch_rainfall.py` (`--test` first) -
`data/` (district tables; AHS report tables; no household-level data) - `.streamlit/config.toml` (theme) - `i18n.py` (Kinyarwanda interface strings) - `KINYARWANDA_REVIEW.csv` - `KINYARWANDA_UI_REVIEW.csv` - `DEPLOY.md`.

## Sources
National Institute of Statistics of Rwanda (NISR), Agricultural Household Survey 2024 and its report (August 2025); NASA POWER rainfall (optional); RAB notices for animal-movement restrictions (entered by the user).
