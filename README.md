# semis-risk-lab

Risk analytics for ten semiconductor stocks, built from raw market data up to portfolio risk. Work in progress.

**Universe:** NVDA, AMD, AVGO, QCOM (design) · TSM, INTC, MU (manufacturing) · ASML, SNPS, CDNS (equipment and EDA)

**Benchmarks:** SOXX, SPY · **Period:** January 2016 to today, daily

## Status

| Stage | Status |
|---|---|
| Data pipeline (Python, SQLite) and SQL analysis | Done |
| Risk metrics: volatility, beta, Sharpe, drawdown, VaR, expected shortfall, tracking error | Next |
| Attribution: Brinson-Fachler and a Fama French 3-factor regression | Planned |
| Time series: stationarity tests, rolling beta, GARCH(1,1) | Planned |
| Machine learning: next-month realised volatility | Planned |
| LLM extraction of 10-K risk factors, with every quote verified against the filing | Planned |
| Automated daily run with GitHub Actions | Planned |

## Run it

Windows, Python 3.12.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe pipeline.py
```

This rebuilds `data/semis.db` from nothing. The database is not committed; the pipeline recreates it.

## Pipeline

`pipeline.py` runs extract, transform and load in five functions.

- **Extract:** daily prices from Yahoo Finance through `yfinance`, and the daily Fama French 3 factors from the Ken French Data Library.
- **Transform:** adjusted closes reshaped to one row per ticker per date; missing prices dropped rather than filled; factor file parsed by locating its header and footer, converted from percent to decimals, and checked for missing-value codes.
- **Load:** both tables replaced inside a single transaction.

| Table | Columns | Primary key |
|---|---|---|
| `prices` | ticker, date, adj_close | (ticker, date) |
| `factors` | date, mkt_rf, smb, hml, rf | date |

## Design decisions

- **Adjusted prices.** Returns use prices adjusted for splits and dividends, so a split does not appear as a loss.
- **Full refresh, never append.** Adjusted history is restated after every split and dividend, so each run reloads the full history.
- **Idempotent and crash safe.** Delete and insert run in one transaction, and the primary keys reject duplicates. Running twice gives identical row counts; a failed run rolls back to the previous data.
- **Source risk.** `yfinance` is an unofficial interface to Yahoo Finance and can break without notice. Extraction is isolated so a licensed data source could replace it without touching the rest.

## SQL

Written by hand in `sql/`:

1. `01_daily_returns.sql`: daily returns with `LAG` and `PARTITION BY ticker`
2. `02_returns_join_factors.sql`: returns joined to the Fama French market factor
3. `03_annual_returns.sql`: annual total returns from year-end prices with `GROUP BY`

## Known limitations

- Factor data is published monthly, so the latest weeks of prices have no matching factors.
- No 2016 annual return, because the price history starts in January 2016.
- The latest year in the annual return query is year to date.
