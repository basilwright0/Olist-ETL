with source as (

    select * from {{ source('olist', 'category_translation') }}

),

renamed as (

    select
        product_category_name,
        product_category_name_english as category_name_english
    from source

)

select * from renamed
