.. coapy_message:

coapy.message
=============

.. automodule:: coapy.message
   :no-members:

Messages
--------

The following message types are available:

.. autosummary::
   :nosignatures:

   Request
   SuccessResponse
   ClientErrorResponse
   ServerErrorResponse

.. autoclass:: Message
   :no-show-inheritance:

.. autoclass:: Request
.. autoclass:: Response
.. autoclass:: SuccessResponse
.. autoclass:: ClientErrorResponse
.. autoclass:: ServerErrorResponse

Message Caches
--------------

.. autoclass:: MessageIDCacheEntry
.. autoclass:: MessageIDCache

Utility Classes
---------------

.. autoclass:: TransmissionParameters
   :no-show-inheritance:

.. autoclass:: RetransmissionState
   :no-show-inheritance:

Message-Related Exceptions
--------------------------

.. autoexception:: MessageError
.. autoexception:: MessageFormatError
.. autoexception:: MessageValidationError
.. autoexception:: MessageReplyError
