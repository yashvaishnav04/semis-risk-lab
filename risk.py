import sqlite3

import pandas as pd

DB_PATH = "data/semis.db"

STOCKS = ["NVDA", "AMD", "AVGO", "QCOM", "TSM", "INTC", "MU", "ASML", "SNPS", "CDNS"]
BENCHMARKS = ["SOXX", "SPY"]

# Portfolio weights, one per stock. They must sum to 1.
WEIGHTS = {
    "SNPS": 0.15,
    "CDNS": 0.15,
    "ASML": 0.12,
    "NVDA": 0.12,
    "TSM": 0.12,
    "AVGO": 0.10,
    "AMD": 0.08,
    "QCOM": 0.06,
    "MU": 0.05,
    "INTC": 0.05,
}


def load_prices():
    """Read the prices table and return adjusted closes, one column per ticker."""
    conn = sqlite3.connect(DB_PATH)
    try:
        long = pd.read_sql_query("SELECT ticker, date, adj_close FROM prices", conn)
    finally:
        conn.close()

    # Wide format (index date, columns ticker) makes row-wise return maths easy
    prices = long.pivot(index="date", columns="ticker", values="adj_close")
    prices.index = pd.to_datetime(prices.index)

    # Fail loudly instead of guessing: a missing ticker or price would silently skew risk numbers
    missing = [t for t in STOCKS + BENCHMARKS if t not in prices.columns]
    if missing:
        raise ValueError(f"Tickers missing from prices table: {missing}")
    if prices.isna().any().any():
        raise ValueError("Prices contain null values; refusing to fill them")

    return prices


def daily_returns(prices):
    """Simple daily return: today's price / yesterday's price - 1."""
    returns = prices / prices.shift(1) - 1
    # The first day has no previous price, so its return is NaN
    return returns.iloc[1:]


def portfolio_returns(returns):
    """Daily portfolio return as the weighted sum of the stock returns."""
    if set(WEIGHTS) != set(STOCKS):
        raise ValueError("WEIGHTS keys must exactly match STOCKS")
    if abs(sum(WEIGHTS.values()) - 1) > 1e-9:
        raise ValueError("WEIGHTS must sum to 1")

    # Align weights to the column order of the returns so each weight meets the right stock
    weights = pd.Series(WEIGHTS)[STOCKS]
    portfolio = returns[STOCKS].dot(weights)
    portfolio.name = "PORTFOLIO"
    return portfolio


def main():
    prices = load_prices()
    print("Prices shape:", prices.shape)
    print("Date range:", prices.index.min().date(), "to", prices.index.max().date())

    returns = daily_returns(prices)
    print("Returns shape:", returns.shape)
    print("NVDA return on 2026-08-27:", returns.loc["2026-08-27", "NVDA"])

    portfolio = portfolio_returns(returns)
    print("First three portfolio returns:")
    print(portfolio.head(3))


if __name__ == "__main__":
    main()
