Session Management
==================

.. automodule:: cpau.session
   :members:
   :undoc-members:
   :show-inheritance:

CpauApiSession
--------------

.. autoclass:: cpau.session.CpauApiSession
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __enter__, __exit__

   .. rubric:: Example

   .. code-block:: python

      from cpau import CpauApiSession

      # Use as context manager for automatic cleanup
      with CpauApiSession(userid='user@example.com', password='password') as session:
          meter = session.get_electric_meter()
          # Session automatically closed when exiting context

      # Or manage manually
      session = CpauApiSession(userid='user@example.com', password='password')
      try:
          meter = session.get_electric_meter()
          # ... use meter ...
      finally:
          session.close()
