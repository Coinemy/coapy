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
        self.assertEqual([3, 6, 12, 24], delays)


class TestRetransmissionState (unittest.TestCase):
    def testBasic(self):
        rs = RetransmissionState(3, 2)
        self.assertEqual([3, 6], list(rs))
        rs = RetransmissionState(3, 4)
        self.assertEqual([3, 6, 12, 24], list(rs))
        rs = RetransmissionState(1, 5)
        self.assertEqual([1, 2, 4, 8, 16], list(rs))


class TestMessage (unittest.TestCase):
    def testType(self):
        m = Message()
        self.assertEqual(m.messageType, Message.Type_NON)
        self.assertFalse(m.is_confirmable())
        self.assertTrue(m.is_non_confirmable())
        self.assertFalse(m.is_acknowledgement())
        self.assertFalse(m.is_reset())
        m = Message(confirmable=True)
        self.assertEqual(m.messageType, Message.Type_CON)
        self.assertTrue(m.is_confirmable())
        self.assertFalse(m.is_non_confirmable())
        self.assertFalse(m.is_acknowledgement())
        self.assertFalse(m.is_reset())
        m = Message(acknowledgement=True)
        self.assertEqual(m.messageType, Message.Type_ACK)
        self.assertFalse(m.is_confirmable())
        self.assertFalse(m.is_non_confirmable())
        self.assertTrue(m.is_acknowledgement())
        self.assertFalse(m.is_reset())
        m = Message(reset=True)
        self.assertEqual(m.messageType, Message.Type_RST)
        self.assertFalse(m.is_confirmable())
        self.assertFalse(m.is_non_confirmable())
        self.assertFalse(m.is_acknowledgement())
        self.assertTrue(m.is_reset())

    @staticmethod
    def setCode(instance, value):
        instance.code = value

    def testCode(self):
        m = Message()
        self.assertTrue(m.code is None)
        with self.assertRaises(ValueError):
            _ = m.packed_code
        m.code = 0
        self.assertEqual((0, 0), m.code)
        self.assertEqual(0, m.packed_code)
        m.code = (7, 15)
        self.assertEqual((7, 15), m.code)
        self.assertEqual(0xEF, m.packed_code)
        for ic in (-3, (1, 2, 3)):
            with self.assertRaises(ValueError):
                self.setCode(m, ic)
        for ic in (None, 23.42, [1, 2]):
            with self.assertRaises(TypeError):
                self.setCode(m, ic)
        m = Message(code=0xef)
        self.assertEqual((7, 15), m.code)

    @staticmethod
    def setMessageID(instance, value):
        instance.messageID = value

    def testMessageID(self):
        m = Message()
        self.assertTrue(m.messageID is None)
        m.messageID = 3
        self.assertEqual(3, m.messageID)
        self.assertRaises(TypeError, self.setMessageID, m, None)
        self.assertRaises(TypeError, self.setMessageID, m, 4.3)
        self.assertRaises(ValueError, self.setMessageID, m, -1)
        self.assertRaises(ValueError, self.setMessageID, m, 65536)

    @staticmethod
    def setToken(instance, value):
        instance.token = value

    def testToken(self):
        m = Message()
        self.assertTrue(m.token is None)
        m.token = b'123'
        self.assertEqual(b'123', m.token)
        m.token = None
        self.assertTrue(m.token is None)
        self.assertRaises(TypeError, self.setToken, m, 'text')
        self.assertRaises(ValueError, self.setToken, m, b'')
        self.assertRaises(ValueError, self.setToken, m, b'123456789')

    @staticmethod
    def setPayload(instance, value):
        instance.payload = value

    def testPayload(self):
        m = Message()
        self.assertTrue(m.payload is None)
        m.payload = b'123'
        self.assertEqual(b'123', m.payload)
        m.payload = None
        self.assertTrue(m.payload is None)
        m.payload = b''
        self.assertTrue(m.payload is None)
        self.assertRaises(TypeError, self.setPayload, m, 'text')

    def testReadOnly(self):
        m = Message()
        self.assertEqual(0, Message.Type_CON)
        self.assertEqual(0, m.Type_CON)
        self.assertEqual(1, Message.Type_NON)
        self.assertEqual(1, m.Type_NON)
        self.assertEqual(2, Message.Type_ACK)
        self.assertEqual(2, m.Type_ACK)
        self.assertEqual(3, Message.Type_RST)
        self.assertEqual(3, m.Type_RST)
        with self.assertRaises(AttributeError):
            Message.Type_CON = 23
        with self.assertRaises(AttributeError):
            Message.Type_NON = 23
        with self.assertRaises(AttributeError):
            Message.Type_ACK = 23
        with self.assertRaises(AttributeError):
            Message.Type_RST = 23


class TestRequest (unittest.TestCase):
    def testImmutable(self):
        req = Request()
        with self.assertRaises(AttributeError):
            Request.Class = 8
        with self.assertRaises(AttributeError):
            req.Class = 8
        with self.assertRaises(AttributeError):
            Request.GET = 8
        with self.assertRaises(AttributeError):
            req.GET = 8
        with self.assertRaises(AttributeError):
            Request.POST = 8
        with self.assertRaises(AttributeError):
            req.POST = 8
        with self.assertRaises(AttributeError):
            Request.PUT = 8
        with self.assertRaises(AttributeError):
            req.PUT = 8
        with self.assertRaises(AttributeError):
            Request.DELETE = 8
        with self.assertRaises(AttributeError):
            req.DELETE = 8
        self.assertEqual(0, Request.Class)
        self.assertEqual(1, Request.GET)
        self.assertEqual(2, Request.POST)
        self.assertEqual(3, Request.PUT)
        self.assertEqual(4, Request.DELETE)
        self.assertEqual(0, req.Class)
        self.assertEqual(1, req.GET)
        self.assertEqual(2, req.POST)
        self.assertEqual(3, req.PUT)
        self.assertEqual(4, req.DELETE)


if __name__ == '__main__':
    unittest.main()
