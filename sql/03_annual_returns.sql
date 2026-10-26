-- Annual total return per ticker: year-end adjusted close divided by the previous year-end close, minus 1.
-- 2016 is NULL because the data starts in January 2016. The latest year is year to date, not a full year.
WITH year_end AS (
    SELECT ticker, substr(date, 1, 4) AS year, MAX(date) AS last_date
    FROM prices
    GROUP BY ticker, year
),
year_end_price AS (
    SELECT year_end.ticker, year_end.year, prices.adj_close
    FROM year_end
    JOIN prices ON prices.ticker = year_end.ticker AND prices.date = year_end.last_date
)
SELECT ticker, year, adj_close / LAG(adj_close) OVER (PARTITION BY ticker ORDER BY year) - 1 AS annual_return
FROM year_end_price
WHERE ticker = 'NVDA'
ORDER BY year;
