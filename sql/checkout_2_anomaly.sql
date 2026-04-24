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
    END AS relative_deviation,
    ((same_day_last_week + avg_last_week + avg_last_month) / 3.0) >= 5.0 AS is_material,
    CASE
        WHEN ((same_day_last_week + avg_last_week + avg_last_month) / 3.0) < 5.0 THEN 'normal'
        WHEN
            today - ((same_day_last_week + avg_last_week + avg_last_month) / 3.0) >= 8
            AND (
                CASE
                    WHEN (same_day_last_week + avg_last_week + avg_last_month) = 0 THEN 0
                    ELSE (
                        today - ((same_day_last_week + avg_last_week + avg_last_month) / 3.0)
                    ) / ((same_day_last_week + avg_last_week + avg_last_month) / 3.0)
                END
            ) >= 0.5 THEN 'surge'
        WHEN
            today - ((same_day_last_week + avg_last_week + avg_last_month) / 3.0) <= -8
            AND (
                CASE
                    WHEN (same_day_last_week + avg_last_week + avg_last_month) = 0 THEN 0
                    ELSE (
                        today - ((same_day_last_week + avg_last_week + avg_last_month) / 3.0)
                    ) / ((same_day_last_week + avg_last_week + avg_last_month) / 3.0)
                END
            ) <= -0.5 THEN 'drop'
        ELSE 'normal'
    END AS direction,
    ((same_day_last_week + avg_last_week + avg_last_month) / 3.0) >= 5.0
    AND today = 0.0 AS zero_gap,
    CASE
        WHEN ((same_day_last_week + avg_last_week + avg_last_month) / 3.0) >= 5.0 THEN ABS(
            today - ((same_day_last_week + avg_last_week + avg_last_month) / 3.0)
        )
        ELSE 0.0
    END AS severity_score
FROM read_csv_auto('database/checkout_2.csv')
ORDER BY time;

