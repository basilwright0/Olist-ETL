-- Singular data-quality test: any order marked 'delivered' must have an
-- actual delivery timestamp. Returned rows = failing records.
select
    order_id,
    order_status,
    delivered_to_customer_at
from {{ ref('stg_olist__orders') }}
where order_status = 'delivered'
  and delivered_to_customer_at is null
