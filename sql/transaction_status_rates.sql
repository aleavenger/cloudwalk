WITH transactions AS (
    SELECT *
    FROM read_csv_auto('database/transactions.csv')
),
per_minute AS (
    SELECT
        timestamp,
        SUM(CASE WHEN status = 'approved' THEN count ELSE 0 END) AS approved,
        SUM(CASE WHEN status = 'denied' THEN count ELSE 0 END) AS denied,
        SUM(CASE WHEN status = 'failed' THEN count ELSE 0 END) AS failed,
        SUM(CASE WHEN status = 'reversed' THEN count ELSE 0 END) AS reversed,
        SUM(CASE WHEN status = 'backend_reversed' THEN count ELSE 0 END) AS backend_reversed,
        SUM(CASE WHEN status = 'refunded' THEN count ELSE 0 END) AS refunded
    FROM transactions
    GROUP BY timestamp
),
totals AS (
    SELECT
        timestamp,
        approved,
        denied,
        failed,
        reversed,
        backend_reversed,
        refunded,
        (approved + denied + failed + reversed + backend_reversed + refunded) AS total
    FROM per_minute
)
SELECT
    timestamp,
    approved,
    denied,
    failed,
    reversed,
    backend_reversed,
    refunded,
    total,
    (approved * 1.0 / NULLIF(total, 0)) AS approved_rate,
    (denied * 1.0 / NULLIF(total, 0)) AS denied_rate,
    (failed * 1.0 / NULLIF(total, 0)) AS failed_rate,
    (reversed * 1.0 / NULLIF(total, 0)) AS reversed_rate
FROM totals
ORDER BY timestamp;

