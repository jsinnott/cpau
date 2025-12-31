Water Meter
===========

.. automodule:: cpau.water_meter
   :members:
   :undoc-members:
   :show-inheritance:

CpauWaterMeter
--------------

.. autoclass:: cpau.water_meter.CpauWaterMeter
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:

   .. rubric:: Supported Intervals

   * ``billing`` - Billing period data
   * ``monthly`` - Monthly aggregated usage
   * ``daily`` - Daily usage data
   * ``hourly`` - Hourly usage data

   .. rubric:: Authentication

   Water meter authentication uses Playwright for SAML/SSO flow:

   * First authentication: ~15 seconds (Playwright/SAML)
   * Cached authentication: ~1 second (10-minute cache window)
   * Cache location: ``~/.cpau/watersmart_cookies.json`` (default)

   .. rubric:: Example

   .. code-block:: python

      from cpau import CpauWaterMeter
      from datetime import date

      # Create water meter (handles SAML/SSO authentication automatically)
      meter = CpauWaterMeter(
          username='user@example.com',
          password='password',
          cache_dir='~/.cpau'  # Optional: cache cookies for fast re-auth
      )

      # Get usage data
      records = meter.get_usage(
          interval='daily',
          start_date=date(2024, 12, 1),
          end_date=date(2024, 12, 31)
      )

      # Water usage is in the import_kwh field (gallons, not kWh)
      for record in records:
          print(f"{record.date}: {record.import_kwh} gallons")

      # Check data availability
      earliest, latest = meter.get_availability_window('daily')
      print(f"Water data available from {earliest} to {latest}")

   .. note::
      Water meter data is stored in the ``import_kwh`` field of UsageRecord,
      but contains gallons instead of kWh. The ``export_kwh`` and ``net_kwh``
      fields are always 0.0 for water meters.

WatersmartSessionManager
-------------------------

.. automodule:: cpau.watersmart_session
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: cpau.watersmart_session.WatersmartSessionManager
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

   Low-level session manager for WaterSmart portal authentication.
   Most users should use :class:`CpauWaterMeter` instead.
