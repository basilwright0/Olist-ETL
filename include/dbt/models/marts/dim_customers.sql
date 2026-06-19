with customers as (

    select * from {{ ref('stg_olist__customers') }}

),

-- Grain: one row per *real* customer (customer_unique_id), not per order.
-- This is what makes repeat-purchase analysis possible.
final as (

    select
        customer_unique_id,
        {{ dbt_utils.generate_surrogate_key(['customer_unique_id']) }} as customer_key,
        count(distinct customer_id) as order_account_count,
        max(state) as customer_state,
        max(city)  as customer_city
    from customers
    group by customer_unique_id

)

select * from final
