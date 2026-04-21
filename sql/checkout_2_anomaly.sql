SELECT
    time,
    today,
    yesterday,
    same_day_last_week,
    avg_last_week,
    avg_last_month,
    (same_day_last_week + avg_last_week + avg_last_month) / 3.0 AS baseline,
    today - ((same_day_last_week + avg_last_week + avg_last_month) / 3.0) AS absolute_deviation,
    CASE
        WHEN (same_day_last_week + avg_last_week + avg_last_month) = 0 THEN 0
        ELSE (
            today - ((same_day_last_week + avg_last_week + avg_last_month) / 3.0)
        ) / ((same_day_last_week + avg_last_week + avg_last_month) / 3.0)
    END AS relative_deviation
FROM checkout_2
ORDER BY time;

