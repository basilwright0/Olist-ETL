-- USD/BRL rate for every calendar day. ECB only publishes on business days,
-- so each rate is carried forward until the next published rate (an as-of
-- join), giving weekends and holidays the last known rate.
with rates as (

    select
        rate_date,
        brl_per_usd,
        lead(rate_date) over (order by rate_date) as next_rate_date
    from {{ ref('stg_fx__rates') }}

),

dates as (

    select date_day from {{ ref('dim_dates') }}

)

select
    dates.date_day,
    rates.brl_per_usd
from dates
join rates
    on dates.date_day >= rates.rate_date
   and (dates.date_day < rates.next_rate_date or rates.next_rate_date is null)
