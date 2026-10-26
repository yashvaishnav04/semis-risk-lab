# semis-risk-lab

Learning project by Yash: a public portfolio repo showing data and risk skills for equity research roles.

## Working rules
- Yash is a beginner and must be able to explain every line. Write simple, readable Python with short comments explaining WHY, not what.
- Do not write the three analysis SQL queries (daily returns with LAG, returns JOIN factors, annual returns GROUP BY). Yash writes those by hand. You may write the SQL that creates tables and loads data.
- Make small, focused changes. Do not create files that were not asked for.
- Environment: Windows, PowerShell. Python lives in .venv; run scripts with .venv\Scripts\python.exe.
- Never read or print .env.
- Do not run git commit or git push. Yash runs git himself.

## Data decisions (already made; ask before changing any)
- Tickers: NVDA, AMD, AVGO, QCOM, INTC, MU, TSM, ASML, SNPS, CDNS. Benchmarks: SOXX, SPY.
- Start date 2016-01-01 (whole calendar years). End date: today.
- Prices: yfinance with auto_adjust=True. Store only the adjusted close, in a column named adj_close.
- Factors: Fama French 3 factors, daily CSV from the Ken French Data Library:
  https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip
  - Skip the text lines at the top and the copyright line at the bottom.
  - Dates are YYYYMMDD; convert to YYYY-MM-DD.
  - Values are in percent; divide by 100.
  - Keep only dates from 2016-01-01.
- Database: SQLite file at data/semis.db (data/ is git-ignored).
  - prices(ticker TEXT, date TEXT, adj_close REAL, PRIMARY KEY (ticker, date)), long format.
  - factors(date TEXT PRIMARY KEY, mkt_rf REAL, smb REAL, hml REAL, rf REAL).
- Idempotency: every run downloads the full history and overwrites existing rows. Never append only new days, because adjusted prices are restated after every split and dividend.

## pipeline.py structure
- Five functions, extract_prices, extract_factors, transform_prices, transform_factors and load, called in order from main.
