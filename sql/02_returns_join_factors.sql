-- Daily returns matched to the Fama French market factor on the same date.
-- The JOIN keeps only dates present in both tables, so results stop where the factor data stops.
WITH returns AS (
    SELECT ticker, date, adj_close / LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date) - 1 AS daily_return
    FROM prices
)
SELECT returns.ticker, returns.date, returns.daily_return, factors.mkt_rf
FROM returns
JOIN factors ON returns.date = factors.date
WHERE returns.ticker = 'NVDA'
ORDER BY returns.date
LIMIT 5;
