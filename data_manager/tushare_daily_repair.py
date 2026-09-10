"""Safe helpers for repairing QMT DAT daily volume/turnover from Tushare."""


def update_missing_daily_units(conn, dataframe) -> int:
    """Update only existing daily rows with missing turnover; preserve OHLC."""
    if dataframe is None or dataframe.empty:
        return 0
    repair = dataframe[['stock_code', 'date', 'volume', 'amount']].copy()
    conn.register('_tmp_daily_unit_repair', repair)
    try:
        matched = conn.execute("""
            SELECT COUNT(*)
            FROM stock_daily AS target
            JOIN _tmp_daily_unit_repair AS source
              ON target.stock_code = source.stock_code
             AND CAST(target.date AS DATE) = CAST(source.date AS DATE)
            WHERE target.period = '1d'
              AND (target.amount IS NULL OR target.amount = 0)
              AND source.volume IS NOT NULL
              AND source.amount IS NOT NULL
        """).fetchone()[0]
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute("""
                UPDATE stock_daily AS target
                SET volume = CAST(ROUND(source.volume) AS BIGINT),
                    amount = source.amount,
                    updated_at = CURRENT_TIMESTAMP
                FROM _tmp_daily_unit_repair AS source
                WHERE target.stock_code = source.stock_code
                  AND CAST(target.date AS DATE) = CAST(source.date AS DATE)
                  AND target.period = '1d'
                  AND (target.amount IS NULL OR target.amount = 0)
                  AND source.volume IS NOT NULL
                  AND source.amount IS NOT NULL
            """)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return int(matched)
    finally:
        conn.unregister('_tmp_daily_unit_repair')
