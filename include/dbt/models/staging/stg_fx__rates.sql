with source as (

    select * from {{ source('fx', 'fx_rates') }}

),

renamed as (

    select
        cast(rate_date as date)     as rate_date,
        base                        as base_currency,
        quote                       as quote_currency,
        cast(rate as numeric(12, 6)) as brl_per_usd
    from source

)

select * from renamed
