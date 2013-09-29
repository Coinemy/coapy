.. api:

*****************
API Documentation
*****************

.. module:: coapy.option

Option-Related Exceptions
=========================

.. autoexception:: OptionError
.. autoexception:: OptionRegistryConflictError
.. autoexception:: InvalidOptionTypeError
.. autoexception:: OptionLengthError
.. autoexception:: OptionDecodeError
.. autoexception:: UnrecognizedCriticalOptionError
.. autoexception:: InvalidOptionError
.. autoexception:: InvalidRequestOptionError
.. autoexception:: InvalidResponseOptionError


Option Formatting
=================

.. autoclass:: _format_base
   :no-show-inheritance:
.. autoclass:: format_empty
.. autoclass:: format_opaque
.. autoclass:: format_uint
.. autoclass:: format_string

Options
=======

.. autofunction:: find_option
.. autofunction:: is_critical_option
.. autofunction:: is_unsafe_option
.. autofunction:: is_no_cache_key_option

.. autoclass:: UrOption
   :no-show-inheritance:

.. autoclass:: UnknownOption

Pre-Defined Options
-------------------

.. autosummary::
   :nosignatures:

   IfMatch
   UriHost
   ETag
   IfNoneMatch
   UriPort
   LocationPath
   UriPath
   ContentFormat
   MaxAge
   UriQuery
   Accept
   LocationQuery
   ProxyUri
   ProxyScheme
   Size1

.. autoclass:: IfMatch
.. autoclass:: UriHost
.. autoclass:: ETag
.. autoclass:: IfNoneMatch
.. autoclass:: UriPort
.. autoclass:: LocationPath
.. autoclass:: UriPath
.. autoclass:: ContentFormat
.. autoclass:: MaxAge
.. autoclass:: UriQuery
.. autoclass:: Accept
.. autoclass:: LocationQuery
.. autoclass:: ProxyUri
.. autoclass:: ProxyScheme
.. autoclass:: Size1
