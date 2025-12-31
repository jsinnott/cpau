Electric Meter
==============

.. automodule:: cpau.electric_meter
   :members:
   :undoc-members:
   :show-inheritance:

CpauElectricMeter
-----------------

.. autoclass:: cpau.electric_meter.CpauElectricMeter
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

   .. rubric:: Supported Intervals

   * ``billing`` - Billing period data (CPAU's billing periods)
   * ``monthly`` - Calendar month aggregation (sum of daily data by month)
   * ``daily`` - Daily aggregated usage
   * ``hourly`` - Hourly usage data
   * ``15min`` - 15-minute interval usage data

   .. rubric:: Example

   .. code-block:: python

      from cpau import CpauApiSession
      from datetime import date

      with CpauApiSession(userid='user@example.com', password='password') as session:
          meter = session.get_electric_meter()

          # Get daily usage data
          records = meter.get_usage(
              interval='daily',
              start_date=date(2024, 12, 1),
              end_date=date(2024, 12, 31)
          )

          # Process records
          for record in records:
              print(f"{record.date}: {record.net_kwh} kWh")

          # Check data availability
          earliest, latest = meter.get_availability_window('daily')
          print(f"Data available from {earliest} to {latest}")

UsageRecord
-----------

.. autoclass:: cpau.meter.UsageRecord
   :members:
   :undoc-members:

   .. rubric:: Fields

   * **date** (date or datetime): Timestamp for this record
   * **export_kwh** (float): Solar generation sent to grid (for NEM 2.0 customers)
   * **import_kwh** (float): Electricity consumed from grid
   * **net_kwh** (float): Import - Export (positive = net consumption)
   * **billing_period_start** (str, optional): Start of billing period (billing interval only)
   * **billing_period_end** (str, optional): End of billing period (billing interval only)
   * **billing_period_length** (int, optional): Days in billing period (billing interval only)
