# -*- coding: utf-8 -*-
# Copyright 2013, Peter A. Bigot
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain a
# copy of the License at:
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
CoAP defines :coapsect:`a variety of options<5.10>` that affect
request and response semantics.  This module provides classes and
functions to operate on native Python instances of the options, and to
translate them between
the Python instances and their :coapsect:`encoded representation
within messages<3.1>`

:copyright: Copyright 2013, Peter A. Bigot
:license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
_log = logging.getLogger(__name__)


import coapy
import struct
import unicodedata


class OptionError (coapy.InfrastructureError):
    pass


class OptionRegistryConflictError (OptionError):
    """Exception raised when option numbers collide.

    CoAPy requires that each subclass of :py:class:`UrOption` has a
    unique option number, enforced by registering the
    subclass when its type is defined.  Attempts to use the same
    number for multiple options produce this exception.
    """
    pass


class InvalidOptionTypeError (OptionError):
    """Exception raised when an option is incorrectly defined.

    Each subclass of :py:class:`UrOption` must override
    :py:attr:`UrOption.number` with the integer option number,
    and :py:attr:`UrOption.format` with the type of the option.
    Failure to do so will cause this exception to be raised.
    """
    pass


class OptionLengthError (ValueError, OptionError):
    """Exception raised when a value's packed representation violates
    an option's length constraints, as determined by
    :attr:`UrOption.format`."""
    pass


class OptionDecodeError (OptionError):
    pass


class UnrecognizedCriticalOptionError (OptionError):
    pass


class InvalidOptionError (OptionError):
    """An option appears in a response or request when it must not."""
    pass


class InvalidMultipleOptionError (InvalidOptionError):
    """An option appears multiple times in a response or request when
    it must only appear once."""
    pass


class _format_base (object):
    """Abstract base for typed option value formatters.

    CoAP options encode values as byte sequences in one of several
    formats including:

    * :class:`format_empty` for no value
    * :class:`format_opaque` for uninterpreted byte sequences
    * :class:`format_uint` for variable-length unsigned integers
    * :class:`format_string` for Unicode text in Net-Unicode form
      (:rfc:`5198`).

    *max_length* is the maximum length of the packed representation in
    octets.  *min_length* is the minimum length of the packed
    representation in octets.
    """
    def _min_length(self):
        """The minimum acceptable length of the packed representation,
        in octets.  This is a read-only property."""
        return self.__min_length
    min_length = property(_min_length)

    def _max_length(self):
        """The maximum acceptable length of the packed representation,
        in octets.  This is a read-only property."""
        return self.__max_length
    max_length = property(_max_length)

    def _unpacked_type(self):
        """The Python type used for unpacked values.  This is a
        read-only property."""
        return self._UnpackedType
    unpacked_type = property(_unpacked_type)

    def __init__(self, max_length, min_length):
        self.__max_length = max_length
        self.__min_length = min_length

    def to_packed(self, value):
        """Convert *value* to packed form.

        If *value* is not an instance of :attr:`unpacked_type` then
        :exc:`TypeError<python:exceptions.typeError>` will be raised
        with *value* as an argument.

        The return value is a :class:`bytes` object with a length
        between :attr:`min_length` and :attr:`max_length`.  If *value*
        results in a packed format that is not within these bounds,
        :exc:`OptionLengthError` will be raised with *value* as
        an argument.
        """
        if not isinstance(value, self.unpacked_type):
            raise TypeError(value)
        pv = self._to_packed(value)
        if (len(pv) < self.min_length) or (self.max_length < len(pv)):
            raise OptionLengthError(value)
        return pv

    def _to_packed(self, value):
        """'Virtual' method implemented by subclasses to do
        type-specific packing.  The subclass implementation may assume
        *value* is of type :attr:`unpacked_type` and that the length
        constraints on the packed representation will be checked by
        :method:`to_packed`.
        """
        raise NotImplementedError

    def from_packed(self, packed):
        """Convert *packed* to its unpacked form.

        If *packed* is not an instance of :class:`bytes` then
        :exc:`TypeError<python:exceptions.TypeError>` will be raised
        with *packed* as an argument.

        If the length of *packed* is not between :attr:`min_length`
        and :attr:`max_length` (both inclusive) then
        :exc:`OptionLengthError` will be raised with *packed* as
        an argument.

        Otherwise the value is unpacked and a corresponding instance
        of :attr:`unpacked_type` is returned.
        """
        if not isinstance(packed, bytes):
            raise TypeError(packed)
        if (len(packed) < self.min_length) or (self.max_length < len(packed)):
            raise OptionLengthError(packed)
        return self._from_packed(packed)

    def _from_packed(self, value):
        """'Virtual' method implemented by subclasses to do
        type-specific unpacking.  The subclass implementation may
        assume *value* is of type :attr:`bytes` and that the length
        constraints on the packed representation have been checked.
        It must return an instance of :attr:`unpacked_type`.
        """
        raise NotImplementedError


