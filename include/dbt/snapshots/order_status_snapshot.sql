{#
  Slowly-changing-dimension demo: track how an order's status evolves over
  time. With the static Olist dataset most orders have a single final status,
  but the snapshot machinery is exactly what you'd use against a mutating
  source table (e.g. an operational orders table updated in place).
#}
{% snapshot order_status_snapshot %}

{{
    config(
        unique_key='order_id',
        strategy='check',
        check_cols=['order_status']
    )
}}

select
    order_id,
    order_status,
    purchased_at
from {{ ref('stg_olist__orders') }}

{% endsnapshot %}
