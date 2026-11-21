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



# Announcement dates are meeting end dates from the Federal Reserve calendar.
# Unscheduled meetings and notation votes are intentionally excluded.
FOMC_DATES = [
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28",
]

FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"


def event_reaction(series: pd.Series, event: pd.Timestamp, multiplier: float, horizons=(0, 1, 5)):
    """Compare an event-day observation and subsequent valid observations with the prior one.

    Horizon 0 = event-date observation; +1 = next available observation after it;
    +5 = fifth available observation after it. No gaps are forward-filled.
    Returns rows with actual dates, so data lag is visible.
    """
    s = series.dropna().sort_index()
    before = s.loc[s.index < event]
    event_obs = s.loc[s.index == event]
    if before.empty or event_obs.empty:
        return None, "No valid observation on the announcement date or preceding it."
    baseline_date = before.index[-1]
    baseline = float(before.iloc[-1])
    after = s.loc[s.index >= event]
    if len(after) <= max(horizons):
        return None, "Not enough observations after the announcement for the selected horizons."
    result = []
    for horizon in horizons:
        date_at = after.index[horizon]
        value = float(after.iloc[horizon])
        change = (value - baseline) * multiplier if multiplier else ((value / baseline) - 1) * 100
        result.append({"Horizon": "Event day" if horizon == 0 else f"+{horizon} sessions",
                       "Observation date": date_at.date().isoformat(), "Change": change})
    return {"baseline_date": baseline_date, "baseline_value": baseline, "rows": result}, None


def event_chart(series: pd.Series, event: pd.Timestamp, title: str, multiplier: float, units: str):
    """Plot value changes relative to the last valid observation before the meeting."""
    valid = series.dropna().sort_index()
    prior = valid.loc[valid.index < event]
    on_day = valid.loc[valid.index == event]
    if prior.empty or on_day.empty:
        st.warning(f"{title}: missing baseline or event-date observation.")
        return
    baseline_date, baseline = prior.index[-1], float(prior.iloc[-1])
    left = valid.loc[(valid.index >= event - pd.Timedelta(days=14)) & (valid.index <= event + pd.Timedelta(days=14))]
    left = pd.concat([valid.loc[[baseline_date]], left]).sort_index()
    changes = (left - baseline) * multiplier if multiplier else (left / baseline - 1) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=changes.index, y=changes.values, mode="lines+markers", name=title))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.add_vline(x=event.timestamp() * 1000, line_dash="dash", line_color="gray")
    fig.update_layout(title=title, yaxis_title=units, height=345,
                      margin=dict(l=15, r=15, t=48, b=15), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)


def classify_curve_level(spread_bp: pd.Series, flat_threshold_bp: float) -> pd.Series:
    """Classify the observed 2s10s slope, with an explicit flat tolerance."""
    return spread_bp.map(lambda v: (
        "Inverted" if v < -flat_threshold_bp else
        "Upward sloping" if v > flat_threshold_bp else "Flat / near-flat"
    ))


def classify_curve_move(curve: pd.DataFrame, min_move_bp: float) -> pd.DataFrame:
    """Compare consecutive shared-observation sessions; avoid filling missing yields.

    Bull/bear refers to direction of the *average* of 2Y and 10Y yields.
    Steepening/flattening refers to the change in 10Y minus 2Y spread.
    Moves below tolerance are labelled unclassified, rather than forced into a quadrant.
    """
    out = curve.copy()
    out["2Y change (bp)"] = out["US 2Y Treasury Yield"].diff() * 100
    out["10Y change (bp)"] = out["US 10Y Treasury Yield"].diff() * 100
    out["Spread change (bp)"] = out["2s10s Spread (bp)"].diff()
    out["Average yield change (bp)"] = (out["2Y change (bp)"] + out["10Y change (bp)"]) / 2
    def describe(row):
        slope, avg = row["Spread change (bp)"], row["Average yield change (bp)"]
        if pd.isna(slope) or pd.isna(avg):
            return "N/A"
        if abs(slope) < min_move_bp or abs(avg) < min_move_bp:
            return "Mixed / small move"
        return ("Bull" if avg < 0 else "Bear") + (" steepening" if slope > 0 else " flattening")
    out["Curve move"] = out.apply(describe, axis=1)
    return out


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

