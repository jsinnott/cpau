Exceptions
==========

.. automodule:: cpau.exceptions
   :members:
   :undoc-members:
   :show-inheritance:

Exception Hierarchy
-------------------

All CPAU-specific exceptions inherit from :class:`CpauError`:

.. code-block:: text

   CpauError
   ├── CpauAuthenticationError
   ├── CpauConnectionError
   ├── CpauApiError
   └── CpauMeterNotFoundError

Exception Classes
-----------------

CpauError
~~~~~~~~~

.. autoexception:: cpau.exceptions.CpauError
   :members:
   :show-inheritance:

   Base exception for all CPAU-related errors.

CpauAuthenticationError
~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: cpau.exceptions.CpauAuthenticationError
   :members:
   :show-inheritance:

   Raised when authentication with CPAU portal fails.

   Common causes:

   * Invalid credentials
   * Account locked due to too many failed login attempts
   * CPAU portal is down or unavailable

CpauConnectionError
~~~~~~~~~~~~~~~~~~~

.. autoexception:: cpau.exceptions.CpauConnectionError
   :members:
   :show-inheritance:

   Raised when unable to connect to CPAU portal.

   Common causes:

   * Network connectivity issues
   * CPAU portal is down
   * Firewall blocking connection

CpauApiError
~~~~~~~~~~~~

.. autoexception:: cpau.exceptions.CpauApiError
   :members:
   :show-inheritance:

   Raised when API request fails or returns unexpected data.

   Common causes:

   * Invalid date range
   * Invalid interval type
   * CPAU API changed (breaking change)
   * Data not available for requested period

CpauMeterNotFoundError
~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: cpau.exceptions.CpauMeterNotFoundError
   :members:
   :show-inheritance:

   Raised when no meter is found for the account.

   Common causes:

   * New account with no meter assigned yet
   * Account has access to multiple meters (not yet supported)

Example Usage
-------------

.. code-block:: python

   from cpau import CpauApiSession
   from cpau.exceptions import (
       CpauAuthenticationError,
       CpauConnectionError,
       CpauApiError
   )
   from datetime import date

   try:
       with CpauApiSession(userid='user@example.com', password='wrong') as session:
           meter = session.get_electric_meter()
           data = meter.get_usage('daily', date(2024, 12, 1))

   except CpauAuthenticationError as e:
       print(f"Login failed: {e}")
       print("Check your credentials in secrets.json")

   except CpauConnectionError as e:
       print(f"Connection failed: {e}")
       print("Check your network connection")

   except CpauApiError as e:
       print(f"API error: {e}")
       print("The CPAU portal may have changed or be unavailable")
