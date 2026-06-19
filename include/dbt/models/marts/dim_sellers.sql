with sellers as (

    select * from {{ ref('stg_olist__sellers') }}

),

final as (

    select
        seller_id,
        {{ dbt_utils.generate_surrogate_key(['seller_id']) }} as seller_key,
        state as seller_state,
        city  as seller_city,
        zip_code_prefix
    from sellers

)

select * from final