class format_empty (_format_base):
    """Support options with no value.

    The only acceptable value is a zero-length byte string.  This is
    both the packed and unpacked value.
    """

    _UnpackedType = bytes

    def __init__(self):
        super(format_empty, self).__init__(0, 0)

    def _to_packed(self, value):
        return value

    def _from_packed(self, value):
        return value


class format_opaque (_format_base):
    """Support options with opaque values.

    Unpacked values are instances of :class:`bytes`, and packing and
    unpacking is an identity operation.
    """

    _UnpackedType = bytes

    def __init__(self, max_length, min_length=0):
        super(format_opaque, self).__init__(max_length, min_length)

    def _to_packed(self, value):
        return value

    def _from_packed(self, value):
        return value


class format_uint (_format_base):
    """Supports options with variable-length unsigned integer values.
    *max_length* is the maximum number of octets in the packed format.
    The implicit *min_length* is always zero.

    Unpacked values are instances of :class:`int`.  The packed value is
    big-endian in a :class:`bytes` string with all zero-valued leading
    bytes removed.  Thus the packed representation of zero is an empty
    string.

    Per the CoAP specification packed values with leading NUL bytes
    will decode correctly; however, they are still subject to
    validation against :attr:`max_length`.
    """

    _UnpackedType = int

    def __init__(self, max_length):
        super(format_uint, self).__init__(max_length, 0)

    def _to_packed(self, value):
        if 0 == value:
            return b''
        pv = bytearray(struct.pack(str('!Q'), value))
        for i in xrange(len(pv)):
            if pv[i] != 0:
                break
        return bytes(pv[i:])

    def _from_packed(self, data):
        value = 0
        data = bytearray(data)
        for i in xrange(len(data)):
            value = (value * 256) + data[i]
        return value

    def option_encoding(self, value):
        if not isinstance(value, int):
            raise TypeError(value)
        if (0 > value):
            raise ValueError(value)
        if value < 13:
            ov = value
            ovx = b''
        elif value < 269:
            ov = 13
            ovx = self.to_packed(value - 13)
            while len(ovx) < 1:
                ovx = b'\x00' + ovx
        else:
            ov = 14
            ovx = self.to_packed(value - 269)
            while len(ovx) < 2:
                ovx = b'\x00' + ovx
        return (ov, ovx)

    def option_decoding(self, ov, data):
        if 15 <= ov:
            raise ValueError(ov)
        if 14 == ov:
            return (269 + self.from_packed(data[:2]), data[2:])
        if 13 == ov:
            return (13 + self.from_packed(data[:1]), data[1:])
        return (ov, data)


class format_string (_format_base):
    """Supports options with text values.

    Unpacked values are Python Unicode (text) strings.  Packed values
    are :class:`bytes` in Net-Unicode form (:rfc:`5198`), a
    canonicalized ``utf-8`` encoding.  Note that, as usual, the
    *max_length* and *min_length* attributes apply to the packed
    representation, which for non-ASCII text may be longer than the
    unpacked representation.
    """

    _UnpackedType = unicode

    def __init__(self, max_length, min_length=0):
        super(format_string, self).__init__(max_length, min_length)

    def _to_packed(self, value):
        # At first blush, this is Net-Unicode.
        rv = unicodedata.normalize('NFC', value).encode('utf-8')
        return rv

    def _from_packed(self, value):
        rv = value.decode('utf-8')
        return rv


_OptionRegistry = {}


# Internal function used to register option classes as their
# definitions are processed by Python.
def _register_option(option_class):
    if not issubclass(option_class, UrOption):
        raise InvalidOptionTypeError(option_class)
    if not isinstance(option_class.number, int):
        raise InvalidOptionTypeError(option_class)
    if not ((0 <= option_class.number) and (option_class.number <= 65535)):
        raise InvalidOptionTypeError(option_class)
    if not isinstance(option_class.format, _format_base):
        raise InvalidOptionTypeError(option_class)
    if not (isinstance(option_class._repeatable, tuple)
            and (2 == len(option_class._repeatable))):
        raise InvalidOptionTypeError(option_class)
    for v in option_class._repeatable:
        if not ((v is None) or isinstance(v, bool)):
            raise InvalidOptionTypeError(option_class)
    if option_class.number in _OptionRegistry:
        raise OptionRegistryConflictError(option_class)
    _OptionRegistry[option_class.number] = option_class
    return option_class


