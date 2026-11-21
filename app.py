from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="FICC Market Dashboard", page_icon="📈", layout="wide")

SERIES = {
    "US 2Y Treasury Yield": "DGS2",
    "US 10Y Treasury Yield": "DGS10",
    "USD/SGD": "DEXSIUS",
    "Fed Target Rate (Upper Bound)": "DFEDTARU",
}


def api_key():
    try:
        key = st.secrets.get("FRED_API_KEY", "")
    except (FileNotFoundError, KeyError):
        key = ""
    return str(key).strip()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_series(series_id: str, start: str, end: str, key: str) -> pd.Series:
    response = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
        },
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    if "observations" not in payload:
        raise ValueError(f"Unexpected FRED response for {series_id}: {payload}")
    records = payload["observations"]
    if not records:
        raise ValueError(f"No observations returned for {series_id}.")
    values = pd.Series(
        {pd.Timestamp(r["date"]): pd.to_numeric(r["value"], errors="coerce") for r in records},
        name=series_id,
        dtype="float64",
    )
    return values.sort_index()


def latest_pair(s: pd.Series):
    valid = s.dropna()
    if valid.empty:
        return None, None, None
    latest = float(valid.iloc[-1])
    previous = float(valid.iloc[-2]) if len(valid) > 1 else None
    return latest, previous, valid.index[-1].date()


def line_chart(data: pd.DataFrame, columns: list[str], title: str, suffix: str = ""):
    fig = go.Figure()
    for col in columns:
        fig.add_trace(go.Scatter(x=data.index, y=data[col], mode="lines", name=col))
    fig.update_layout(
        title=title,
        height=400,
        margin=dict(l=15, r=15, t=50, b=15),
        legend=dict(orientation="h", y=-0.2),
        hovermode="x unified",
        yaxis_title=suffix,
    )
    st.plotly_chart(fig, use_container_width=True)


st.title("FICC Market Analytics Dashboard")
st.caption("US rates, yield-curve structure, and USD/SGD | Historical daily observations from FRED")

with st.sidebar:
    st.header("Controls")
    start_date = st.date_input("Start date", value=date.today() - timedelta(days=730), max_value=date.today())
    end_date = st.date_input("End date", value=date.today(), max_value=date.today())
    st.caption("Treasury yields and policy rates are quoted in percent. Yield changes/spreads are expressed in basis points (bp).")
    if st.button("Refresh data"):
        fetch_series.clear()
        st.rerun()

if start_date >= end_date:
    st.error("Start date must precede end date.")
    st.stop()

key = api_key()
if not key:
    st.error("FRED API key missing. Create .streamlit/secrets.toml with FRED_API_KEY = \"your_key_here\" (see README).")
    st.stop()

try:
    with st.spinner("Loading FRED historical data..."):
        raw = {
            name: fetch_series(code, start_date.isoformat(), end_date.isoformat(), key)
            for name, code in SERIES.items()
        }
except (requests.RequestException, ValueError) as exc:
    st.error(f"FRED data request failed: {exc}")
    st.info("Check your API key, internet connection, and selected dates, then try Refresh data.")
    st.stop()

df = pd.concat(raw.values(), axis=1)
df.columns = list(raw.keys())
df["2s10s Spread (bp)"] = (df["US 10Y Treasury Yield"] - df["US 2Y Treasury Yield"]) * 100

cols = st.columns(4)
metric_specs = [
    ("US 2Y Yield", "US 2Y Treasury Yield", "%", 100),
    ("US 10Y Yield", "US 10Y Treasury Yield", "%", 100),
    ("2s10s Spread", "2s10s Spread (bp)", " bp", 1),
    ("USD/SGD", "USD/SGD", "", 1),
]
for container, (label, column, unit, scale) in zip(cols, metric_specs):
    latest, previous, last_date = latest_pair(df[column])
    if latest is None:
        container.metric(label, "N/A")
        continue
    precision = 4 if column == "USD/SGD" else 2
    value_text = f"{latest:.{precision}f}{unit}"
    delta = (latest - previous) * scale if previous is not None else None
    delta_text = f"{delta:+.4f}" if column == "USD/SGD" and delta is not None else (f"{delta:+.1f} bp" if delta is not None else None)
    container.metric(label, value_text, delta=delta_text, delta_color="off")
    container.caption(f"As of {last_date:%d %b %Y}")

