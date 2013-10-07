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
Utility classes and functions used within CoAPy.

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
import unicodedata
import functools


class ClassReadOnly (object):
    """A marker to indicate an attribute of a class should be
    read-only within the class as well as instances of the class.

    Effective only if the metaclass is (or is derived from)
    :class:`ReadOnlyMeta`.

    Example::

      class C(Object):
          __metaclass__ = ReadOnlyMeta

          Zero = ClassReadOnly(0)

      instance = C()
      assert 0 == C.Zero
      assert 0 == instance.Zero

      # This will raise an exception:
      C.Zero = 4
      # As will this:
      instance.Zero = 4
    """

    def __init__(self, value):
        self.value = value


class ReadOnlyMeta (type):
    """Metaclass for supporting read-only values in classes.

    When used as a metaclass, this inserts an intermediary type that
    prevents assignment to certain attributes at both the instance and
    class levels.  Any attribute in the class that is initialized in
    the class body with a value of type :class:`ClassReadOnly` is made
    read-only.

    See example at :class:`ClassReadOnly`.

    """
    def __new__(cls, name, bases, namespace):
        # Provide a unique type that can hold the read-only class
        # values.
        class ReadOnly (cls):
            pass
        nsdup = namespace.copy()
        for (n, v) in namespace.iteritems():
            if isinstance(v, ClassReadOnly):
                mp = property(lambda self_or_cls, _v=v.value: _v)
                nsdup[n] = mp
                setattr(ReadOnly, n, mp)
        return super(ReadOnlyMeta, cls).__new__(ReadOnly, name, bases, nsdup)


@functools.total_ordering
class TimeDueOrdinal(object):
    """Base class for elements that are sorted by time.

    The intent is that information related to an activity that should
    occur at or after a particular time be held in a subclass of
    :class:`TimeDueOrdinal`.  The priority queue of upcoming activity
    is implemented using a sorted list, as instances of (subclasses
    of) :class:`TimeDueOrdinal` are ordered by increasing value of
    :attr:`time_due` using the features of :mod:`python:bisect`.

    *time_due* as a keyword parameter is the initial value of
    :attr:`time_due`.
    """

    time_due = None
    """The time at which the subclass instance becomes relevant.

    This is a value in the ordinal space defined by
    :func:`coapy.clock`.
    """

    def __init__(self, **kw):
        time_due = kw.pop('time_due', None)
        super(TimeDueOrdinal, self).__init__(**kw)
        self.time_due = time_due

    def __eq__(self, other):
        return self.time_due == other.time_due

    # total_ordering doesn't handle eq/ne inference, so need both
    def __ne__(self, other):
        return self.time_due != other.time_due

    def __lt__(self, other):
        return self.time_due < other.time_due


def to_net_unicode(text):
    """Convert text to Net-Unicode (:rfc:`5198`) data.

    This normalizes the text to ensure all characters are their own
    canonical equivalent in the NFC form (section 3 of :rfc:`5198`).
    The result is encoded in UTF-8 and returned.

    The operation currently does not handle newline normalization
    (section 2 item 2), since its use in CoAP is currently limited to
    values of options with format :class:`coapy.option.format_string`.
    """
    # At first blush, this is Net-Unicode.
    return unicodedata.normalize('NFC', text).encode('utf-8')