def find_option(number):
    """Look up an option by number.

    Returns the :py:class:`UrOption` subclass registered for *number*,
    or ``None`` if no such option has been registered.  *number* must
    be an :class:`int` in the range 0 through 65535.
    """
    if not isinstance(number, int):
        raise TypeError(number)
    if not ((0 <= number) and (number <= 65535)):
        raise ValueError(number)
    return _OptionRegistry.get(number, None)


# Meta class used to enforce constraints on option types.  This serves
# several purposes:
#
# * It ensures that each subclass of UrOption properly provides both a
#   number and a format attribute;
#
# * It verifies that the values of these attributes are consistent with
#   the specification;
#
# * It rewrites the subclass so that those attributes are read-only in
#   both class and instance forms;
#
# * It registers each option class so that it can be looked up by
#   number.
#
# The concepts in this approach derive from:
# http://stackoverflow.com/questions/1735434/class-level-read-only-properties-in-python
#
# Note that coapy.util.ReadOnlyMeta does something similar but only to
# the class in which the attribute is introduced, while this works only
# on subclasses of UrOption.
class _MetaUrOption(type):

    # This class must do its work before UrOption has been added to
    # the module namespace.  Once that's been done this will be a
    # reference to it.
    __UrOption = None

    # The set of attributes in types that are to be made immutable if
    # the type provides a non-None value for the attribute.
    __ReadOnlyAttrs = ('number', '_repeatable', 'format')

    @classmethod
    def SetUrOption(cls, ur_option):
        cls.__UrOption = ur_option

    def __new__(cls, name, bases, namespace):
        # Provide a unique type that can hold the immutable class
        # number and format values.
        class UniqueUrOption (cls):
            pass

        do_register = (cls.__UrOption is not None) and namespace.get('_RegisterOption', True)

        # Only subclasses of UrOption have read-only attributes.  Make
        # those attributes immutable at both the class and instance
        # levels.
        if (cls.__UrOption is not None):
            for n in cls.__ReadOnlyAttrs:
                v = namespace.get(n, None)
                if (v is not None) and not isinstance(v, property):
                    mp = property(lambda self_or_cls, _v=v: _v)
                    namespace[n] = mp
                    setattr(UniqueUrOption, n, mp)

        # Create the subclass type, and register it if it's complete
        # (and not UrOption).
        mcls = type.__new__(UniqueUrOption, name, bases, namespace)
        if do_register:
            _register_option(mcls)

        return mcls


def is_critical_option(number):
    """Return ``True`` iff *number* identifies a critical option.

    A :coapsect:`critical option<5.4.1>` is one that must be
    understood by the endpoint processing the message.  This is
    indicated by bit 0 (0x01) of the *number* being set.
    """
    return number & 1


def is_unsafe_option(number):
    """Return ``True`` iff the option number identifies an unsafe option.

    An :coapsect:`unsafe option<5.4.2>` is one that must be recognized
    by a proxy in order to safely forward (or cache) the message.
    This is indicated by bit 1 (0x02) of the *number* being set."""
    return number & 2


def is_no_cache_key_option(number):
    """Return ``True`` iff the option number identifies a NoCacheKey option.

    A :coapsect:`NoCacheKey option<5.4.2>` is one for which the value
    of the option does not contribute to the key that identifies a
    matching value in a cache.  This is encoded in bits 1 through 5 of
    the *number*.  Options that are :func:`unsafe<is_unsafe_option>`
    are always NoCacheKey options.
    """
    return (0x1c == (number & 0x1e))


