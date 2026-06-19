with spine as (

    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2016-01-01' as date)",
        end_date="cast('2019-01-01' as date)"
    ) }}

),

final as (

    select
        cast(date_day as date)              as date_day,
        extract(year    from date_day)::int as year,
        extract(quarter from date_day)::int as quarter,
        extract(month   from date_day)::int as month,
        extract(day     from date_day)::int as day_of_month,
        extract(dow     from date_day)::int as day_of_week,
        trim(to_char(date_day, 'Day'))      as day_name,
        extract(dow from date_day) in (0, 6) as is_weekend
    from spine

)

select * from final
