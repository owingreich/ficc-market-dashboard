# FICC Market Analytics Dashboard

A Python/Streamlit historical dashboard for US Treasury yields, 2s10s curve, USD/SGD, and the Fed target-rate upper bound using FRED API data.

## Local setup (macOS / PyCharm)

1. Open this folder as a project in PyCharm.
2. In PyCharm Terminal, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

3. Make a copy of `.streamlit/secrets.toml.example` named `.streamlit/secrets.toml`, and replace `PASTE_YOUR_FRED_API_KEY_HERE` with your own key from https://fred.stlouisfed.org/docs/api/api_key.html. Keep this file private and do not commit it.
4. Run:

```bash
python -m streamlit run app.py
```

5. Your browser should open the app, usually at http://localhost:8501.

## Deploy

1. Commit `app.py`, `requirements.txt`, `README.md`, `.gitignore`, and `.streamlit/secrets.toml.example` to a GitHub repo. **Do not commit `.streamlit/secrets.toml`.**
2. Open https://share.streamlit.io, connect your GitHub account, and deploy your repository with entrypoint `app.py`.
3. Under app secrets (advanced settings), add `FRED_API_KEY = "your_actual_key"`.
4. Launch the deployed app and confirm charts load.

## Notes

- Market observations are historical and may lag. Treat displayed dates as source observation dates.
- DEXSIUS measures SGD per USD.
- All figures are research/education and are not investment advice.
- Review data licensing before redistribution.
