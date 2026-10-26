-- Daily return per ticker: today's adjusted close divided by the previous trading day's, minus 1.
-- PARTITION BY ticker keeps LAG inside each stock, so one stock is never compared with another.
SELECT ticker, date, adj_close / LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date) - 1 AS daily_return
FROM prices
WHERE ticker = 'NVDA'
ORDER BY date
LIMIT 5;