with source as (

    select * from {{ source('olist', 'order_items') }}

),

renamed as (

    select
        order_id,
        cast(order_item_id as integer)             as order_item_number,
        product_id,
        seller_id,
        nullif(shipping_limit_date, '')::timestamp as shipping_limit_at,
        cast(price as numeric(12, 2))              as price,
        cast(freight_value as numeric(12, 2))      as freight_value
    from source

)

select * from renamed
