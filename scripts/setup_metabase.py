#!/usr/bin/env python3
"""Provision the Olist Metabase dashboard from code (infrastructure-as-code).

Idempotent. The script will:
  1. Complete Metabase first-run setup (create the admin user) or log in.
  2. Connect the Postgres warehouse as a data source.
  3. Create/update the six question cards (native SQL on the `marts` schema).
  4. Create/rebuild the "Olist E-Commerce Analytics" dashboard layout.

Run it from the host (Metabase's API is on localhost:3000). The warehouse
connection details are from *Metabase's* perspective — it reaches the database
over the docker network — so they default to host=warehouse, port=5432.

    python scripts/setup_metabase.py

Configuration via environment variables (all optional):
    MB_URL             Metabase base URL          (default http://localhost:3000)
    MB_ADMIN_EMAIL     admin email                (default admin@example.com)
    MB_ADMIN_PASSWORD  admin password             (default OlistDemo2026!)
    MB_SITE_NAME       site name                  (default Olist Analytics)
    WH_HOST WH_PORT WH_DB WH_USER WH_PASSWORD     warehouse connection

Note: against an already-initialised Metabase the script logs in, so
MB_ADMIN_EMAIL / MB_ADMIN_PASSWORD must match the existing admin account.

Standard library only — no `pip install` required.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

MB_URL = os.getenv("MB_URL", "http://localhost:3000").rstrip("/")
ADMIN_EMAIL = os.getenv("MB_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("MB_ADMIN_PASSWORD", "OlistDemo2026!")
SITE_NAME = os.getenv("MB_SITE_NAME", "Olist Analytics")

DB_NAME = "Olist Warehouse"
DB_DETAILS = {
    "host": os.getenv("WH_HOST", "warehouse"),
    "port": int(os.getenv("WH_PORT", "5432")),
    "dbname": os.getenv("WH_DB", "warehouse"),
    "user": os.getenv("WH_USER", "warehouse"),
    "password": os.getenv("WH_PASSWORD", "warehouse"),
    "ssl": False,
    "tunnel-enabled": False,
}

DASHBOARD_NAME = "Olist E-Commerce Analytics"

# Each card: native SQL on the marts, its display type + viz settings, and its
# position on the 24-column dashboard grid.
CARDS = [
    {
        "tag": "orders", "name": "Total orders", "display": "scalar",
        "sql": "select count(*) as orders from marts.fct_orders",
        "viz": {},
        "pos": {"col": 0, "row": 0, "size_x": 6, "size_y": 3},
    },
    {
        "tag": "gmv", "name": "Total GMV (R$)", "display": "scalar",
        "sql": "select round(sum(total_payment_value)::numeric, 0) as gmv "
               "from marts.fct_orders",
        "viz": {},
        "pos": {"col": 6, "row": 0, "size_x": 6, "size_y": 3},
    },
    {
        "tag": "monthly", "name": "Monthly GMV", "display": "line",
        "sql": "select date_trunc('month', order_date)::date as month, "
               "round(sum(total_payment_value)::numeric, 2) as gmv "
               "from marts.fct_orders group by 1 order by 1",
        "viz": {"graph.dimensions": ["month"], "graph.metrics": ["gmv"]},
        "pos": {"col": 12, "row": 0, "size_x": 12, "size_y": 7},
    },
    {
        "tag": "state", "name": "Orders by customer state (top 12)", "display": "row",
        "sql": "select customer_state, count(*) as orders from marts.fct_orders "
               "where customer_state is not null group by 1 order by 2 desc limit 12",
        "viz": {"graph.dimensions": ["customer_state"], "graph.metrics": ["orders"]},
        "pos": {"col": 0, "row": 3, "size_x": 12, "size_y": 7},
    },
    {
        "tag": "review", "name": "Avg delivery days by review score", "display": "bar",
        "sql": "select review_score, round(avg(delivery_days)::numeric, 1) "
               "as avg_delivery_days from marts.fct_orders "
               "where review_score is not null and delivery_days is not null "
               "group by 1 order by 1",
        "viz": {"graph.dimensions": ["review_score"],
                "graph.metrics": ["avg_delivery_days"]},
        "pos": {"col": 12, "row": 7, "size_x": 12, "size_y": 7},
    },
    {
        "tag": "category", "name": "Top categories by revenue", "display": "row",
        "sql": "select product_category, round(sum(gross_item_value)::numeric, 2) "
               "as revenue from marts.fct_order_items "
               "where product_category is not null group by 1 order by 2 desc limit 12",
        "viz": {"graph.dimensions": ["product_category"], "graph.metrics": ["revenue"]},
        "pos": {"col": 0, "row": 10, "size_x": 12, "size_y": 7},
    },
]


def api(method: str, path: str, session: str | None = None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{MB_URL}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if session:
        req.add_header("X-Metabase-Session", session)
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"API {method} {path} -> {exc.code}: {exc.read().decode()}")


def _as_list(resp):
    if isinstance(resp, dict) and "data" in resp:
        return resp["data"]
    return resp or []


def get_session() -> str:
    props = api("GET", "/api/session/properties")
    if not props.get("has-user-setup"):
        print("First-run setup: creating admin user...")
        resp = api("POST", "/api/setup", body={
            "token": props["setup-token"],
            "user": {
                "first_name": "Admin", "last_name": "User",
                "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
                "site_name": SITE_NAME,
            },
            "prefs": {"site_name": SITE_NAME, "site_locale": "en",
                      "allow_tracking": False},
        })
        return resp["id"]
    print(f"Logging in as {ADMIN_EMAIL}...")
    return api("POST", "/api/session",
               body={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})["id"]


def ensure_database(session: str) -> int:
    for db in _as_list(api("GET", "/api/database", session)):
        if db.get("name") == DB_NAME:
            print(f"Database '{DB_NAME}' already connected (id={db['id']}).")
            return db["id"]
    print(f"Connecting database '{DB_NAME}'...")
    db = api("POST", "/api/database", session,
             body={"engine": "postgres", "name": DB_NAME, "details": DB_DETAILS})
    return db["id"]


def ensure_cards(session: str, db_id: int) -> dict[str, int]:
    by_name = {c["name"]: c["id"] for c in _as_list(api("GET", "/api/card", session))}
    ids: dict[str, int] = {}
    for card in CARDS:
        payload = {
            "name": card["name"],
            "dataset_query": {"type": "native",
                              "native": {"query": card["sql"]}, "database": db_id},
            "display": card["display"],
            "visualization_settings": card["viz"],
        }
        if card["name"] in by_name:
            cid = by_name[card["name"]]
            api("PUT", f"/api/card/{cid}", session, body=payload)
            print(f"  updated card  '{card['name']}' (id={cid})")
        else:
            cid = api("POST", "/api/card", session, body=payload)["id"]
            print(f"  created card  '{card['name']}' (id={cid})")
        ids[card["tag"]] = cid
    return ids


def ensure_dashboard(session: str, card_ids: dict[str, int]) -> int:
    dash_id = None
    for dash in _as_list(api("GET", "/api/dashboard", session)):
        if dash.get("name") == DASHBOARD_NAME:
            dash_id = dash["id"]
            break
    if dash_id is None:
        dash_id = api("POST", "/api/dashboard", session,
                      body={"name": DASHBOARD_NAME})["id"]
        print(f"Created dashboard '{DASHBOARD_NAME}' (id={dash_id}).")
    else:
        print(f"Dashboard '{DASHBOARD_NAME}' exists (id={dash_id}); rebuilding layout.")

    dashcards = [
        {
            "id": -(i + 1), "card_id": card_ids[c["tag"]],
            "row": c["pos"]["row"], "col": c["pos"]["col"],
            "size_x": c["pos"]["size_x"], "size_y": c["pos"]["size_y"],
            "series": [], "parameter_mappings": [], "visualization_settings": {},
        }
        for i, c in enumerate(CARDS)
    ]
    api("PUT", f"/api/dashboard/{dash_id}", session, body={"dashcards": dashcards})
    return dash_id


def main() -> None:
    print(f"Metabase: {MB_URL}")
    session = get_session()
    db_id = ensure_database(session)
    card_ids = ensure_cards(session, db_id)
    dash_id = ensure_dashboard(session, card_ids)
    print(f"\nDone -> {MB_URL}/dashboard/{dash_id}")


if __name__ == "__main__":
    main()
