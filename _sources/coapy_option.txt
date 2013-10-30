.. coapy_option:

coapy.option
============

.. automodule:: coapy.option
   :no-members:

Operations
----------

.. autofunction:: all_options
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

The following table shows all options that are defined in base CoAP, along
with the format and the :attr:`maximum length of the packed
value<_format_base.max_length>` (and the minimum length if not zero).

   =======  ========================  =======================  =================
   Option   Class                     Format                   Max (min) Length
   =======  ========================  =======================  =================
   1        :class:`IfMatch`          :class:`format_opaque`   8
   3        :class:`UriHost`          :class:`format_string`   255 (1)
   4        :class:`ETag`             :class:`format_opaque`   8 (1)
   5        :class:`IfNoneMatch`      :class:`format_empty`
   7        :class:`UriPort`          :class:`format_uint`     2
   8        :class:`LocationPath`     :class:`format_string`   255
   11       :class:`UriPath`          :class:`format_string`   255
   12       :class:`ContentFormat`    :class:`format_uint`     2
   14       :class:`MaxAge`           :class:`format_uint`     4
   15       :class:`UriQuery`         :class:`format_string`   255
   17       :class:`Accept`           :class:`format_uint`     2
   20       :class:`LocationQuery`    :class:`format_string`   255
   35       :class:`ProxyUri`         :class:`format_string`   1034 (1)
   39       :class:`ProxyScheme`      :class:`format_string`   255 (1)
   60       :class:`Size1`            :class:`format_uint`     4
   =======  ========================  =======================  =================

Additional options are defined in protocol extensions.


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
