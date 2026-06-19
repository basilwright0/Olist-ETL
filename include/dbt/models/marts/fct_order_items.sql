{{
    config(
        materialized='incremental',
        unique_key='order_item_id',
        on_schema_change='append_new_columns'
    )
}}

with items as (

    select
        {{ dbt_utils.generate_surrogate_key(['order_id', 'order_item_number']) }} as order_item_id,
        order_id,
        order_item_number,
        product_id,
        seller_id,
        product_category,
        price,
        freight_value,
        gross_item_value,
        order_date
    from {{ ref('int_order_items_joined') }}

)

select * from items

{% if is_incremental() %}

-- Only process line items whose order is newer than what we've already loaded.
-- This is what lets daily Airflow runs (and backfills) stay cheap + idempotent.
where order_date > (select coalesce(max(order_date), '1900-01-01') from {{ this }})

{% endif %}
