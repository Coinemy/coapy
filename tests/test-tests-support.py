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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
_log = logging.getLogger(__name__)

import unittest
import coapy
import tests.support


class TestManagedClock (tests.support.ManagedClock_mixin, unittest.TestCase):

    def testBasic(self):
        self.assertEqual(1.5, coapy.transmissionParameters.ACK_RANDOM_FACTOR)
        clk = coapy.clock
        self.assertTrue(isinstance(clk, coapy.ManagedClock))
        self.assertEqual(0.0, clk())


class TestDeterministicBEBO (tests.support.DeterministicBEBO_mixin, unittest.TestCase):

    def testBasic(self):
        clk = coapy.clock
        self.assertTrue(isinstance(clk, coapy.RealTimeClock))
        self.assertEqual(1.0, coapy.transmissionParameters.ACK_RANDOM_FACTOR)


class TestLogHandler (tests.support.LogHandler_mixin, unittest.TestCase):
    def testBasic(self):
        self.assertTrue(self.log_handler is not None)
        hdl = self.log_handler
        self.assertTrue(isinstance(hdl.buffer, list))
        self.assertEqual(0, len(hdl.buffer))
        self.assertTrue(_log.isEnabledFor(logging.ERROR))
        self.assertTrue(_log.isEnabledFor(logging.DEBUG))
        _log.debug('hi there')
        self.assertEqual(1, len(hdl.buffer))
        rec = hdl.buffer[0]
        self.assertEqual(rec.levelno, logging.DEBUG)
        self.assertEqual(rec.msg, 'hi there')
        self.assertEqual(rec.funcName, 'testBasic')
        hdl.flush()
        self.assertEqual(0, len(hdl.buffer))


class TestFIFOEndpoint (unittest.TestCase):

    def testBasic(self):
        import socket
        import errno
        ep1 = tests.support.FIFOEndpoint()
        ep2 = tests.support.FIFOEndpoint()
        with self.assertRaises(socket.error) as cm:
            (data, sep) = ep1.rawrecvfrom(2048)
        e = cm.exception
        self.assertEqual(e.args[0], errno.EAGAIN)
        self.assertEqual(e.args[1], 'Resource temporarily unavailable')
        ep1.rawsendto(b'hi there', ep2)
        (rv, sep) = ep2.rawrecvfrom(2048)
        self.assertTrue(sep is ep1)
        self.assertEqual(b'hi there', rv)


if __name__ == '__main__':
    unittest.main()
