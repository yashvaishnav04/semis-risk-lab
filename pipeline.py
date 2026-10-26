import io
import sqlite3
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

TICKERS = ["NVDA", "AMD", "AVGO", "QCOM", "INTC", "MU", "TSM", "ASML", "SNPS", "CDNS"]
BENCHMARKS = ["SOXX", "SPY"]
START_DATE = "2016-01-01"
DB_PATH = Path("data") / "semis.db"
FACTORS_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_daily_CSV.zip"
)


def extract_prices():
    # auto_adjust=True so prices are already adjusted for splits and dividends
    # Always download the full history, because adjusted prices get restated over time
    return yf.download(
        TICKERS + BENCHMARKS,
        start=START_DATE,
        end=date.today().isoformat(),
        auto_adjust=True,
    )


def extract_factors():
    # timeout so the pipeline fails instead of hanging if the site stops responding
    response = requests.get(FACTORS_URL, timeout=30)
    # Stop here with a clear error if the download failed, instead of parsing junk later
    response.raise_for_status()

    # The download is a zip file, so open it in memory and read the one CSV inside
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        csv_name = zf.namelist()[0]
        # Return the text as is; cleaning belongs in the transform stage
        return zf.read(csv_name).decode("utf-8")


def transform_prices(raw):
    # Keep only Close; with auto_adjust=True it is already the adjusted close
    close = raw["Close"]

    # Wide (one column per ticker) to long (one row per ticker and date)
    long = close.reset_index().melt(
        id_vars="Date", var_name="ticker", value_name="adj_close"
    )
    long = long.rename(columns={"Date": "date"})

    # SQLite has no date type, so store dates as YYYY-MM-DD text
    long["date"] = long["date"].dt.strftime("%Y-%m-%d")

    # Drop missing prices; forward filling would invent prices that never traded
    missing = long["adj_close"].isna().sum()
    long = long.dropna(subset=["adj_close"])
    print("Missing price rows dropped:", missing)

    # The primary key is (ticker, date), so duplicates would break the load
    long = long.drop_duplicates(subset=["ticker", "date"])

    return long.reset_index(drop=True)


def transform_factors(text):
    lines = text.splitlines()

    # Find the header by its leading comma, so extra text lines at the top do not matter
    header_index = next(i for i, line in enumerate(lines) if line.startswith(","))

    # Read data rows until the first line that does not start with a digit,
    # which is where the copyright footer begins
    data_lines = []
    for line in lines[header_index + 1:]:
        if not line[:1].isdigit():
            break
        data_lines.append(line)

    csv_text = lines[header_index] + "\n" + "\n".join(data_lines)
    df = pd.read_csv(io.StringIO(csv_text))

    # The first column has no name in the file, so name it date
    df = df.rename(columns={df.columns[0]: "date"})

    # -99.99 and -999 mean "missing" in the source; fail loudly instead of using them as returns
    factor_cols = df.columns[1:]
    if df[factor_cols].isin([-99.99, -999]).any().any():
        raise ValueError("Factor data contains a missing-value code (-99.99 or -999)")

    # Dates arrive as YYYYMMDD numbers; convert to YYYY-MM-DD text
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d").dt.strftime(
        "%Y-%m-%d"
    )

    # Values are in percent, so divide by 100 to get decimals
    df[factor_cols] = df[factor_cols] / 100
    df.columns = ["date", "mkt_rf", "smb", "hml", "rf"]

    # YYYY-MM-DD text sorts in date order, so a string comparison works here
    df = df[df["date"] >= START_DATE]

    df = df.drop_duplicates(subset=["date"])

    return df.reset_index(drop=True)


def load(prices, factors):
    # SQLite creates the file but not the folder, so make sure data/ exists first
    DB_PATH.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        # IF NOT EXISTS keeps the primary keys and lets the script be run repeatedly
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                ticker TEXT,
                date TEXT,
                adj_close REAL,
                PRIMARY KEY (ticker, date)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS factors (
                date TEXT PRIMARY KEY,
                mkt_rf REAL,
                smb REAL,
                hml REAL,
                rf REAL
            )
            """
        )

        # "with conn" is one transaction: commit if it succeeds, roll back if anything fails,
        # so a crash halfway leaves the previous complete data untouched
        with conn:
            # Delete everything and reinsert, because adjusted prices are restated over time
            conn.execute("DELETE FROM prices")
            conn.execute("DELETE FROM factors")

            # Column order here must match the table columns above
            conn.executemany(
                "INSERT INTO prices (ticker, date, adj_close) VALUES (?, ?, ?)",
                prices[["ticker", "date", "adj_close"]].itertuples(index=False, name=None),
            )
            conn.executemany(
                "INSERT INTO factors (date, mkt_rf, smb, hml, rf) VALUES (?, ?, ?, ?, ?)",
                factors[["date", "mkt_rf", "smb", "hml", "rf"]].itertuples(
                    index=False, name=None
                ),
            )
    finally:
        conn.close()


def main():
    raw_prices = extract_prices()
    factors_text = extract_factors()

    prices = transform_prices(raw_prices)
    factors = transform_factors(factors_text)

    print("Price rows per ticker:")
    print(prices.groupby("ticker").size())

    print("Factors first 3 rows:")
    print(factors.head(3))
    print("Factors last 3 rows:")
    print(factors.tail(3))
    print("Factors total rows:", len(factors))

    load(prices, factors)

    # Read the counts back from the database to confirm what was actually stored
    conn = sqlite3.connect(DB_PATH)
    try:
        for table in ["prices", "factors"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table} rows in database:", count)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