class UrOption (object):
    """Abstract base for CoAP options.

    If *unpacked_value* is not ``None``, :attr:`value` will be initialized
    with that value; otherwise if *packed_value* is not ``None``
    :attr:`value` will be initialized with the corresponding unpacked
    value; otherwise :attr:`value` will be ``None`` until a valid
    value is assigned.
    """

    __metaclass__ = _MetaUrOption

    number = None
    """The option number.

    An unsigned integer in the range 0..65535.  This is an
    IANA-registered value with the following policies
    (:rfc:`5226`):

    ============   ========
    Option Range   Policy
    ============   ========
        0..255     IETF Review or IESG Approval
      256..2047    Specification Required
     2048..64999   Designated Expert
    65000..65535   Reserved for experiments
    ============   ========

    The attribute is read-only.  Each subclass of :py:class:`UrOption`
    is registered during its definition.  :py:exc:`InvalidOptionType`
    will be raised if a previously-registered option exists with the
    same option number.
    """

    _repeatable = None
    """A tuple ``(request, response)`` indicating allowed
    cardinality of the option in requests and responses, respectively.

    The value of *request* and *response* is ``True`` if the option
    may appear multiple times in the corresponding message, ``False``
    if it must appear only once, and ``None`` if it may not appear at
    all.
    """

    format = None
    """An instance of :class:`format_empty`, :class:`format_opaque`,
    :class:`format_uint`, or :class:`format_string`.  The instance is
    used to check that the :attr:`value` is acceptable for the
    option."""

    def is_critical(self):
        """Passes ``self.number`` to :func:`is_critical_option`."""
        return is_critical_option(self.number)

    def is_unsafe(self):
        """Passes ``self.number`` to :func:`is_unsafe_option`."""
        return is_unsafe_option(self.number)

    def is_no_cache_key(self):
        """Passes ``self.number`` to :func:`is_no_cache_key_option`."""
        return is_no_cache_key_option(self.number)

    def valid_in_request(self):
        """Return ``True`` iff this option may appear at least once in a request message."""
        return self._repeatable[0] is not None

    def valid_multiple_in_request(self):
        """Return ``True`` iff this option may appear multiple times in a request message."""
        return self._repeatable[0] is True

    def valid_in_response(self):
        """Return ``True`` iff this option may appear at least once in a response message."""
        return self._repeatable[1] is not None

    def valid_multiple_in_response(self):
        """Return ``True`` iff this option may appear multiple times in a response message."""
        return self._repeatable[1] is True

    def __init__(self, unpacked_value=None, packed_value=None):
        super(UrOption, self).__init__()
        if unpacked_value is not None:
            self._set_value(unpacked_value)
        elif packed_value is not None:
            self.__value = self.format.from_packed(packed_value)
        else:
            self.__value = None

    def _set_value(self, unpacked_value):
        self.__value = self.format.from_packed(self.format.to_packed(unpacked_value))

    def _get_value(self):
        return self.__value

    value = property(_get_value, _set_value, None,
                     """Contains the value of the option.  This is an
                     instance of
                     :attr:`format.unpacked_type<_format_base.unpacked_type>`.
                     Only values that pass the restrictions of
                     :attr:`format` may be assigned to this property.
                     Unacceptable values result in
                     :exc:`TypeError<python:exceptions.TypeError>`
                     or :exc:`OptionLengthError`.""")

    @property
    def packed_value(self):
        """The :attr:`value` of the option in its packed representation."""
        return self.format.to_packed(self.value)


# Register the UrOption so subclasses can
_MetaUrOption.SetUrOption(UrOption)

# A utility instance used to encode and decode variable-length
# integers in options, which comprise a 4-bit code with zero to two
# bytes of offset.
_optionint_helper = format_uint(2)


def sorted_options(options):
    """Sort a sequence of options into canonical order.

    Return a list with the same elements as *options* sorted using the option
    :attr:`number<UrOption.number>` as the key.  The sort is stable:
    options with the same number remain in their original order.  This
    operation is used for duplicate detection and to calculate the
    delta required to encode options."""
    return sorted(options, key=lambda _o: _o.number)


def replace_unacceptable_options(options, is_request):
    """Verify that a set of options passes CoAP requirements.

    Individual options have occurrence restrictions that are encoded
    within the options themselves and may be inspected by these
    methods:

        * :meth:`coapy.option.UrOption.valid_in_request`
        * :meth:`coapy.option.UrOption.valid_in_response`
        * :meth:`coapy.option.UrOption.valid_multiple_in_request`
        * :meth:`coapy.option.UrOption.valid_multiple_in_response`

    :coapsect:`5.4.5` specifies that options violating these
    constraints are to be interpreted as :class:`unrecognized
    options<UnrecognizedOption>`.  These are subsequently used to
    check for :coapsect:`critical<5.4.1>` or :coapsect:`unsafe<5.7>`
    options.

    This method replaces individual recognized options in
    :attr:`options` with an equivalent unrecognized option instance
    based on *is_request* and each option's restrictions.  The
    resulting list of options is returned.
    """
    newopts = []
    if is_request:
        valid = lambda _o: _o.valid_in_request()
        valid_multiple = lambda _o: _o.valid_multiple_in_request()
    else:
        valid = lambda _o: _o.valid_in_response()
        valid_multiple = lambda _o: _o.valid_multiple_in_response()
    last_number = 0
    for opt in sorted_options(options):
        delta = opt.number - last_number
        last_number = opt.number
        if not valid(opt):
            newopts.append(UnrecognizedOption.from_option(opt))
        elif (0 == delta) and not valid_multiple(opt):
            newopts.append(UnrecognizedOption.from_option(opt))
        else:
            newopts.append(opt)
    return newopts


