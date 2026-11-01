import sqlite3

import pandas as pd

DB_PATH = "data/semis.db"

# Approximate number of trading days in a year, used to annualise daily numbers
TRADING_DAYS = 252

# Confidence level for VaR and expected shortfall: 95% means we look at the worst 5% of days
CONFIDENCE = 0.95

# Where write_report saves the Markdown report (overwritten on every run)
REPORT_PATH = "risk_report.md"

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

def historical_var(returns, confidence=CONFIDENCE):
    """Historical VaR: the (1 - confidence) quantile of daily returns, kept negative."""
    # No sign flip: a loss stays a negative return, like max_drawdown
    return returns.quantile(1 - confidence)


def expected_shortfall(returns, confidence=CONFIDENCE):
    """Expected shortfall: the mean of the daily returns at or below the VaR."""
    var = historical_var(returns, confidence)
    # le aligns the VaR Series to the columns, so each stock is compared to its own VaR
    tail = returns.where(returns.le(var))
    es = tail.mean()

    # The average of the tail cannot be above its cut-off; if it is, something is wrong
    if (es > var).any():
        raise ValueError("Expected shortfall is greater than VaR for at least one column")
    return es

def correlation_matrix(returns):
    """Pairwise correlation of the daily returns of the 10 stocks (Pearson, the pandas default)."""
    # Only the stocks: benchmarks and the portfolio would just repeat the same information
    return returns[STOCKS].corr()

def tracking_error(portfolio, benchmark):
    """Annualised sample std of the daily active return (portfolio minus benchmark)."""
    active = portfolio - benchmark
    return active.std(ddof=1) * TRADING_DAYS**0.5

def information_ratio(portfolio, benchmark):
    """Annualised mean daily active return divided by the tracking error."""
    active = portfolio - benchmark
    # Mean scales linearly with time, while the tracking error already scales with sqrt of time
    return active.mean() * TRADING_DAYS / tracking_error(portfolio, benchmark)

def markdown_table(headers, rows):
    """Turn a header list and a list of rows (lists of strings) into a Markdown table."""
    # Plain string joins, so no extra package (like tabulate) is needed
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

def write_report(summary, all_returns):
    """Write the risk report as Markdown to REPORT_PATH, overwriting any old file."""
    last_factor_date = load_factors().index.max().date()
    first_date = all_returns.index.min().date()
    last_date = all_returns.index.max().date()

    # Biggest weight first; sorted is stable, so ties keep their order from WEIGHTS
    weight_rows = [
        [ticker, f"{weight * 100:.1f}%"]
        for ticker, weight in sorted(WEIGHTS.items(), key=lambda item: item[1], reverse=True)
    ]

    # These four are shown as percentages, beta and Sharpe are plain ratios
    # Stocks first, then the benchmarks, then the portfolio, instead of alphabetical order
    summary_rows = []
    for name, row in summary.loc[STOCKS + BENCHMARKS + ["PORTFOLIO"]].iterrows():
        summary_rows.append(
            [
                name,
                f"{row['volatility'] * 100:.1f}%",
                f"{row['beta_vs_SOXX']:.2f}",
                f"{row['sharpe']:.2f}",
                f"{row['max_drawdown'] * 100:.1f}%",
                f"{row['var_95'] * 100:.1f}%",
                f"{row['es_95'] * 100:.1f}%",
            ]
        )

    portfolio = all_returns["PORTFOLIO"]
    soxx = all_returns["SOXX"]
    te = tracking_error(portfolio, soxx)
    ir = information_ratio(portfolio, soxx)

    corr = correlation_matrix(all_returns)
    corr_rows = [[name] + [f"{value:.2f}" for value in row] for name, row in corr.iterrows()]

    lines = [
        "# Semiconductor Portfolio Risk Report",
        "",
        f"Data period: {first_date} to {last_date} (daily returns). Last factor date: {last_factor_date}.",
        "",
        "## Portfolio weights",
        "",
        markdown_table(["Ticker", "Weight"], weight_rows),
        "",
        "## Summary",
        "",
        markdown_table(
            ["Ticker", "Volatility", "Beta vs SOXX", "Sharpe", "Max drawdown", "VaR 95%", "ES 95%"],
            summary_rows,
        ),
        "",
        "## Portfolio vs SOXX",
        "",
        f"- Tracking error: {te * 100:.1f}%",
        f"- Information ratio: {ir:.2f}",
        "",
        "## Correlation matrix",
        "",
        markdown_table([""] + list(corr.columns), corr_rows),
        "",
        "## Method notes",
        "",
        "- Returns are simple daily returns computed from adjusted closes.",
        f"- Volatility and the Sharpe ratio are annualised with {TRADING_DAYS} trading days.",
        "- Beta is measured against SOXX, the sector benchmark.",
        "- The Sharpe ratio uses the Fama French daily rf; after the last factor date the last known rf is carried forward.",
        f"- VaR and expected shortfall are one-day {CONFIDENCE:.0%} historical figures.",
        "- The portfolio uses fixed weights, rebalanced daily.",
        "- The weights were chosen in 2026, so the backtest contains hindsight.",
        "",
    ]

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    return REPORT_PATH

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
            "var_95": historical_var(all_returns),
            "es_95": expected_shortfall(all_returns),
        }
    )
    print(summary.round(3))

    print("Correlation matrix of daily stock returns:")
    print(correlation_matrix(all_returns).round(2))
    # SOXX is not in the matrix, so check one stock against it directly
    print("Check: SNPS vs SOXX correlation:", round(all_returns["SNPS"].corr(all_returns["SOXX"]), 3))

    print("Portfolio vs SOXX")
    print("Tracking error:", round(tracking_error(all_returns["PORTFOLIO"], all_returns["SOXX"]), 3))
    print("Information ratio:", round(information_ratio(all_returns["PORTFOLIO"], all_returns["SOXX"]), 3))

    print("Report written to:", write_report(summary, all_returns))


if __name__ == "__main__":
    main()
