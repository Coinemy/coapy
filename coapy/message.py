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
Something

:copyright: Copyright 2013, Peter A. Bigot
:license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


import random
import coapy


class TransmissionParameters(object):
    """The :coapsect:`transmission parameters<4.8>` that support
    message transmission behavior including :coapsect:`congestion
    control<4.7>` in CoAP.

    Some of these parameters are primitive, and some are derived.
    Consult :coapsect:`4.8.1` for information related to changing
    these parameters.  After changing the primitive parameters in an
    instance, invoke :func:`recalculate_derived` to update the derived
    parameters.

    ==========================  ==============  ==================  ==========
    Parameter                   Units           Documentation       Class
    ==========================  ==============  ==================  ==========
    :attr:`ACK_TIMEOUT`         seconds         :coapsect:`4.8`     Primitive
    :attr:`ACK_RANDOM_FACTOR`   seconds         :coapsect:`4.8`     Primitive
    :attr:`MAX_RETRANSMIT`      transmissions   :coapsect:`4.8`     Primitive
    :attr:`NSTART`              messages        :coapsect:`4.7`     Primitive
    :attr:`DEFAULT_LEISURE`     seconds         :coapsect:`8.2`     Primitive
    :attr:`PROBING_RATE`        bytes/second    :coapsect:`4.7`     Primitive
    :attr:`MAX_LATENCY`         seconds         :coapsect:`4.8.2`   Primitive
    :attr:`PROCESSING_DELAY`    seconds         :coapsect:`4.8.2`   Primitive
    :attr:`MAX_TRANSMIT_SPAN`   seconds         :coapsect:`4.8.2`   Derived
    :attr:`MAX_TRANSMIT_WAIT`   seconds         :coapsect:`4.8.2`   Derived
    :attr:`MAX_RTT`             seconds         :coapsect:`4.8.2`   Derived
    :attr:`EXCHANGE_LIFETIME`   seconds         :coapsect:`4.8.2`   Derived
    :attr:`NON_LIFETIME`        seconds         :coapsect:`4.8.2`   Derived
    ==========================  ==============  ==================  ==========

    """

    ACK_TIMEOUT = 2
    """The initial timeout waiting for an acknowledgement, in seconds."""

    ACK_RANDOM_FACTOR = 1.5
    """A randomization factor to avoid synchronization, in seconds."""

    MAX_RETRANSMIT = 4
    """The maximum number of retransmissions of a confirmable message.
    A value of 4 produces a maximum of 5 transmissions when the first
    transmission is included."""

    NSTART = 1
    """The maximum number of messages permitted to be outstanding for
    an endpoint."""

    DEFAULT_LEISURE = 5
    """A duration, in seconds, that a server may delay before
    responding to a multicast message."""

    PROBING_RATE = 1
    """The target maximum average data rate, in bytes per second, for
    transmissions to an endpoint that does not respond."""

    MAX_LATENCY = 100
    """The maximum time, in seconds, expected from the start of
    datagram transmission to completion of its reception.  This
    includes endpoint transport-, link-, and physical-layer
    processing, propagation delay through the communications medium,
    and intermediate routing overhead."""

    PROCESSING_DELAY = ACK_TIMEOUT
    """The maximum time, in seconds, that node requires to generate an
    acknowledgement to a confirmable message."""

    MAX_TRANSMIT_SPAN = 45
    """Maximum time, in seconds, from first transmission of a
    confirmable message to its last retransmission.."""

    MAX_TRANSMIT_WAIT = 93
    """Maximum time, in seconds, from first transmission of a
    confirmable message to when the sender may give up on receiving
    acknowledgement or reset."""

    MAX_RTT = 202
    """Maximum round-trip-time, in seconds, considering
    :attr:`MAX_LATENCY` and :attr:`PROCESSING_DELAY`."""

    EXCHANGE_LIFETIME = 247
    """Time, in seconds, from first transmission of a confirmable
    message to when an acknowledgement is no longer expected."""

    NON_LIFETIME = 145
    """Time, in seconds, from transmission of a non-confirmable
    message to when its Message-ID may be safely re-used."""

    def recalculate_derived(self):
        """Calculate values for parameters that may be derived.

        This uses the calculations in :coapsect:`4.8.2` to calculate
        :attr:`MAX_TRANSMIT_SPAN`, :attr:`MAX_TRANSMIT_WAIT`,
        :attr:`MAX_RTT`, :attr:`EXCHANGE_LIFETIME`, and
        :attr:`NON_LIFETIME` from other parameters in the instance.
        """
        self.MAX_TRANSMIT_SPAN = \
            self.ACK_TIMEOUT \
            * ((1 << self.MAX_RETRANSMIT) - 1) \
            * self.ACK_RANDOM_FACTOR
        self.MAX_TRANSMIT_WAIT = \
            self.ACK_TIMEOUT \
            * ((1 << (self.MAX_RETRANSMIT + 1)) - 1) \
            * self.ACK_RANDOM_FACTOR
        self.MAX_RTT = (2 * self.MAX_LATENCY) + self.PROCESSING_DELAY
        self.EXCHANGE_LIFETIME = self.MAX_TRANSMIT_SPAN + self.MAX_RTT
        self.NON_LIFETIME = self.MAX_TRANSMIT_SPAN + self.MAX_LATENCY

    def timeout_control(self, initial_timeout=None, max_retransmissions=None):
        return RetransmissionState(initial_timeout=initial_timeout,
                                   max_retransmissions=max_retransmissions,
                                   transmission_parameters=self)


class RetransmissionState (object):
    """An iterable that provides the time to the next retransmission.

    *initial_timeout* is the time, in seconds, to the first
    retransmission; a default is calculated from
    *transmission_parameters* if provided.

    *max_retransmissions* is the total number of re-transmissions; a
    default is obtained from *transmission_parameters* if provided.

    Thus::

      list(RetransmissionState(3,4))

    will produce::

      [3, 6, 12, 24]

    """
    def __init__(self, initial_timeout=None,
                 max_retransmissions=None, transmission_parameters=None):
        if (not isinstance(transmission_parameters, TransmissionParameters)
            and ((initial_timeout is None)
                 or (max_retransmissions is None))):
            raise ValueError
        if initial_timeout is None:
            initial_timeout = \
                transmission_parameters.ACK_TIMEOUT \
                + random.random() * transmission_parameters.ACK_RANDOM_FACTOR
        if max_retransmissions is None:
            max_retransmissions = transmission_parameters.MAX_RETRANSMIT
        self.timeout = initial_timeout
        self.max_retransmissions = max_retransmissions
        self.counter = 0

    def __iter__(self):
        return self

    def _get_remaining(self):
        """The number of retransmissions remaining in the iterator."""
        return self.max_retransmissions - self.counter
    retransmissions_remaining = property(_get_remaining)

    def next(self):
        if self.counter >= self.max_retransmissions:
            raise StopIteration
        rv = self.timeout
        self.counter += 1
        self.timeout += self.timeout
        return rv