def encode_options(options):
    """Encode a set of options into packed form.

    This returns a :class:`bytes` object that represents the encoding
    of *options* after they have been :func:`sorted<sorted_options>`.
    It may raise an exception if an option's value cannot be encoded,
    but performs no semantic
    validation."""
    last_number = 0
    packed = []
    for opt in sorted_options(options):
        delta = opt.number - last_number
        last_number = opt.number
        pvalue = opt.packed_value
        (od, odx) = _optionint_helper.option_encoding(delta)
        (ol, olx) = _optionint_helper.option_encoding(len(pvalue))
        encoded = struct.pack(str('B'), (od << 4) | ol)
        encoded += odx + olx + pvalue
        packed.append(encoded)
    return b''.join(packed)


def _decode_one_option(data):
    if 0xFF == data[0]:
        return (None, None, data)
    odl = data.pop(0)
    od = (odl >> 4)
    ol = (odl & 0x0F)
    if (15 == od) or (15 == ol):
        raise OptionDecodeError(odl, bytes(data))
    (delta, data) = _optionint_helper.option_decoding(od, data)
    (length, data) = _optionint_helper.option_decoding(ol, data)
    return (delta, length, data)


def decode_options(data):
    """Extract a list of options from the packed *data* which is :class:`bytes`.

    Returns ``(options, remaining_data)`` where *options* is a list of
    instances of subclasses of :class:`UrOption`.  Options that are
    unknown to the infrastructure will be returned as instances of
    :class:`UnrecognizedOption`.  *remaining_data* will be the suffix of
    *data* that was not consumed when unpacking the options.

    This will raise :exc:`OptionDecodeError` or other exceptions if
    the option data is malformed, but does no semantic validation"""
    idx = 0
    option_number = 0
    options = []
    data = bytearray(data)      # avoid 2to3 ord/chr issues
    while 0 < len(data):
        (delta, length, data) = _decode_one_option(data)
        if delta is None:
            break
        option_number += delta
        option_type = find_option(option_number)
        packed = bytes(data[:length])
        data = data[length:]
        opt = None
        if option_type is not None:
            try:
                opt = option_type(packed_value=packed)
            except OptionLengthError:
                pass
        if opt is None:
            opt = UnrecognizedOption(option_number, packed_value=packed)
        options.append(opt)
    if 0 == len(options):
        options = None
    return (options, bytes(data))


class UnrecognizedOption (UrOption):
    """Contains an option for which the registered :class:`UrOption`
    subclass is not available or may not be used.

    *number* must be provided, must be in the range 0 through 65535.
    *unpacked_value* and *packed_value* operate as in
    :class:`UrOption` and accept only :class:`bytes` objects.

    :class:`UnrecognizedOption` instances are structurally accepted in
    both request and response messages and instances with the same
    :attr:`number` may appear multiple times in each.  Semantic
    restrictions may apply based on :meth:`UrOption.is_critical`.

    .. note::

       :coapsect:`5.4` specifies situations where an option must be
       treated as an unrecognized option even if its number matches a
       recognized option.
    """

    _RegisterOption = False
    _repeatable = (True, True)
    format = format_opaque(1034)
    """Unknown options carry their payload as uninterpreted
    :class:`bytes` objects with a maximum length of 1034 octets."""

    def _get_number(self):
        """The :attr:`option number<UrOption.number>` associated with
        this option.  This is a read-only attribute."""
        return self.__number
    number = property(_get_number)

    def __init__(self, number, unpacked_value=None, packed_value=None):
        if not isinstance(number, int):
            raise TypeError(number)
        if (0 > number) or (65535 < number):
            raise ValueError(number)
        self.__number = number
        super(UnrecognizedOption, self).__init__(unpacked_value=unpacked_value,
                                                 packed_value=packed_value)

    @classmethod
    def from_option(cls, opt):
        """Create an :class:`UnrecognizedOption` from an existing (recognized) option.

        This conversion is necessary per :coapsect:`5.4` in various
        instances where the recognized option is not accepted.
        Standard option processing then proceeds with the option left
        unrecognized."""
        return cls(opt.number, opt.packed_value)


