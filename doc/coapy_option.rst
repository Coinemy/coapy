.. coapy_option:

coapy.option
============

.. automodule:: coapy.option
   :no-members:

Operations on Options
---------------------

.. autofunction:: find_option
.. autofunction:: is_critical_option
.. autofunction:: is_unsafe_option
.. autofunction:: is_no_cache_key_option
.. autofunction:: encode_options
.. autofunction:: decode_options
.. autofunction:: replace_unacceptable_options
.. autofunction:: sorted_options

Option Classes
--------------

.. autoclass:: UrOption
   :no-show-inheritance:

.. autoclass:: UnrecognizedOption

Base CoAP Options
^^^^^^^^^^^^^^^^^

The following table shows all options that are defined in base CoAP.
Additional options are defined in protocol extensions.

.. autosummary::
   :nosignatures:

   UriHost
   UriPort
   UriPath
   UriQuery
   ProxyUri
   ProxyScheme
   ContentFormat
   Accept
   MaxAge
   ETag
   LocationPath
   LocationQuery
   IfMatch
   IfNoneMatch
   Size1

.. autoclass:: UriHost
.. autoclass:: UriPort
.. autoclass:: UriPath
.. autoclass:: UriQuery
.. autoclass:: ProxyUri
.. autoclass:: ProxyScheme
.. autoclass:: ContentFormat
.. autoclass:: Accept
.. autoclass:: MaxAge
.. autoclass:: ETag
.. autoclass:: LocationPath
.. autoclass:: LocationQuery
.. autoclass:: IfMatch
.. autoclass:: IfNoneMatch
.. autoclass:: Size1

Option Formatter Classes
------------------------

When encoded option values are packed in space efficient ways depending on
the :coapsect:`format of the option value<3.2>`.

.. autoclass:: _format_base
   :no-show-inheritance:
.. autoclass:: format_empty
.. autoclass:: format_opaque
.. autoclass:: format_uint
.. autoclass:: format_string

Option-Related Exceptions
-------------------------

.. autoexception:: OptionError
.. autoexception:: OptionRegistryConflictError
.. autoexception:: InvalidOptionTypeError
.. autoexception:: OptionLengthError
.. autoexception:: OptionDecodeError
.. autoexception:: UnrecognizedCriticalOptionError
.. autoexception:: InvalidOptionError
.. autoexception:: InvalidMultipleOptionError
