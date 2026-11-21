# FICC Market Analytics Dashboard

An interactive financial market dashboard built using Python and Streamlit to analyse US Treasury yields, yield curve dynamics, USD/SGD exchange rates, and Federal Reserve monetary policy.

The project explores relationships between fixed income markets, foreign exchange movements, and macroeconomic conditions through historical market data and quantitative analysis.

## Project Overview

Fixed Income, Currencies and Commodities (FICC) markets are closely linked through interest rate expectations, monetary policy decisions, and changing macroeconomic conditions.

This dashboard provides a consolidated interface for examining these relationships, with an initial focus on US interest rates and the USD/SGD currency pair.

The project focuses on three areas:

- **Market monitoring:** Tracking Treasury yields, yield curve spreads, exchange rates, and policy interest rates.
- **Quantitative analysis:** Examining historical market volatility, daily price and yield changes, and cross-asset correlations.
- **Financial interpretation:** Understanding how movements in interest rates and currencies relate to broader macroeconomic developments.

## Key Features

### 1. US Treasury Market Analysis

- Historical 2-year and 10-year US Treasury yields.
- Interactive yield charts with adjustable date ranges.
- Daily yield changes measured in basis points.
- 2s10s Treasury yield spread analysis.
- Federal Reserve target interest rate tracking.

### 2. Foreign Exchange Analysis

- Historical USD/SGD exchange rates.
- Interactive exchange rate visualisations.
- Daily percentage return calculations.
- Historical foreign exchange volatility.

### 3. Quantitative Market Analytics

- 20-observation rolling volatility for Treasury yield changes and FX returns.
- Historical correlation between US 10-year Treasury yield changes and USD/SGD returns.
- Date-aligned historical observations.
- Descriptive analysis of cross-asset market movements.

### 4. Data Exploration

- User-defined historical analysis periods.
- Cached data retrieval from the FRED API.
- Historical observation tables.
- CSV export for further financial analysis.

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Application Framework | Streamlit |
| Data Processing | pandas, NumPy |
| Data Visualisation | Plotly |
| Market Data | Federal Reserve Economic Data (FRED) |
| Version Control | GitHub |
| Deployment | Streamlit Community Cloud |

## Data Sources

Historical financial market data are retrieved through the Federal Reserve Bank of St. Louis FRED API.

| Market Indicator | FRED Series |
|---|---|
| US 2-Year Treasury Yield | DGS2 |
| US 10-Year Treasury Yield | DGS10 |
| USD/SGD Exchange Rate | DEXSIUS |
| Federal Funds Target Range Upper Limit | DFEDTARU |

Data are subject to the publication schedules, observation frequencies, and availability constraints of their respective sources.

## Quantitative Methodology

**2s10s Yield Spread**

The difference between 10-year and 2-year US Treasury yields, expressed in basis points:

2s10s Spread = (10Y Yield - 2Y Yield) × 100

**Daily Treasury Yield Changes**

Calculated as the difference between consecutive available yield observations, expressed in basis points.

**Foreign Exchange Returns**

Calculated using the percentage change between consecutive available exchange rate observations.

**Rolling Volatility**

Measured using the standard deviation of daily yield changes or FX returns over a rolling 20-observation window.

**Cross-Asset Correlation**

Measured using Pearson correlation between US 10-year Treasury yield changes and USD/SGD daily returns, using up to the most recent 60 aligned observations.

These metrics provide descriptive insights into historical market behaviour and should not be interpreted as standalone predictive trading signals.

## Running Locally

**Requirements:** Python 3.12+ and a FRED API key.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Configure the FRED API key in `.streamlit/secrets.toml`:

```toml
FRED_API_KEY = "your_api_key"
```

Launch the application:

```bash
python -m streamlit run app.py
```

## Limitations

- The dashboard uses historical observations rather than real-time market data.
- Market holidays, publication delays, and differences in reporting frequency affect data availability.
- Historical correlations do not establish causal relationships or predictive trading performance.
- The analysis currently focuses on selected US interest rate and USD/SGD indicators rather than the full FICC market universe.

## Future Development

Planned extensions include:

- FOMC announcement event studies.
- Historical market reaction analysis around monetary policy decisions.
- Rule-based trading hypothesis testing.
- Additional risk metrics and market scenario analysis.
- Expanded cross-asset coverage.

## Disclaimer

This project is intended for financial market research, quantitative analysis, and educational purposes. It does not constitute investment advice or a recommendation to trade financial instruments.

Market data are attributed to their respective providers through FRED and remain subject to applicable usage and redistribution terms.
