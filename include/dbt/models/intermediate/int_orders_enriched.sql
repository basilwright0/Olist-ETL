with orders as (

    select * from {{ ref('stg_olist__orders') }}

),

customers as (

    select * from {{ ref('stg_olist__customers') }}

),

joined as (

    select
        orders.order_id,
        orders.customer_id,
        customers.customer_unique_id,
        customers.state as customer_state,
        customers.city  as customer_city,
        orders.order_status,
        orders.purchased_at,
        orders.approved_at,
        orders.delivered_to_customer_at,
        orders.estimated_delivery_at,

        -- actual delivery time in days (null until delivered)
        case
            when orders.delivered_to_customer_at is not null
            then extract(epoch from (orders.delivered_to_customer_at - orders.purchased_at)) / 86400.0
        end as delivery_days,

        -- positive => late vs. the estimate, negative => early
        case
            when orders.delivered_to_customer_at is not null
                 and orders.estimated_delivery_at is not null
            then extract(epoch from (orders.delivered_to_customer_at - orders.estimated_delivery_at)) / 86400.0
        end as delivery_vs_estimate_days,

        case
            when orders.delivered_to_customer_at is null then null
            when orders.delivered_to_customer_at <= orders.estimated_delivery_at then true
            else false
        end as delivered_on_time

    from orders
    left join customers on orders.customer_id = customers.customer_id

)

select * from joined
