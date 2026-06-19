with payments as (

    select * from {{ ref('stg_olist__order_payments') }}

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['order_id', 'payment_sequential']) }} as payment_id,
        order_id,
        payment_sequential,
        payment_type,
        payment_installments,
        payment_value
    from payments

)

select * from final
