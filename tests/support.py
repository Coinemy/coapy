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
Support for CoAPy unit testing.

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
import unittest


class ManagedClock_mixin(object):
    """Extension that replaces :data:`coapy.clock` with an instance of
    :class:`coapy.ManagedClock` to eliminate non-determinism in clock
    queries.

    This class should be mixed-in as a base class along with
    :class:`python:unittest.TestCase` for tests that need to control
    the CoAPy clock.
    """
    def setUp(self):
        """Cooperative super-calling support to install managed clock."""
        super(ManagedClock_mixin, self).setUp()
        self.__clock = coapy.clock
        coapy.clock = coapy.ManagedClock()

    def tearDown(self):
        """Cooperative super-calling support to return to default
        clock.
        """
        coapy.clock = self.__clock
        super(ManagedClock_mixin, self).tearDown()


class DeterministicBEBO_mixin(object):
    """Extension that replaces :data:`coapy.transmissionParameters`
    with an instance of :class:`coapy.message.TransmissionParameters`
    that sets
    :attr:`ACK_RANDOM_FACTOR<coapy.message.TransmissionParameters.ACK_RANDOM_FACTOR>`
    to 1.0 to eliminate non-determinism in delays.

    This class should be mixed-in as a base class along with
    :class:`python:unittest.TestCase` for tests that need
    deterministic retransmission behavior.
    """

    def setUp(self):
        """Cooperative super-calling support to install deterministic
        transmission parameters.
        """
        super(DeterministicBEBO_mixin, self).setUp()
        import coapy.message
        self.__transmission_parameters = coapy.transmissionParameters
        coapy.transmissionParameters = coapy.message.TransmissionParameters()
        coapy.transmissionParameters.ACK_RANDOM_FACTOR = 1.0
        coapy.transmissionParameters.recalculate_derived()

    def tearDown(self):
        """Cooperative super-calling support to return to default
        transmission parameters.
        """
        coapy.transmissionParameters = self.__transmission_parameters
        super(DeterministicBEBO_mixin, self).tearDown()
