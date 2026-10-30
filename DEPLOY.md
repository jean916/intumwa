# Put Intumwa online and get ready to present

## 1. Pre-flight (30 minutes)
0. `python check_apis.py` prints OK or FAIL for the NISR catalogue, Open-Meteo and NASA POWER on your network. Anything that fails is simply skipped by the app.
1. Rainfall (needs internet): `python fetch_rainfall.py --test`. If the one-district numbers look plausible (roughly -40 to +40), run `python fetch_rainfall.py`. It writes `data/rainfall_anomaly.csv` and `data/rainfall_normals.csv`; the sidebar then offers "Rainfall data file" and "Live forecast (Open-Meteo)". **Commit both files to GitHub** so the deployed app has them.
2. Send `KINYARWANDA_REVIEW.csv` to a native speaker; copy corrections into `app.py` (search for the text) and re-run.
3. Click through every tab once in both hazards. Take screenshots of each as a backup in case the venue wifi fails.
4. Check you have **not** included `.venv`, raw microdata (`.dta`) or personal data in the folder you publish (`.gitignore` already excludes `.venv`).

## 2. GitHub (public repository)
Web way: github.com > New repository > Public > "uploading an existing file" > drag in `app.py`, `requirements.txt`, `README.md`, `DEPLOY.md`,
`KINYARWANDA_REVIEW.csv`, `build_vulnerability.py`, `fetch_rainfall.py`, `.gitignore`, the `data` folder and the `.streamlit` folder.
Command line:
```
git init
git add .
git commit -m "Intumwa"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/intumwa.git
git push -u origin main
```

## 3. Free hosting (Streamlit Community Cloud)
1. share.streamlit.io > sign in with GitHub > **Create app**.
2. Repository: `YOUR-NAME/intumwa`, branch `main`, main file `app.py` > **Deploy**.
3. After about two minutes you get a public link like `https://intumwa.streamlit.app`. Put it in the PDF and the submission form.
4. Open the link on your phone to check it.

## 4. Four-minute demo order
1. **Problem (30 s):** 2026 milk shortage and RVF: signs existed, warnings reached farmers late.
2. **Risk map (60 s):** switch to **Live forecast** if the APIs work (otherwise drought 30%); show the top-10 list; "risk = weather x how vulnerable farmers are". Move the slider.
3. **Alerts (45 s):** a High district; Kinyarwanda SMS (one message); the reason chips; switch to heavy rain.
4. **Livestock (45 s):** choose the June 2026 RVF preset; the movement-restriction line appears. Show NISR's milk fall (4.0 to 2.8 litres).
5. **USSD (20 s):** type 1, 2, 3 on a basic-phone menu.
6. **Method & validation (40 s):** "30 of 30 comparisons match NISR"; be open about poverty and about it being a risk signal, not a forecast.
