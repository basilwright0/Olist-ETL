{#
  Use the schema name from the model config verbatim (staging, marts, ...)
  instead of dbt's default of prefixing it with the target schema. Keeps the
  warehouse tidy: analytics_staging -> staging, analytics_marts -> marts.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
