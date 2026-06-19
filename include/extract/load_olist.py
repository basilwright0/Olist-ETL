"""Extract + load helpers for the Olist ELT pipeline.

Raw CSVs (downloaded from Kaggle into ``data/raw/``) are loaded into the
warehouse ``raw`` schema as text using PostgreSQL ``COPY`` (fast + low memory).
Reference tables are full-refreshed by streaming the CSV straight to the
database; orders/order_items are loaded one logical day at a time so the static
Kaggle dump behaves like a daily feed and supports idempotent backfills.
"""

from __future__ import annotations

import csv
import io
import os

import pandas as pd
import psycopg2

RAW_SCHEMA = os.getenv("RAW_SCHEMA", "raw")
DATA_DIR = os.getenv("DATA_DIR", "/opt/airflow/data/raw")

# Relatively static tables: full-refreshed each run (cheap via COPY).
REFERENCE_FILES = {
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

ORDERS_FILE = "olist_orders_dataset.csv"
ORDER_ITEMS_FILE = "olist_order_items_dataset.csv"


def _connect():
    return psycopg2.connect(
        host=os.getenv("WAREHOUSE_HOST", "warehouse"),
        port=os.getenv("WAREHOUSE_PORT", "5432"),
        user=os.getenv("WAREHOUSE_USER", "warehouse"),
        password=os.getenv("WAREHOUSE_PASSWORD", "warehouse"),
        dbname=os.getenv("WAREHOUSE_DB", "warehouse"),
    )


def _csv_header(path: str) -> list[str]:
    # utf-8-sig strips a leading BOM (present in some Olist CSVs) so column
    # names don't pick up an invisible ﻿ prefix.
    with open(path, encoding="utf-8-sig") as fh:
        return next(csv.reader(fh))


def _create_text_table(cur, table: str, columns: list[str]) -> None:
    cols = ", ".join(f'"{c}" text' for c in columns)
    cur.execute(f"create table if not exists {RAW_SCHEMA}.{table} ({cols})")


def _table_exists(cur, table: str) -> bool:
    cur.execute("select to_regclass(%s) is not null", (f"{RAW_SCHEMA}.{table}",))
    return cur.fetchone()[0]


def load_reference_data(**_) -> None:
    """Full-refresh the static reference tables by streaming each CSV via COPY."""
    conn = _connect()
    with conn:
        with conn.cursor() as cur:
            cur.execute(f"create schema if not exists {RAW_SCHEMA}")
            for table, filename in REFERENCE_FILES.items():
                path = os.path.join(DATA_DIR, filename)
                # CREATE IF NOT EXISTS + TRUNCATE (not DROP) so the dbt staging
                # views that depend on these raw tables stay valid.
                _create_text_table(cur, table, _csv_header(path))
                cur.execute(f"truncate table {RAW_SCHEMA}.{table}")
                with open(path, encoding="utf-8-sig") as fh:
                    cur.copy_expert(
                        f"copy {RAW_SCHEMA}.{table} from stdin "
                        f"with (format csv, header true)",
                        fh,
                    )
                print(f"Loaded {RAW_SCHEMA}.{table} from {filename}")
    conn.close()


def _copy_dataframe(cur, table: str, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cols = ", ".join(f'"{c}"' for c in df.columns)
    cur.copy_expert(
        f"copy {RAW_SCHEMA}.{table} ({cols}) from stdin with (format csv)", buf
    )


def _load_day(cur, table: str, df: pd.DataFrame, day: str) -> None:
    """Idempotent per-day load: delete this day's rows, then COPY them in."""
    df = df.copy()
    df["_loaded_for_date"] = day
    if _table_exists(cur, table):
        cur.execute(
            f"delete from {RAW_SCHEMA}.{table} where _loaded_for_date = %s", (day,)
        )
    else:
        _create_text_table(cur, table, list(df.columns))
    _copy_dataframe(cur, table, df)


def load_orders_for_interval(**context) -> None:
    """Load orders + their items for the run's logical date only."""
    day = context["data_interval_start"].date().isoformat()

    orders = pd.read_csv(os.path.join(DATA_DIR, ORDERS_FILE), dtype=str)
    orders_day = orders[orders["order_purchase_timestamp"].str[:10] == day]

    items = pd.read_csv(os.path.join(DATA_DIR, ORDER_ITEMS_FILE), dtype=str)
    items_day = items[items["order_id"].isin(orders_day["order_id"])]

    print(f"{len(orders_day)} orders / {len(items_day)} items for {day}")

    conn = _connect()
    with conn:
        with conn.cursor() as cur:
            cur.execute(f"create schema if not exists {RAW_SCHEMA}")
            _load_day(cur, "orders", orders_day, day)
            _load_day(cur, "order_items", items_day, day)
    conn.close()
