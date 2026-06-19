"""Live USD/BRL exchange-rate feed (Frankfurter API, ECB reference rates).

This is the "live API" source that flows through the same DAG as the batch
Olist CSV load. Daily rates land in raw.fx_rates; dbt forward-fills the
business-day rates to every calendar day (dim_fx_rates) and converts order GMV
to USD in fct_orders.

The API blocks the default urllib User-Agent (HTTP 403), so a UA header is set.
"""

from __future__ import annotations

import json
import urllib.request

from psycopg2.extras import execute_values

from extract.load_olist import RAW_SCHEMA, _connect

SINGLE_URL = "https://api.frankfurter.app/{date}?from=USD&to=BRL"
RANGE_URL = "https://api.frankfurter.dev/v1/{start}..{end}?base=USD&symbols=BRL"
USER_AGENT = "olist-etl/1.0 (+https://github.com/basilwright0/Olist-ETL)"


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_one(day: str) -> tuple[str, float]:
    """USD->BRL rate for `day` (or the most recent prior business day)."""
    data = _get_json(SINGLE_URL.format(date=day))
    return data["date"], data["rates"]["BRL"]


def fetch_range(start: str, end: str) -> dict[str, float]:
    """All business-day USD->BRL rates between start and end (inclusive)."""
    data = _get_json(RANGE_URL.format(start=start, end=end))
    return {d: r["BRL"] for d, r in data["rates"].items()}


def _ensure_table(cur) -> None:
    cur.execute(f"create schema if not exists {RAW_SCHEMA}")
    cur.execute(
        f"create table if not exists {RAW_SCHEMA}.fx_rates ("
        "rate_date text, base text, quote text, rate text, "
        "loaded_at timestamptz default now())"
    )


def _upsert(cur, rates: dict[str, float]) -> None:
    if not rates:
        return
    cur.execute(
        f"delete from {RAW_SCHEMA}.fx_rates where rate_date = any(%s)",
        (list(rates.keys()),),
    )
    execute_values(
        cur,
        f"insert into {RAW_SCHEMA}.fx_rates (rate_date, base, quote, rate) values %s",
        [(d, "USD", "BRL", str(r)) for d, r in rates.items()],
    )


def load_fx_for_interval(**context) -> None:
    """DAG task: fetch the run's logical-date USD/BRL rate into raw.fx_rates."""
    day = context["data_interval_start"].date().isoformat()
    rate_date, rate = fetch_one(day)
    conn = _connect()
    with conn:
        with conn.cursor() as cur:
            _ensure_table(cur)
            _upsert(cur, {rate_date: rate})
    conn.close()
    print(f"FX {day}: 1 USD = {rate} BRL (rate_date {rate_date})")


def backfill_fx_range(start: str, end: str) -> None:
    """Seed raw.fx_rates for a whole date range in one API call (history)."""
    rates = fetch_range(start, end)
    conn = _connect()
    with conn:
        with conn.cursor() as cur:
            _ensure_table(cur)
            _upsert(cur, rates)
    conn.close()
    print(f"FX backfill {start}..{end}: {len(rates)} business-day rates loaded")
