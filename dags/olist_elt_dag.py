"""Olist ELT pipeline.

    load_reference_data  ->  load_orders_for_interval  ->  dbt_transform (Cosmos)

Each dbt model/test renders as its own Airflow task via Cosmos, so the DAG
graph shows full lineage. The DAG is dated to the Olist history (2016-2018):
unpausing it won't backfill automatically (catchup is off) — instead trigger a
date range, e.g.

    airflow dags backfill olist_elt -s 2017-01-01 -e 2017-03-31
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import TestBehavior

sys.path.append("/opt/airflow/include")
from extract.load_olist import load_orders_for_interval, load_reference_data  # noqa: E402
from fx.load_fx import load_fx_for_interval  # noqa: E402

DBT_PROJECT_DIR = Path("/opt/airflow/include/dbt")
DBT_EXECUTABLE = "/opt/dbt-venv/bin/dbt"

profile_config = ProfileConfig(
    profile_name="olist",
    target_name="dev",
    profiles_yml_filepath=DBT_PROJECT_DIR / "profiles.yml",
)

default_args = {
    "owner": "data-engineering",
    "retries": 2,
}

with DAG(
    dag_id="olist_elt",
    description="Olist e-commerce ELT: extract/load + dbt transforms",
    start_date=datetime(2016, 9, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["olist", "elt", "portfolio"],
) as dag:

    load_reference = PythonOperator(
        task_id="load_reference_data",
        python_callable=load_reference_data,
    )

    load_orders = PythonOperator(
        task_id="load_orders_for_interval",
        python_callable=load_orders_for_interval,
    )

    # Live API source: same DAG run also pulls that day's USD/BRL rate.
    load_fx = PythonOperator(
        task_id="load_fx_for_interval",
        python_callable=load_fx_for_interval,
    )

    transform = DbtTaskGroup(
        group_id="dbt_transform",
        project_config=ProjectConfig(DBT_PROJECT_DIR),
        profile_config=profile_config,
        execution_config=ExecutionConfig(dbt_executable_path=DBT_EXECUTABLE),
        render_config=RenderConfig(
            test_behavior=TestBehavior.AFTER_EACH,
            dbt_executable_path=DBT_EXECUTABLE,
        ),
        operator_args={"install_deps": True},
    )

    load_reference >> load_orders >> transform
    load_fx >> transform
