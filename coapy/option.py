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
    ************
    coapy.option
    ************

    :copyright: Copyright 2013, Peter A. Bigot
    :license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


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


class OptionValueLengthError (OptionError):
    pass

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
    if not isinstance(option_class.format, UrOption._OptionFormat):
        raise InvalidOptionTypeError(option_class)
    if option_class.number in _OptionRegistry:
        raise OptionRegistryConflictError(option_class)
    _OptionRegistry[option_class.number] = option_class
    return option_class


def find_option(number):
    """Look up an option by number.

    Returns the :py:class:`UrOption` subclass registered for *number*,
    or ``None`` if no such option has been registered.
    """
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
class _MetaUrOption(type):

    # This class must do its work before UrOption has been added to
    # the module namespace.  Once that's been done this will be a
    # reference to it.
    __UrOption = None

    # The set of attributes in types that are to be made immutable if
    # the type provides a non-None value for the attribute.
    __ReadOnlyAttrs = ('number', 'repeatable', 'format')

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


class UrOption (object):
    """Abstract base for CoAP options.

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
    is registered during its definition; :py:exc:`InvalidOptionType`
    will be raised if multiple options with the same number are
    defined.
    """

    repeatable = None
    """A tuple ``(request, response)`` indicating allowed
    cardinality of the option in requests and responses, respectively.

    The value of *request* and *response* is ``True`` if the option
    may appear multiple times in the corresponding message, ``False``
    if it must appear only once, and ``None`` if it may not appear at
    all.
    """

    format = None

    class _OptionFormat (object):
        def _min_length(self):
            return self.__min_length
        min_length = property(_min_length)

        def _max_length(self):
            return self.__max_length
        max_length = property(_max_length)

        def __init__(self, max_length, min_length):
            self.__max_length = max_length
            self.__min_length = min_length

        def to_packed(self, value):
            if value is None:
                raise ValueError(value)
            pv = self._to_packed(value)
            if (len(pv) < self.min_length) or (self.max_length < len(pv)):
                raise OptionValueLengthError(value)
            return pv

        def from_packed(self, packed):
            if not isinstance(packed, bytes):
                raise ValueError(packed)
            if (len(packed) < self.min_length) or (self.max_length < len(packed)):
                raise OptionValueLengthError(packed)
            return self._from_packed(packed)

    class empty (_OptionFormat):
        def __init__(self):
            super(UrOption.empty, self).__init__(0, 0)

        def to_packed(self, value):
            if value is not None:
                raise ValueError(value)
            return b''

        def from_packed(self, packed):
            if packed != b'':
                raise ValueError(packed)
            return None

    class opaque (_OptionFormat):
        def __init__(self, max_length, min_length=0):
            super(UrOption.opaque, self).__init__(max_length, min_length)

        def _to_packed(self, value):
            if not isinstance(value, bytes):
                raise ValueError(value)
            return value

        def _from_packed(self, value):
            if not isinstance(value, bytes):
                raise ValueError(value)
            return value

        def convert_value(self, value):
            if value is not None:
                value = bytes(value)
            return value

    class uint (_OptionFormat):
        def __init__(self, max_length, min_length=0):
            super(UrOption.uint, self).__init__(max_length, min_length)

        def _to_packed(self, value):
            if not isinstance(value, int):
                raise ValueError(value)
            if 0 == value:
                return b''
            pv = struct.pack(str('!Q'), value)
            for i in xrange(len(pv)):
                if ord(pv[i]) != 0:
                    break
            return pv[i:]

        def _from_packed(self, data):
            if not isinstance(data, bytes):
                raise ValueError(value)
            value = 0
            for i in xrange(len(data)):
                value = (value * 256) + ord(data[i])
            return value

    class string (_OptionFormat):
        def __init__(self, max_length, min_length=0):
            super(UrOption.string, self).__init__(max_length, min_length)

        def _to_packed(self, value):
            if not isinstance(value, unicode):
                raise ValueError(value)
            rv = unicodedata.normalize('NFC', value).encode('utf-8')
            return rv

        def _from_packed(self, value):
            if not isinstance(value, bytes):
                raise ValueError(value)
            rv = value.decode('utf-8')
            return rv

    def is_critical(self):
        return (self.number & 1)

    def is_unsafe(self):
        return (self.number & 2)

    def is_no_cache_key(self):
        return (0x1c == (self.number & 0x1e))

    def valid_in_request(self):
        return self.repeatable[0] is not None

    def valid_multiple_in_request(self):
        return self.repeatable[0] is True

    def valid_in_response(self):
        return self.repeatable[1] is not None

    def valid_multiple_in_response(self):
        return self.repeatable[1] is True

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

    value = property(_get_value, _set_value)

# Register the UrOption so subclasses can
_MetaUrOption.SetUrOption(UrOption)


class UnknownOption (UrOption):
    _RegisterOption = False
    repeatable = (True, True)
    format = UrOption.opaque(1034)

    def _get_number(self):
        return self.__number
    number = property(_get_number)

    def __init__(self, number, unpacked_value=None, packed_value=None):
        if not (isinstance(number, int) and (0 <= number) and (number <= 65535)):
            raise ValueError('invalid option number')
        option = find_option(number)
        if option is not None:
            raise ValueError('conflicting option number', option)
        self.__number = number
        super(UnknownOption, self).__init__(unpacked_value=unpacked_value,
                                            packed_value=packed_value)


class IfMatch (UrOption):
    number = 1
    repeatable = (True, None)
    format = UrOption.opaque(8)


class UriHost (UrOption):
    number = 3
    repeatable = (False, None)
    format = UrOption.string(255, min_length=1)


class ETag (UrOption):
    number = 4
    repeatable = (True, False)
    format = UrOption.opaque(8, min_length=1)


class IfNoneMatch (UrOption):
    number = 5
    repeatable = (False, None)
    format = UrOption.empty()


class UriPort (UrOption):
    number = 7
    repeatable = (False, None)
    format = UrOption.uint(2)


class LocationPath (UrOption):
    number = 8
    repeatable = (None, True)
    format = UrOption.string(255)


class UriPath (UrOption):
    number = 11
    repeatable = (True, None)
    format = UrOption.string(255)


class ContentFormat (UrOption):
    number = 12
    repeatable = (False, False)
    format = UrOption.uint(2)


class MaxAge (UrOption):
    number = 14
    repeatable = (None, False)
    format = UrOption.uint(4)


class UriQuery (UrOption):
    number = 15
    repeatable = (True, None)
    format = UrOption.string(255)


class Accept (UrOption):
    number = 17
    repeatable = (False, None)
    format = UrOption.uint(2)


class LocationQuery (UrOption):
    number = 20
    repeatable = (None, True)
    format = UrOption.string(255)


class ProxyUri (UrOption):
    number = 35
    repeatable = (False, None)
    format = UrOption.string(1034, min_length=1)


class ProxyScheme (UrOption):
    number = 39
    repeatable = (False, None)
    format = UrOption.string(255, min_length=1)


class Size1 (UrOption):
    number = 60
    repeatable = (False, False)
    format = UrOption.uint(4)
