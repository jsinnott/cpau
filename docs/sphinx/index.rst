CPAU - City of Palo Alto Utilities Data Access
==============================================

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License: MIT

.. image:: https://img.shields.io/badge/python-3.8+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.8+

A Python library and CLI tools for downloading electric and water meter data from the City of Palo Alto Utilities (CPAU) customer portal.

Overview
--------

This library provides programmatic access to your historical electricity and water usage data from CPAU's customer portals:

* **Electric meter data**: From the `CPAU customer portal <https://mycpau.cityofpaloalto.org/Portal/Usages.aspx>`_
* **Water meter data**: From the `WaterSmart portal <https://paloalto.watersmart.com>`_

Since CPAU doesn't provide a public API, this library reverse-engineers the web portals' internal APIs to retrieve your data programmatically.

Features
--------

✅ **Python Library**: Clean, pythonic API for accessing CPAU data in your applications

✅ **CLI Tools**: Command-line interfaces for electric (``cpau-electric``) and water (``cpau-water``) data

✅ **Multiple Intervals**: Billing periods, monthly, daily, hourly, and 15-minute data

✅ **CSV Output**: Standard CSV format for easy data analysis

✅ **Type Hints**: Full type annotations for better IDE support

✅ **Cookie Caching**: Fast authentication (~1s) for repeated water meter queries

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install cpau

   # For water meter support, install Playwright browser
   playwright install chromium

Set Up Credentials
~~~~~~~~~~~~~~~~~~

Create a ``secrets.json`` file with your CPAU login credentials:

.. code-block:: json

   {
       "userid": "your_email@example.com",
       "password": "your_password"
   }

⚠️ **Important**: Never commit this file to version control.

CLI Usage
~~~~~~~~~

.. code-block:: bash

   # Electric meter - get daily usage
   cpau-electric --interval daily 2024-12-01 2024-12-31 > electric_daily.csv

   # Water meter - get hourly usage
   cpau-water --interval hourly 2024-12-01 2024-12-31 > water_hourly.csv

Library Usage
~~~~~~~~~~~~~

.. code-block:: python

   from cpau import CpauApiSession
   from datetime import date

   # Electric meter
   with CpauApiSession(userid='your_email', password='your_password') as session:
       meter = session.get_electric_meter()
       data = meter.get_usage(
           interval='daily',
           start_date=date(2024, 12, 1),
           end_date=date(2024, 12, 31)
       )

       for record in data:
           print(f"{record.date}: {record.net_kwh} kWh")

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   cli_usage
   library_usage

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/session
   api/electric_meter
   api/water_meter
   api/exceptions

.. toctree::
   :maxdepth: 1
   :caption: Additional Information

   performance
   troubleshooting
   how_it_works
   contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
