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
    *****
    coapy
    *****

    :copyright: Copyright 2013, Peter A. Bigot
    :license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
_log = logging.getLogger(__name__)


COAP_PORT = 5683
"""The IANA-assigned default port number for unsecured CoAP (the
"coap" URI scheme).
"""

COAPS_PORT = 0
"""The IANA-assigned default port number for secured CoAP (the "coaps"
URI scheme).
"""


class CoAPyException (Exception):
    pass


class InfrastructureError (CoAPyException):
    pass


transmissionParameters = None
"""The default instance of
:class:`TransmissionParameters<coapy.message.TransmissionParameters>`
for the system.

This is initialized when :mod:`coapy.message` is first loaded.
"""


class _Clock(object):
    """Base class for CoAPy clock abstraction.

    An instance of (a subclass of) this class is made available
    globally at :data:`coapy.clock`.

    The current clock value is obtained by invoking the instance as a
    callable object.
    """

    @property
    def epoch(self):
        """The value of this clock at a point corresponding to "system
        start".

        Set implicitly when the clock instance is created.
        """
        return self.__epoch

    def __call__(self):
        raise NotImplementedException

    def __init__(self):
        self.__epoch = self()


class ManagedClock(_Clock):
    """A clock that increments under program control.

    An instance of this class may be placed in :data:`coapy.clock` to
    ensure deterministic behavior for simulation and automated
    testing.  The value of the clock is initially zero; it is changed
    only through the :meth:`adjust` method.
    """
    def __init__(self):
        self.__clock = 0.0
        super(ManagedClock, self).__init__()

    def __call__(self):
        return self.__clock

    def adjust(self, adj):
        """Add *adj* to the clock value."""
        self.__clock += adj


class RealTimeClock(_Clock):
    """A clock that increments in lock-step with real-time.

    This uses :func:`python:time.time` to obtain the current time.
    :attr:`epoch<_Clock.epoch>` is a record of the time at which the
    clock was created.
    """
    def __call__(self):
        import time
        return time.time()


clock = RealTimeClock()
"""The system clock.

This is an instance of :class:`_Clock` that returns a non-decreasing
ordinal when invoked (probably a :class:`python:float` but possibly an
:class:`python:int`).  The integer part increments in "seconds".  It
is used for :class:`Max-Age<coapy.option.MaxAge>`, state related to
:coapsect:`congestion control<4.7>` and :coapsect:`message
retransmission<4.2>`, and other time-related phenomena.

.. note::
   The default value is an instance of :class:`RealTimeClock`, but
   this may be overridden with an instance of :class:`ManagedClock`
   for the purposes of simulation or testing.  Unless you're doing
   this sort of thing, you should assume the clock increments in lock
   step with real-world time.
"""
