with orders as (

    select * from {{ ref('int_orders_enriched') }}

),

items as (

    select
        order_id,
        count(*)            as item_count,
        sum(price)          as items_price,
        sum(freight_value)  as freight_value
    from {{ ref('stg_olist__order_items') }}
    group by order_id

),

payments as (

    select
        order_id,
        sum(payment_value) as total_payment_value,
        count(*)           as payment_count
    from {{ ref('stg_olist__order_payments') }}
    group by order_id

),

reviews as (

    select
        order_id,
        max(review_score) as review_score
    from {{ ref('stg_olist__order_reviews') }}
    group by order_id

),

final as (

    select
        orders.order_id,
        {{ dbt_utils.generate_surrogate_key(['orders.customer_unique_id']) }} as customer_key,
        orders.order_status,
        orders.purchased_at,
        cast(orders.purchased_at as date) as order_date,
        orders.customer_state,
        orders.delivery_days,
        orders.delivery_vs_estimate_days,
        orders.delivered_on_time,
        coalesce(items.item_count, 0)     as item_count,
        items.items_price,
        items.freight_value,
        payments.total_payment_value,
        reviews.review_score
    from orders
    left join items    on orders.order_id = items.order_id
    left join payments on orders.order_id = payments.order_id
    left join reviews  on orders.order_id = reviews.order_id

)

select * from final
