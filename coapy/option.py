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


class OptionRegistryConflict (coapy.InfrastructureError):
    """Exception raised when option numbers collide.

    CoAPy requires that each subclass of :py:class:`UrOption` has a
    unique option number, enforced by registering the
    subclass when its type is defined.  Attempts to use the same
    number for multiple options produce this exception.
    """
    pass


class InvalidOptionType (coapy.InfrastructureError):
    """Exception raised when an option is incorrectly defined.

    Each subclass of :py:class:`UrOption` must override
    :py:attr:`UrOption.number` with the integer option number,
    and :py:attr:`UrOption.format` with the type of the option.
    Failure to do so will cause this exception to be raised.
    """
    pass


_OptionRegistry = {}


# Internal function used to register option classes as their
# definitions are processed by Python.
def _register_option(option_class):
    if not issubclass(option_class, UrOption):
        raise InvalidOptionType(option_class)
    if not isinstance(option_class.number, int):
        raise InvalidOptionType(option_class)
    if not ((0 <= option_class.number) and (option_class.number <= 65535)):
        raise InvalidOptionType(option_class)
    if not (option_class.format in (UrOption.empty, UrOption.opaque, UrOption.uint, UrOption.string)):
        raise InvalidOptionType(option_class)
    if option_class.number in _OptionRegistry:
        raise OptionRegistryConflict(option_class)
    _OptionRegistry[option_class.number] = option_class
    return option_class


def find_option(number):
    """Look up an option by number.

    Returns the subclass of :py:class:`UrOption` registered for
    *number*, or ``None`` if no such option has been registered.
    """
    return _OptionRegistry.get(number, None)


# Meta class used to enforce constraints on option types.  This serves
# several purposes:
#
# * It ensures that each subclass of UrOption properly provides both a
#   number and a format attribute;
#
# * It verifies that the values of these attributes are
#
# * It rewrites the subclass so that those attributes are read-only in
#   both class and instance forms;
#
# * It registers each option class so that it can be looked up by
#   number.
#
class _MetaUrOption(type):

    # This class must do its work before UrOption has been added to
    # the module namespace.  Once that's been done this will be a
    # reference to it.
    __UrOption = None

    @classmethod
    def SetUrOption(cls, ur_option):
        cls.__UrOption = ur_option

    def __new__(cls, name, bases, namespace):
        # Provide a unique type that can hold the immutable class
        # number and format values.
        class UniqueUrOption (cls):
            pass

        # Only subclasses of UrOption have non-None number and format
        # values.  Make those attributes immutable at both the class
        # and instance levels.
        if (cls.__UrOption is not None):
            for n in ('number', 'format'):
                v = namespace.get(n, None)
                mp = property(lambda self_or_cls, _v=v: _v)
                namespace[n] = mp
                setattr(UniqueUrOption, n, mp)

        # Create the subclass type, and register it if it's not
        # UrOption.
        mcls = type.__new__(UniqueUrOption, name, bases, namespace)
        if cls.__UrOption is not None:
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

    format = None

    class empty (object):
        pass

    class opaque (bytes):
        pass

    class uint (int):
        pass

    class string (unicode):
        pass

# Register the UrOption so subclasses can
_MetaUrOption.SetUrOption(UrOption)


class IfMatch (UrOption):
    number = 1
    format = UrOption.opaque


class UriHost (UrOption):
    number = 3
    format = UrOption.string


class ETag (UrOption):
    number = 4
    format = UrOption.opaque


class IfNoneMatch (UrOption):
    number = 5
    format = UrOption.empty


class UriPort (UrOption):
    number = 7
    format = UrOption.uint


class LocationPath (UrOption):
    number = 8
    format = UrOption.string


class UriPath (UrOption):
    number = 11
    format = UrOption.string


class ContentFormat (UrOption):
    number = 12
    format = UrOption.uint


class MaxAge (UrOption):
    number = 14
    format = UrOption.uint


class UriQuery (UrOption):
    number = 15
    format = UrOption.string


class Accept (UrOption):
    number = 17
    format = UrOption.uint


class LocationQuery (UrOption):
    number = 20
    format = UrOption.string


class ProxyUri (UrOption):
    number = 35
    format = UrOption.string


class ProxyScheme (UrOption):
    number = 39
    format = UrOption.string


class Size1 (UrOption):
    number = 60
    format = UrOption.uint
