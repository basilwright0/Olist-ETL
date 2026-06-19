with products as (

    select * from {{ ref('stg_olist__products') }}

),

categories as (

    select * from {{ ref('stg_olist__category_translation') }}

),

final as (

    select
        products.product_id,
        {{ dbt_utils.generate_surrogate_key(['products.product_id']) }} as product_key,
        coalesce(categories.category_name_english,
                 products.product_category_name,
                 'unknown') as product_category,
        products.product_weight_g,
        products.product_length_cm,
        products.product_height_cm,
        products.product_width_cm,
        products.product_photos_qty
    from products
    left join categories on products.product_category_name = categories.product_category_name

)

select * from final
