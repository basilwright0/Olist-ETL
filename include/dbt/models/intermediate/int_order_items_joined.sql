with items as (

    select * from {{ ref('stg_olist__order_items') }}

),

products as (

    select * from {{ ref('stg_olist__products') }}

),

categories as (

    select * from {{ ref('stg_olist__category_translation') }}

),

orders as (

    select * from {{ ref('stg_olist__orders') }}

),

joined as (

    select
        items.order_id,
        items.order_item_number,
        items.product_id,
        items.seller_id,
        coalesce(categories.category_name_english,
                 products.product_category_name,
                 'unknown') as product_category,
        items.price,
        items.freight_value,
        items.price + items.freight_value as gross_item_value,
        orders.purchased_at,
        cast(orders.purchased_at as date) as order_date
    from items
    left join products   on items.product_id = products.product_id
    left join categories on products.product_category_name = categories.product_category_name
    left join orders     on items.order_id = orders.order_id

)

select * from joined
