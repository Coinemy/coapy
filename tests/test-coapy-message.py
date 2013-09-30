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

    def testDefaults(self):
        tp = TransmissionParameters()
        rs = tp.timeout_control()
        self.assertEqual(rs.retransmissions_remaining, tp.MAX_RETRANSMIT)
        ti = rs.timeout
        t0 = rs.next()
        self.assertTrue((t0 >= tp.ACK_TIMEOUT) and (t0 < (tp.ACK_TIMEOUT + tp.ACK_RANDOM_FACTOR)))
        self.assertEqual(t0, ti)


class TestRetransmissionState (unittest.TestCase):
    def testBasic(self):
        rs = RetransmissionState(3, 2)
        self.assertEqual([3, 6], list(rs))
        rs = RetransmissionState(3, 4)
        self.assertEqual([3, 6, 12, 24], list(rs))
        rs = RetransmissionState(1, 5)
        self.assertEqual([1, 2, 4, 8, 16], list(rs))

    def testBadCreation(self):
        with self.assertRaises(ValueError):
            RetransmissionState(initial_timeout=3)
        with self.assertRaises(ValueError):
            RetransmissionState(max_retransmissions=4)


class TestCodeSupport (unittest.TestCase):
    def testBasic(self):
        m = Message(code=Request.GET)
        self.assertEqual(m.code, Request.GET)
        cs = m.code_support()
        self.assertEqual(cs.name, 'GET')
        self.assertEqual(cs.constructor, Request)
        self.assertEqual(Message._type_for_code(m.code), Request)

    def testUnregistered(self):
        m = Message(code=(1,31))
        self.assertEqual(m.code, (1,31))
        cs = m.code_support()
        self.assertTrue(m.code_support() is None)
        self.assertTrue(Message._type_for_code(m.code) is None)


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
        self.assertRaises(TypeError, Message.code_as_tuple, None)
        self.assertRaises(ValueError, Message.code_as_tuple, (1, 2, 3))
        self.assertRaises(ValueError, Message.code_as_tuple, (8, 0))
        self.assertRaises(ValueError, Message.code_as_tuple, (1, 32))
        self.assertRaises(TypeError, Message.code_as_integer, None)
        self.assertRaises(ValueError, Message.code_as_integer, (1, 2, 3))
        self.assertRaises(ValueError, Message.code_as_integer, (8, 0))
        self.assertRaises(ValueError, Message.code_as_integer, (1, 32))
        self.assertEqual((0, 0), Message.code_as_tuple(0))
        self.assertEqual((7, 15), Message.code_as_tuple(0xef))
        self.assertEqual(0xef, Message.code_as_integer(0xef))
        self.assertEqual(0xef, Message.code_as_integer((7, 15)))
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

    def testOptions(self):
        m = Message()
        self.assertEqual([], m.options)
        m.options = [coapy.option.UriPath('p1'),
                     coapy.option.UriHost('h')]
        self.assertTrue(isinstance(m.options, list))
        self.assertEqual(2, len(m.options))
        # Assignment sorts the instances
        self.assertTrue(isinstance(m.options[0], coapy.option.UriHost))
        self.assertTrue(isinstance(m.options[1], coapy.option.UriPath))

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

    def testStringize(self):
        m = Message(confirmable=True, token=b'123', message_id=0x1234, code=Request.GET,
                    options=[coapy.option.UriPath('sensor'),
                             coapy.option.UriPath('temp')],
                    payload=b'20 C')
        self.assertEqual(unicode(m), '''[1234] CON 0.01 (GET)
Token: 123
Option UriPath: sensor
Option UriPath: temp
Payload: 20 C''')


class TestRequest (unittest.TestCase):
    def testImmutable(self):
        req = Request()
        with self.assertRaises(AttributeError):
            Request.CodeClass = 8
        with self.assertRaises(AttributeError):
            req.CodeClass = 8
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
        self.assertEqual(0, Request.CodeClass)
        self.assertEqual((0, 1), Request.GET)
        self.assertEqual((0, 2), Request.POST)
        self.assertEqual((0, 3), Request.PUT)
        self.assertEqual((0, 4), Request.DELETE)
        self.assertEqual(0, req.CodeClass)
        self.assertEqual((0, 1), req.GET)
        self.assertEqual((0, 2), req.POST)
        self.assertEqual((0, 3), req.PUT)
        self.assertEqual((0, 4), req.DELETE)


class TestClassRegistry (unittest.TestCase):
    def testBasic(self):
        self.assertEqual(Request, Message._type_for_code(Request.GET))
        self.assertEqual(SuccessResponse, Message._type_for_code(SuccessResponse.Valid))
        self.assertEqual(ClientErrorResponse,
                         Message._type_for_code(ClientErrorResponse.NotFound))
        self.assertEqual(ServerErrorResponse,
                         Message._type_for_code(ServerErrorResponse.NotImplemented))


class TestMessageEncodeDecode (unittest.TestCase):
    import coapy.option

    def testBasic(self):
        m = Message(confirmable=True, token=b'123', message_id=0x1234, code=Request.GET)
        phdr = b'\x43\x01\x12\x34123'
        popt = b''
        ppld = b''
        pm = m.to_packed()
        self.assertTrue(isinstance(pm, bytes))
        self.assertEqual(phdr + popt + ppld, pm)
        m.options = [coapy.option.UriPath(u'sensor')]
        popt = coapy.option.encode_options(m.options)
        pm = m.to_packed()
        self.assertTrue(isinstance(pm, bytes))
        self.assertEqual(phdr + popt + ppld, pm)
        m.payload = b'20 C'
        ppld = b'\xff' + m.payload
        pm = m.to_packed()
        self.assertTrue(isinstance(pm, bytes))
        self.assertEqual(phdr + popt + ppld, pm)
        m2 = Message.from_packed(pm)
        self.assertEqual(m.messageType, m2.messageType)
        self.assertEqual(m.code, m2.code)
        self.assertEqual(m.messageID, m2.messageID)
        self.assertEqual(m.token, m2.token)
        self.assertEqual(len(m.options), len(m2.options))
        for i in xrange(len(m.options)):
            self.assertEqual(type(m.options[i]), type(m2.options[i]))
            self.assertEqual(m.options[i].value, m2.options[i].value)
        self.assertEqual(m.payload, m2.payload)


    def testDiagnosticEmpty(self):
        empty_diag = '4.1: bytes after Message ID'
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(b'\x42\x00\x00\x00')
        self.assertEqual(cm.exception.args[0], empty_diag)
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(b'\x40\x00\x00\x00\x01')
        self.assertEqual(cm.exception.args[0], empty_diag)

    def testInvalid(self):
        self.assertRaises(TypeError, Message.from_packed, 'text')
        m = Message.from_packed(b'\x80')
        self.assertTrue(m is None)
        packed = b'\x43\x01\x12\x34123\xF0'
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(packed)
        self.assertEqual(cm.exception.args[0], 'option decode error')
        packed = b'\x43\x01\x12\x34123\xFF'
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(packed)
        self.assertEqual(cm.exception.args[0], 'empty payload')

    def testUnrecognizedCodes(self):
        m = Message.from_packed(b'\x40\x8A\x12\x34')
        self.assertEqual((4, 10), m.code)
        self.assertTrue(isinstance(m, ClientErrorResponse))
        with self.assertRaises(MessageFormatError) as cm:
            m = Message.from_packed(b'\x40\x6A\x12\x34')
        self.assertEqual(cm.exception.args[0], 'unrecognized code')
        self.assertEqual(cm.exception.args[1], (3, 10))


if __name__ == '__main__':
    unittest.main()
