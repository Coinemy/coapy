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
    *************
    coapy.message
    *************

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
    ACK_TIMEOUT = 2                 # seconds
    ACK_RANDOM_FACTOR = 1.5         # no units
    MAX_RETRANSMIT = 4              # transmissions
    NSTART = 1                      # messages
    DEFAULT_LEISURE = 5             # seconds
    PROBING_RATE = 1                # bytes per second
    MAX_LATENCY = 100               # seconds
    PROCESSING_DELAY = ACK_TIMEOUT  # seconds
    MAX_TRANSMIT_SPAN = 45          # seconds
    MAX_TRANSMIT_WAIT = 93          # seconds
    MAX_LATENCY = 100               # seconds
    MAX_RTT = 202                   # seconds
    EXCHANGE_LIFETIME = 247         # seconds
    NON_LIFETIME = 145              # seconds

    def recalculate_derived(self):
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

    def timeout_control(self, initial_timeout=None):
        class retry (object):
            def __init__(self, params, initial_timeout):
                if initial_timeout is None:
                    initial_timeout = \
                        params.ACK_TIMEOUT \
                        + random.random() * params.ACK_RANDOM_FACTOR
                self.timeout = initial_timeout
                self.max_counter = params.MAX_RETRANSMIT
                self.counter = -1

            def __iter__(self):
                return self

            def next(self):
                if not self.have_next():
                    raise StopIteration
                rv = self.timeout
                self.counter += 1
                self.timeout += self.timeout
                return rv

            def have_next(self):
                return self.counter < self.max_counter

        return retry(self, initial_timeout)
