-- Singular data-quality test: an order marked 'delivered' should have an
-- actual delivery timestamp. The full Olist dataset contains a handful (~8) of
-- delivered orders missing this date — a known source-data quirk — so we warn
-- on any occurrence but only fail the build if it spikes past 20, which would
-- indicate a real upstream regression.
{{ config(error_if = '>20', warn_if = '>0') }}

select
    order_id,
    order_status,
    delivered_to_customer_at
from {{ ref('stg_olist__orders') }}
where order_status = 'delivered'
  and delivered_to_customer_at is null
