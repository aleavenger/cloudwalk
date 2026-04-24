WITH transactions AS (
    SELECT *
    FROM read_csv_auto('database/transactions.csv')
),
transactions_auth_codes AS (
    SELECT *
    FROM read_csv_auto('database/transactions_auth_codes.csv')
)
SELECT
    t.timestamp,
    t.status,
    t.count AS status_count,
    a.auth_code,
    a.count AS auth_code_count
FROM transactions t
LEFT JOIN transactions_auth_codes a
    ON t.timestamp = a.timestamp
WHERE t.timestamp IN (
    '2025-07-12 17:18:00',
    '2025-07-14 06:33:00',
    '2025-07-15 04:30:00'
)
ORDER BY t.timestamp, t.status, a.auth_code;