rates_tab, fx_tab, analytics_tab, fomc_tab, curve_tab, data_tab = st.tabs([
    "Rates", "FX", "Analytics", "FOMC Event Study", "Yield Curve Analysis", "Data & Methodology"
])

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


with fomc_tab:
    st.subheader("FOMC announcement event study")
    st.write("Compare selected US Treasury and USD/SGD observations around scheduled Federal Reserve policy announcements.")
    eligible = [x for x in FOMC_DATES if pd.Timestamp(x).date() <= date.today()]
    selected = st.selectbox("Announcement date (US Eastern calendar date)",
                            list(reversed(eligible)),
                            format_func=lambda d: pd.Timestamp(d).strftime("%d %b %Y"))
    event_day = pd.Timestamp(selected)
    st.caption("The event study fetches its own date window. The main dashboard's sidebar date range does not affect it.")
    st.markdown(f"[Official Federal Reserve meeting calendar]({FOMC_CALENDAR_URL})")

    # Two calendar weeks before and three weeks after the announcement provide
    # a baseline and at least five post-event business sessions in normal circumstances.
    event_start = (event_day - pd.Timedelta(days=21)).date().isoformat()
    event_end = min((event_day + pd.Timedelta(days=21)).date(), date.today()).isoformat()
    event_columns = {
        "US 2Y Treasury Yield": "DGS2",
        "US 10Y Treasury Yield": "DGS10",
        "USD/SGD": "DEXSIUS",
    }
    try:
        with st.spinner("Loading announcement-window market data..."):
            event_data = {name: fetch_series(code, event_start, event_end, key)
                          for name, code in event_columns.items()}
    except (requests.RequestException, ValueError) as exc:
        st.error(f"Could not load FOMC event-window data: {exc}")
    else:
        configs = [
            ("US 2Y Treasury Yield", 100.0, "bp"),
            ("US 10Y Treasury Yield", 100.0, "bp"),
            ("USD/SGD", 0.0, "%"),
        ]
        columns = st.columns(3)
        rows = []
        for panel, (name, multiplier, unit) in zip(columns, configs):
            result, error = event_reaction(event_data[name], event_day, multiplier)
            if error:
                panel.warning(f"{name}: {error}")
                continue
            readings = result["rows"]
            panel.metric(name + " | event day", f"{readings[0]['Change']:+.2f} {unit}")
            panel.caption(f"Baseline {result['baseline_date'].date():%d %b %Y}; event observation {readings[0]['Observation date']}")
            for reading in readings:
                rows.append({"Instrument": name, "Horizon": reading["Horizon"],
                             "Observation date": reading["Observation date"],
                             "Baseline date": result["baseline_date"].date().isoformat(),
                             "Change": round(reading["Change"], 4), "Unit": unit})
        if rows:
            st.subheader("Event-window changes relative to pre-announcement baseline")
            table = pd.DataFrame(rows)
            st.dataframe(table, hide_index=True, use_container_width=True)
            st.download_button("Download event study (CSV)", table.to_csv(index=False),
                               f"fomc_event_{selected}.csv", "text/csv")
            a, b = st.columns(2)
            with a:
                event_chart(event_data["US 2Y Treasury Yield"], event_day, "2Y Treasury yield change", 100.0, "bp from baseline")
                event_chart(event_data["US 10Y Treasury Yield"], event_day, "10Y Treasury yield change", 100.0, "bp from baseline")
            with b:
                event_chart(event_data["USD/SGD"], event_day, "USD/SGD percentage change", 0.0, "% from baseline")
        st.info("Method: Baseline is the last available observation strictly before the announcement. "
                "Event day is the observation dated the announcement day; +1 and +5 sessions are subsequent valid "
                "observations in each series. Yield changes are in bp; FX changes are percentage changes. "
                "Daily data cannot isolate the immediate reaction to the announcement. Moves may reflect other "
                "news, trading-session timing, or broader macroeconomic conditions. Different series may have "
                "different observation timestamps. These are historical associations, not causal estimates.")


