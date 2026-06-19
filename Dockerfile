FROM apache/airflow:2.10.5

# Python deps used by the extract/load tasks + Cosmos (the Airflow<->dbt bridge).
# These are installed into Airflow's own environment, so they must stay
# compatible with the Airflow 2.10.5 constraints.
COPY requirements-airflow.txt /requirements-airflow.txt
RUN pip install --no-cache-dir -r /requirements-airflow.txt

# dbt lives in its own isolated virtualenv so its dependencies never clash
# with Airflow's. Cosmos invokes this interpreter via ExecutionConfig.
USER root
# Pin dbt-core to the stable 1.8 line. dbt-postgres's metadata has a
# pre-release lower bound, so without this pip resolves dbt-core to the
# 2.0 "Fusion" alpha, which doesn't support the Postgres adapter.
RUN python -m venv /opt/dbt-venv \
    && /opt/dbt-venv/bin/pip install --no-cache-dir "dbt-core>=1.8,<1.9" "dbt-postgres>=1.8,<1.9"
USER airflow
