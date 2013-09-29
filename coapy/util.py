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


class ClassReadOnly (object):
    """A marker to indicate an attribute of a class should be
    read-only within the class as well as instances of the class.

    Effective only if the metaclass is (or is derived from)
    :class:`ReadOnlyMeta`.  The read-only nature of the attribute is
    not inherited in sub-classes.

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

      class SubC(C):
          # But nothing prevents this:
          Zero = 2
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