with curve_tab:
    st.subheader("Yield curve structure and trading interpretation")
    st.caption("The 2s10s spread compares the US 10-year and 2-year Treasury yields. "
               "Positive means upward sloping; negative means inverted.")

    curve = df[["US 2Y Treasury Yield", "US 10Y Treasury Yield", "2s10s Spread (bp)"]].dropna().copy()
    if len(curve) < 3:
        st.warning("Choose a longer sidebar date range to analyse Treasury curve regimes.")
    else:
        a, b = st.columns(2)
        with a:
            flat_threshold = st.slider("Flat-curve tolerance (± bp)", min_value=0, max_value=30,
                                       value=10, step=1,
                                       help="Spread between -threshold and +threshold is defined as flat/near-flat.")
        with b:
            move_threshold = st.slider("Minimum movement to classify (bp)", min_value=0.5,
                                       max_value=5.0, value=1.0, step=0.5,
                                       help="Both average yield change and spread change must meet this threshold.")
        curve["Curve level"] = classify_curve_level(curve["2s10s Spread (bp)"], flat_threshold)
        curve = classify_curve_move(curve, move_threshold)

        latest = curve.iloc[-1]
        change_bp = float(latest["Spread change (bp)"])
        average_change_bp = float(latest["Average yield change (bp)"])
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Latest 2s10s", f"{latest['2s10s Spread (bp)']:+.1f} bp",
                  delta=f"{change_bp:+.1f} bp", delta_color="off")
        m2.metric("Curve level", str(latest["Curve level"]))
        m3.metric("Last session move", str(latest["Curve move"]))
        m4.metric("Average yield move", f"{average_change_bp:+.1f} bp")
        st.caption(f"Last shared Treasury observation: {curve.index[-1]:%d %b %Y}. "
                   "Session changes compare consecutive dates on which both 2Y and 10Y observations exist.")

        st.subheader("Curve slope over time")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=curve.index, y=curve["2s10s Spread (bp)"],
                                 mode="lines", name="2s10s spread"))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.add_hline(y=flat_threshold, line_dash="dot", line_color="gray")
        fig.add_hline(y=-flat_threshold, line_dash="dot", line_color="gray")
        fig.update_layout(height=390, yaxis_title="basis points", hovermode="x unified",
                          margin=dict(l=15, r=15, t=25, b=10))
        st.plotly_chart(fig, use_container_width=True)

        left, right = st.columns(2)
        with left:
            st.subheader("Share of observed sessions by curve level")
            distribution = (curve["Curve level"].value_counts(normalize=True) * 100)
            order = ["Inverted", "Flat / near-flat", "Upward sloping"]
            distribution = distribution.reindex(order, fill_value=0)
            st.bar_chart(distribution.rename("Share of sessions (%)"))
            st.caption(f"Based on {len(curve):,} paired observation dates in the selected sidebar range. "
                       "These are observation shares, not calendar-day durations.")
        with right:
            st.subheader("Daily move classifications")
            move_counts = curve["Curve move"].iloc[1:].value_counts().rename("Sessions")
            st.bar_chart(move_counts)
            st.caption("'Mixed / small move' includes days where one or both movement measures are below "
                       "the selected threshold. Classifications describe historical moves, not trade signals.")

        st.subheader("Recent session-by-session curve analysis")
        display_columns = ["US 2Y Treasury Yield", "US 10Y Treasury Yield", "2s10s Spread (bp)",
                           "2Y change (bp)", "10Y change (bp)", "Spread change (bp)",
                           "Average yield change (bp)", "Curve level", "Curve move"]
        recent = curve[display_columns].tail(25).sort_index(ascending=False).copy()
        st.dataframe(recent, use_container_width=True)
        st.download_button("Download curve classifications (CSV)",
                           curve[display_columns].to_csv(index_label="date"),
                           "yield_curve_analysis.csv", mime="text/csv")

        st.subheader("How to interpret the four curve moves")
        st.markdown("""
        | Classification | Average yield move | 10Y–2Y spread move | Typical interpretation |
        |---|---|---|---|
        | Bull steepening | Down | Widens | Yields fall on average, with the curve becoming steeper |
        | Bear steepening | Up | Widens | Yields rise on average, with the curve becoming steeper |
        | Bull flattening | Down | Narrows | Yields fall on average, with the curve becoming flatter |
        | Bear flattening | Up | Narrows | Yields rise on average, with the curve becoming flatter |
        """)
        st.info("**Trading context:** A 2s10s spread change is a description of the relative "
                "move in yields. Translating this to a tradable Treasury position requires "
                "instrument choice, DV01/duration matching, financing costs, entry and exit rules, "
                "and risk limits. Bull/bear classifications here use the sign of the average of "
                "2Y and 10Y yield changes, with a configurable tolerance. They are descriptive "
                "labels, not trading recommendations or backtested returns.")


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
