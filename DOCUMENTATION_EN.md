# Intumwa: early warning for Rwanda's crop farmers and livestock keepers
NISR 2026 Big Data Hackathon, Track 1: Agricultural Productivity. English documentation (a Kinyarwanda version is in the repository PDF). "Intumwa" means "the messenger".

## 1. What it is
A district-level early-warning system. It combines a rainfall hazard (drought or heavy rain) with farmer vulnerability estimated from the NISR Agriculture Household Survey (AHS) 2024 to give each of the 30 districts a risk tier (Low, Elevated, High), then turns it into plain-language alerts in Kinyarwanda and English for SMS and USSD (simulated). **It is a risk signal, not a forecast.**

## 2. Problem and relevance
Recent shocks had early signs but reached farmers and buyers late: the Kigali milk shortage (Aug to Sep 2026, linked to a long dry spell and poor pasture), the Rift Valley fever outbreak and animal-movement restrictions (Jun to Sep 2026), and crop damage and food-price rises from heavy rain and hail (2025 to 2026). *Figures from news and RAB/NISR statements are quoted from the project brief and should be re-checked against the original sources before relying on them.*

AHS 2024 shows the information gap Intumwa targets:
- Only 8.6% of farming households received weather information (Kigali 3.4%, West 3.7%); of those, only 0.9% received it by phone message (Tables 27, 29).
- Litres of milk per cow per day fell from 4.0 (April 2024) to 2.8 (August 2024); the price paid to producers rose from 283 to 324 Rwf per litre (Tables 50, 51, 53). This is a seasonal pattern in the survey, not proof that drought alone caused it.
- Only 5.6% of plots are irrigated and 25.5% of all plots are not irrigated because no water is available (46.7% in the East) (Table 26).

Alignment: NST2 (agricultural transformation, climate resilience, food security) and Vision 2050.

## 3. What was built (Streamlit app, 8 tabs)
Risk map; Alerts (SMS) with CSV download for High-tier districts; Crop context (district yields); Livestock (risk map, RVF movement-restriction input, NISR monthly milk series); Institutions dashboard; Analytics and forecast (9 charts, a yield-prediction test, a clearly labelled DEMO milk forecast); USSD and field reports (simulated); Method and validation.

**Language and theme:** the sidebar switches the interface between English and Kinyarwanda and between a light and a dark theme. Alerts and the USSD menu exist in both languages. Interface translations need native-speaker review.

## 4. Method
1. **Vulnerability (0-100):** mean of seven AHS 2024 indicators, each rescaled 0-1 across districts: poverty, extreme poverty, no extension advice, no bank or mobile-money account, no improved seed, land under 0.5 ha, not in a cooperative.
2. **Hazard (0-100):** rainfall change vs normal; 100 at a 50% deficit (drought) or excess (heavy rain). Inputs: scenario slider, NASA POWER rainfall file, or live Open-Meteo (last 30 days + 14-day forecast vs the 1991-2020 normal).
3. **Risk = hazard / 100 x vulnerability.** Low below 15, Elevated 15 to under 30, High 30 or more. Districts with fewer than 30 survey households (Kicukiro, Gasabo, Nyarugenge) get no tier.
4. **Livestock risk = hazard / 100 x mean(vulnerability, cattle exposure)**, cattle exposure being the share of households keeping cattle, rescaled 0-100.
5. **Explanation:** every alert names the district's biggest weakness relative to other districts.

The thresholds (15, 30) and the 50% cap are transparent choices, not fitted to data.

**Machine learning:** the risk score is a visible rule, not ML. A ridge regression predicting district median yield from the AHS indicators was tested leave-one-district-out. Cross-validated R-squared: maize 0.15, bush bean 0.23, cassava 0.03, sweet potato 0.06 (about 25 districts): weak, and reported as such. The milk forecast demo uses synthetic data and is labelled DEMO.

## 5. Validation
District tables, weighted by estimated households, were compared with the published AHS 2024 report: improved seed, extension, cooperative membership, bank account and farms under 0.5 ha match NISR within 0.25 percentage points for the five provinces and nationally (30 of 30 comparisons, recomputed live in the app). Estimated farming households: 2,163,581 vs 2,164,000 published. **Known gap:** poverty is 22.6% here vs 25.9% in Table 2 (about 13% lower in every province), likely a different variable definition; forcing poverty to NISR values changes the index by at most 0.3 points and moves no district between tiers.

## 6. Strengths
Early signal before problems reach consumers; reaches basic phones in Kinyarwanda; built on NISR data with every tier explained; one signal for crops and livestock; open code and district tables.

## 7. Limits and risks
- Risk signal only; one survey year cannot train or test a forecasting model.
- No disease, pest or crop-price data; livestock risk uses cattle-keeping share only; milk data is provincial and single-year and is not part of the score.
- Movement restrictions are entered by the user from RAB notices.
- SMS and USSD are simulated; real delivery needs a telecom partner.
- Kinyarwanda text needs native-speaker review (`KINYARWANDA_REVIEW.csv`).
- District map positions are approximate centres.
- RAB and MINAGRI already monitor disease; Intumwa adds district-level, Kinyarwanda, vulnerability-aware messages.

## 8. Impact and next steps
Intended users: farmers, livestock keepers, cooperatives, dairies, district officers. This is a prototype, so no losses avoided can be claimed. A pilot would measure districts warned, time from signal to action, animals vaccinated early, and message comprehension. Next: native-speaker review and farmer testing; RAB (disease, vaccination, restrictions) and MINAGRI (prices) data; multi-year data such as the Seasonal Agriculture Survey to build a testable forecast; telecom partnership for real SMS/USSD.

## 9. Run it
```
python -m venv .venv
.venv\Scripts\activate        # Mac/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Works immediately in scenario mode. Optional: `python fetch_rainfall.py` (internet) adds real rainfall and the live-forecast option.

## 10. Sources
NISR, Agriculture Household Survey 2024 and report (Aug 2025); NASA POWER; Open-Meteo; RAB notices (user-entered); news reports cited in the brief (The New Times and others). Libraries: Streamlit, pandas, NumPy, Plotly, SciPy, Requests.
