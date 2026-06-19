with source as (

    select * from {{ source('olist', 'geolocation') }}

),

renamed as (

    select
        geolocation_zip_code_prefix as zip_code_prefix,
        cast(geolocation_lat as numeric) as latitude,
        cast(geolocation_lng as numeric) as longitude,
        geolocation_city            as city,
        geolocation_state           as state
    from source

)

select * from renamed
