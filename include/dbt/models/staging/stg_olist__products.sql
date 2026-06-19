with source as (

    select * from {{ source('olist', 'products') }}

),

renamed as (

    select
        product_id,
        product_category_name,
        cast(nullif(product_photos_qty, '') as integer) as product_photos_qty,
        cast(nullif(product_weight_g, '') as numeric)   as product_weight_g,
        cast(nullif(product_length_cm, '') as numeric)  as product_length_cm,
        cast(nullif(product_height_cm, '') as numeric)  as product_height_cm,
        cast(nullif(product_width_cm, '') as numeric)   as product_width_cm
    from source

)

select * from renamed