rates_tab, fx_tab, analytics_tab, data_tab = st.tabs(["Rates", "FX", "Analytics", "Data & Methodology"])

with rates_tab:
    line_chart(df, ["US 2Y Treasury Yield", "US 10Y Treasury Yield"], "US Treasury Yields", "%")
    line_chart(df, ["2s10s Spread (bp)"], "10Y minus 2Y Treasury Spread", "basis points")
    line_chart(df, ["Fed Target Rate (Upper Bound)"], "Federal Funds Target Range Upper Limit", "%")

with fx_tab:
    line_chart(df, ["USD/SGD"], "USD/SGD Exchange Rate", "SGD per USD")
    st.info("A higher USD/SGD rate means one US dollar buys more Singapore dollars (USD strengthening relative to SGD).")

with analytics_tab:
    st.subheader("Rolling 20-observation changes and volatility")
    st.caption("Rates: changes in basis points. FX: daily percentage returns. Rolling calculations exclude missing observations within each individual series.")
    a, b = st.columns(2)
    for panel, column, unit_multiplier, label in [
        (a, "US 10Y Treasury Yield", 100, "10Y daily yield change (bp)"),
        (b, "USD/SGD", None, "USD/SGD daily percentage return (%)"),
    ]:
        valid = df[column].dropna()
        daily = valid.diff() * unit_multiplier if unit_multiplier is not None else valid.pct_change(fill_method=None) * 100
        rolling = daily.rolling(20, min_periods=20).std()
        with panel:
            st.line_chart(rolling.rename("20-observation rolling standard deviation"))
            st.caption(label + " | standard deviation, not annualised")
    st.subheader("Daily correlation: 10Y yield changes vs USD/SGD returns")
    paired = df[["US 10Y Treasury Yield", "USD/SGD"]].dropna()
    changes = pd.DataFrame({
        "10Y yield change (bp)": paired["US 10Y Treasury Yield"].diff() * 100,
        "USD/SGD return (%)": paired["USD/SGD"].pct_change(fill_method=None) * 100,
    }).dropna()
    if len(changes) >= 20:
        corr = changes.iloc[-min(len(changes), 60):].corr().iloc[0, 1]
        st.metric("Correlation (up to last 60 shared observations)", f"{corr:.2f}" if pd.notna(corr) else "N/A")
        st.caption("Descriptive historical correlation. It does not establish causation or a profitable trading strategy.")
    else:
        st.warning("Choose a longer date range for correlation analysis.")

with data_tab:
    st.subheader("Latest observations and downloadable data")
    st.dataframe(df.tail(30).sort_index(ascending=False), use_container_width=True)
    st.download_button("Download historical observations (CSV)", df.to_csv(index_label="date"), "ficc_market_data.csv", "text/csv")
    st.markdown("""
    **Sources:** [FRED](https://fred.stlouisfed.org/) series
    [DGS2](https://fred.stlouisfed.org/series/DGS2),
    [DGS10](https://fred.stlouisfed.org/series/DGS10),
    [DEXSIUS](https://fred.stlouisfed.org/series/DEXSIUS),
    [DFEDTARU](https://fred.stlouisfed.org/series/DFEDTARU).

    **Methodology:** 2s10s spread = (10Y yield − 2Y yield) × 100 bp.
    Yield daily change = current observation − prior available observation, × 100 bp.
    Treasury yields and USD/SGD are generally business-day observations; policy target may have a different publication schedule.
    Missing values remain missing in source data, and observation dates are displayed explicitly.

    **Limitations:** This is a historical research tool, not a real-time trading platform. FRED publication delays,
    holidays, revisions and differences in observation timing affect comparability. Rolling statistics are illustrative.
    Please review source licensing and attribution terms before redistributing data.
    """)
