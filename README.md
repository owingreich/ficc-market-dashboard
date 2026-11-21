# FICC Market Analytics Dashboard

**Interactive research dashboard for US Treasury rates, yield-curve dynamics, USD/SGD and Federal Reserve policy events.**

[Live dashboard](https://ficc-market-dashboard.streamlit.app) | [GitHub repository](https://github.com/owingreich/ficc-market-dashboard)

## Overview

This project uses Python and Streamlit to explore historical relationships across interest rates, foreign exchange and monetary-policy events. It combines market-monitoring charts, FOMC event windows, yield-curve classifications and a rule-based 2s10s strategy research module. Its primary emphasis is transparent, reproducible exploratory analysis, including the limitations of testing trading ideas with end-of-day economic data.

## Features

| Module | Functionality |
| --- | --- |
| Rates | US 2-year and 10-year Treasury yields, 2s10s spread and Federal funds target-range upper limit |
| FX | Historical USD/SGD observations and interactive charts |
| Analytics | Rolling 20-observation volatility of 10Y yield changes and USD/SGD returns; recent cross-asset correlation |
| FOMC Event Study | Selected scheduled announcement dates, pre-event baselines, event-day and subsequent-session changes, charts and CSV export |
| Yield Curve Analysis | Flat, inverted and upward-sloping regimes; bull/bear steepening and flattening using configurable thresholds |
| Strategy Research | Mean-reversion and momentum spread hypotheses, chronological training/holdout comparison, parameter search, performance and risk diagnostics |
| Data & Methodology | Historical observation table, sources and CSV exports |

## Historical data

The application retrieves observations via the Federal Reserve Bank of St. Louis [FRED API](https://fred.stlouisfed.org/docs/api/fred/).

| Series | Description |
| --- | --- |
| [DGS2](https://fred.stlouisfed.org/series/DGS2) | 2-year US Treasury constant-maturity yield, % |
| [DGS10](https://fred.stlouisfed.org/series/DGS10) | 10-year US Treasury constant-maturity yield, % |
| [DEXSIUS](https://fred.stlouisfed.org/series/DEXSIUS) | Singapore dollars per US dollar |
| [DFEDTARU](https://fred.stlouisfed.org/series/DFEDTARU) | Federal funds target-range upper limit, % |

Data frequencies, publication lags, missing observations and quote conventions vary by series. Charts label historical data and should not be treated as live executable prices.

## Quantitative methodology

### Rates and cross-asset statistics

- **2s10s spread (bp)** = `(10Y yield (%) - 2Y yield (%)) × 100`.
- **Daily yield change (bp)** = `(yield_t - yield_(t-1)) × 100` on consecutive valid observations.
- **USD/SGD return (%)** = `(FX_t / FX_(t-1) - 1) × 100`.
- **Rolling volatility** = sample standard deviation of the previous 20 valid daily changes or returns, not annualised.
- **Cross-asset correlation** = Pearson correlation using up to 60 recent shared-date observations of 10Y yield changes and USD/SGD returns.

### FOMC event windows

For selected scheduled FOMC announcement dates, the reference value is the last available observation before the event. Changes are reported on the event date and after one and five subsequent available observations. These are **daily event-window associations**, not estimates of the immediate intraday announcement effect or causality. The selected event list is coded from the [Federal Reserve meeting calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).

### Yield-curve regimes

The curve's level is classified by whether the 2s10s spread is positive, negative or within a configurable near-flat band. Movements are described as bull/bear steepening or flattening, based on the direction of the average 2Y/10Y yield change and the change in the spread. Movements smaller than the selected tolerance remain unclassified.

### Strategy research

The research hypothesis examines whether unusually large deviations in the 2s10s spread from its recent mean are followed by reversal. A matched momentum comparator takes the opposite directional position on the same eligible signals.

1. Compute a z-score at observation `t` against a rolling mean and standard deviation from **prior observations only**.
2. Enter a hypothetical long-spread position at the next paired observation if the z-score is below the negative threshold; enter short-spread if it is above the positive threshold. Momentum reverses the direction.
3. Exit after a configurable number of subsequent paired observations. Positions do not overlap.
4. Score each result as `direction × (exit spread - entry spread) - hypothetical round-trip cost`, all in **spread-proxy basis points**.
5. Split observations chronologically. Training trades must exit before the cutoff; holdout trades must enter on or after it. Trades crossing the boundary are excluded.
6. Optionally select parameters from a predefined 27-combination grid using training mean net proxy, then display the separate holdout evaluation.

Reported statistics include positive-trade rate, mean and aggregate spread proxy, proxy drawdown, profit factor, win/loss averages, annual outcomes, a training-only parameter sensitivity heatmap, trade ledger and CSV exports.

## Example research finding

In an exploratory analysis of January 2018 to November 2026 using a 60-observation lookback, 1.5 z-score threshold, five-session holding period, 1 bp assumed proxy cost and a 70% chronological training split, the mean-reversion hypothesis produced a negative training aggregate but a modest positive holdout aggregate. This divergence illustrates sensitivity to market regime and sample selection; it **does not demonstrate a reliable trading edge**. Results depend on the selected dates, data availability and parameters and should be rechecked against the running app.

## Technology

Python, Streamlit, pandas, NumPy, Plotly, Requests, FRED API and GitHub. Deployment uses Streamlit Community Cloud.

## Run locally

Requires Python 3.12+ and a free FRED API key.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` in your local working directory:

```toml
FRED_API_KEY = "YOUR_FRED_API_KEY"
```

**Never commit `secrets.toml` or disclose your API key.** Launch the app:

```bash
python -m streamlit run app.py
```

For Streamlit Community Cloud, configure `FRED_API_KEY` in the app's Secrets settings.

## Limitations

- FRED observations are historical reference series, with differing release times and possible revisions. Signals based on the observation at `t` might not have been actionable at that point in live trading.
- Hypothetical entry at the `t+1` published observation is not a verified executable price.
- **Spread-proxy basis points are not bond or futures returns, dollars, DV01-neutral curve-trade P&L, or capital-weighted performance.** Instrument pricing, hedge ratios, financing, realistic execution and risk limits are outside the model.
- The round-trip cost is a user-defined sensitivity assumption expressed in proxy bp, not a measured trading cost.
- The chronological holdout is exploratory historical validation, not untouched external testing, especially once results have been viewed during development. Parameter searches can overfit training history.
- Correlation and event-window moves do not establish causation.
- The app focuses on selected fixed-income and FX indicators; it does not cover the full commodities universe.

## Disclaimer

For education and market research only. The dashboard does not provide financial advice, investment recommendations or evidence of an implementable trading strategy. Data remain subject to the providers' terms and attribution requirements.
