import sqlite3

import pandas as pd

DB_PATH = "data/semis.db"

# Approximate number of trading days in a year, used to annualise daily numbers
TRADING_DAYS = 252

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


def annualised_volatility(returns):
    """Sample standard deviation of each column, scaled from daily to yearly."""
    # Volatility grows with the square root of time, not linearly
    return returns.std(ddof=1) * TRADING_DAYS**0.5


def beta(returns, benchmark="SOXX"):
    """Beta of each column vs the benchmark: cov(column, benchmark) / var(benchmark)."""
    # Both use ddof=1 so the sample-size correction cancels consistently
    covariances = returns.cov(ddof=1)[benchmark]
    return covariances / returns[benchmark].var(ddof=1)


def load_factors():
    """Read the daily risk-free rate (rf) from the factors table, indexed by date."""
    conn = sqlite3.connect(DB_PATH)
    try:
        factors = pd.read_sql_query("SELECT date, rf FROM factors", conn)
    finally:
        conn.close()

    factors["date"] = pd.to_datetime(factors["date"])
    return factors.set_index("date")["rf"]


def sharpe_ratio(returns, rf):
    """Annualised Sharpe ratio: mean daily excess return / its sample std, scaled by sqrt(252)."""
    aligned = rf.reindex(returns.index)
    last_factor_date = rf.index.max()

    # A gap inside the factor history is bad data, so fail instead of guessing
    gaps = aligned[aligned.isna() & (aligned.index <= last_factor_date)]
    if not gaps.empty:
        raise ValueError(f"rf missing on {len(gaps)} dates within the factor range")

    # The factor file lags the prices, so carry the last known rf forward for the newest days
    newer = aligned.index > last_factor_date
    aligned[newer] = rf.iloc[-1]
    print(f"rf forward filled on {int(newer.sum())} days after {last_factor_date.date()}")

    excess = returns.sub(aligned, axis=0)
    return excess.mean() / excess.std(ddof=1) * TRADING_DAYS**0.5

def max_drawdown(returns):
    """Largest fall in value from its highest point so far, as a negative number."""
    wealth = (1+ returns).cumprod()
    peak = wealth.cummax()
    drawdown = wealth/peak - 1
    return drawdown.min()

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

    # Put the portfolio next to the tickers so one call scores everything
    all_returns = returns.join(portfolio)
    summary = pd.DataFrame(
        {
            "volatility": annualised_volatility(all_returns),
            "beta_vs_SOXX": beta(all_returns, "SOXX"),
            "sharpe": sharpe_ratio(all_returns, load_factors()),
            "max_drawdown": max_drawdown(all_returns),
        }
    )
    print(summary.round(3))


if __name__ == "__main__":
    main()
