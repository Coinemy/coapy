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


if __name__ == '__main__':
    unittest.main()
