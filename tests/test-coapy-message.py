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


import unittest
from coapy.message import *


class TestTransmissionParameters (unittest.TestCase):
    def testDefaults(self):
        tp = TransmissionParameters()
        self.assertEqual(tp.ACK_TIMEOUT, 2)
        self.assertEqual(tp.ACK_RANDOM_FACTOR, 1.5)
        self.assertEqual(tp.MAX_RETRANSMIT, 4)
        self.assertEqual(tp.NSTART, 1)
        self.assertEqual(tp.DEFAULT_LEISURE, 5)
        self.assertEqual(tp.PROBING_RATE, 1)

    def checkDerived(self, tp):
        self.assertEqual(tp.MAX_TRANSMIT_SPAN, 45)
        self.assertEqual(tp.MAX_TRANSMIT_WAIT, 93)
        self.assertEqual(tp.MAX_LATENCY, 100)
        self.assertEqual(tp.PROCESSING_DELAY, 2)
        self.assertEqual(tp.MAX_RTT, 202)
        self.assertEqual(tp.EXCHANGE_LIFETIME, 247)
        self.assertEqual(tp.NON_LIFETIME, 145)

    def testDerived(self):
        tp = TransmissionParameters()
        self.checkDerived(tp)
        tp.recalculate_derived()
        self.checkDerived(tp)

    def testIterator(self):
        tp = TransmissionParameters()
        delays = list(tp.timeout_control(3))
        self.assertEqual([3, 6, 12, 24, 48], delays)


if __name__ == '__main__':
    unittest.main()
