with geolocation as (

    select * from {{ ref('stg_olist__geolocation') }}

),

-- The raw geolocation table has many rows per zip prefix; collapse to one
-- row per prefix with an averaged centroid.
final as (

    select
        zip_code_prefix,
        max(state) as state,
        max(city)  as city,
        avg(latitude)  as latitude,
        avg(longitude) as longitude
    from geolocation
    group by zip_code_prefix

)

select * from final