class IfMatch (UrOption):
    """Option used to make requests conditional on an :class:`ETag`
    match.  See :coapsect:`5.10.8.1`.
    """
    number = 1
    _repeatable = (True, None)
    format = format_opaque(8)


class UriHost (UrOption):
    """Option encoding the Internet host of a requested resource.  See
    :coapsect:`5.10.1`.
    """
    number = 3
    _repeatable = (False, None)
    format = format_string(255, min_length=1)


class ETag (UrOption):
    """Option used for a resource-local short-hand for a given
    representation of a resource.  See :coapsect:`5.10.6`.
    """
    number = 4
    _repeatable = (True, False)
    format = format_opaque(8, min_length=1)


class IfNoneMatch (UrOption):
    """Option used to make requests conditional absence of a resource.
    See :coapsect:`5.10.8.2`.
    """
    number = 5
    _repeatable = (False, None)
    format = format_empty()

    def __init__(self, unpacked_value=None, packed_value=None):
        if (unpacked_value is None) and (packed_value is None):
            unpacked_value = b''
        super(IfNoneMatch, self).__init__(unpacked_value=unpacked_value,
                                          packed_value=packed_value)


class UriPort (UrOption):
    """Option encoding the transport-layer port of a requested
    resource.  See :coapsect:`5.10.1`.
    """
    number = 7
    _repeatable = (False, None)
    format = format_uint(2)


class LocationPath (UrOption):
    """Option encoding (a segment of) the path of a resource
    identified in a response.  This option may occur multiple times.
    See :coapsect:`5.10.7`.
    """
    number = 8
    _repeatable = (None, True)
    format = format_string(255)


class UriPath (UrOption):
    """Option encoding (a segment of) the path of a requested
    resource.  This option may occur multiple times.  See
    :coapsect:`5.10.1`.
    """
    number = 11
    _repeatable = (True, None)
    format = format_string(255)


class ContentFormat (UrOption):
    """Option encoding the representation format of the message
    payload.  See :coapsect:`5.10.3`.
    """
    number = 12
    _repeatable = (False, False)
    format = format_uint(2)


class MaxAge (UrOption):
    """Option encoding the maximum time (in seconds) that a response
    may be cached before it is outdated.  See :coapsect:`5.10.5`.
    """
    number = 14
    _repeatable = (None, False)
    format = format_uint(4)


class UriQuery (UrOption):
    """Option encoding (an element of) the query part of a requested
    resource.  This option may occur multiple times.  See
    :coapsect:`5.10.1`.
    """
    number = 15
    _repeatable = (True, None)
    format = format_string(255)


class Accept (UrOption):
    """Option encoding the representation format acceptable to a
    client.  See :coapsect:`5.10.4`.
    """
    number = 17
    _repeatable = (False, None)
    format = format_uint(2)


class LocationQuery (UrOption):
    """Option encoding (an element of) the query part of a resource
    identified in a response.  This option may occur multiple times.
    See :coapsect:`5.10.7`.
    """
    number = 20
    _repeatable = (None, True)
    format = format_string(255)


class ProxyUri (UrOption):
    """Option encoding the URI of a request directed through a
    :coapsect:`forward-proxy<5.7>`. See :coapsect:`5.10.2`.

    If this option appears in a request, none of :class:`UriHost`,
    :class:`UriPort`, :class:`UriPath`, or :class:`UriQuery` may
    appear.
    """
    number = 35
    _repeatable = (False, None)
    format = format_string(1034, min_length=1)


class ProxyScheme (UrOption):
    """Option encoding the schema for a URI of a request directed
    through a :coapsect:`forward-proxy<5.7>`.  In this case the
    remainder of the URI is constructed from :class:`UriHost`,
    :class:`UriPort`, :class:`UriPath`, or :class:`UriQuery` options.
    See :coapsect:`5.10.2`.
    """
    number = 39
    _repeatable = (False, None)
    format = format_string(255, min_length=1)


class Size1 (UrOption):
    """Option providing size (in bytes) of a resource representation
    in a request.  It may appear in an informational role in a
    diagnostic response.  See :coapsect:`5.10.9`.
    """
    number = 60
    _repeatable = (False, False)
    format = format_uint(4)
