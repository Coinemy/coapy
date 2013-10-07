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
import logging
import logging.handlers
from coapy.message import *
from coapy.endpoint import Endpoint


class TestHandler (logging.handlers.BufferingHandler):
    def __init__(self, capacity, module_under_test):
        super(TestHandler, self).__init__(capacity)
        self.__log = logging.getLogger(module_under_test.__name__)
        self.__log.addHandler(self)

    def detach(self):
        self.__log.removeHandler(self)

    def records(self):
        return map(self.format, self.buffer)


class TestTransmissionParameters (unittest.TestCase):
    def checkIsDefault(self, tp):
        self.assertEqual(tp.ACK_TIMEOUT, 2)
        self.assertEqual(tp.ACK_RANDOM_FACTOR, 1.5)
        self.assertEqual(tp.MAX_RETRANSMIT, 4)
        self.assertEqual(tp.NSTART, 1)
        self.assertEqual(tp.DEFAULT_LEISURE, 5)
        self.assertEqual(tp.PROBING_RATE, 1)

    def checkIsDerivedDefault(self, tp):
        self.assertEqual(tp.MAX_TRANSMIT_SPAN, 45)
        self.assertEqual(tp.MAX_TRANSMIT_WAIT, 93)
        self.assertEqual(tp.MAX_LATENCY, 100)
        self.assertEqual(tp.PROCESSING_DELAY, 2)
        self.assertEqual(tp.MAX_RTT, 202)
        self.assertEqual(tp.EXCHANGE_LIFETIME, 247)
        self.assertEqual(tp.NON_LIFETIME, 145)

    def testDefaults(self):
        tp = TransmissionParameters()
        self.checkIsDefault(tp)
        self.checkIsDerivedDefault(tp)

    def testGlobalDefaults(self):
        self.checkIsDefault(coapy.transmissionParameters)
        self.checkIsDerivedDefault(coapy.transmissionParameters)

    def testDerived(self):
        tp = TransmissionParameters()
        self.checkIsDefault(tp)
        tp.recalculate_derived()
        self.checkIsDerivedDefault(tp)

    def testIterator(self):
        tp = TransmissionParameters()
        delays = list(tp.timeout_control(3))
        self.assertEqual([3, 6, 12, 24], delays)

    def testTimeoutControl(self):
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
        m = Message(code=(1, 31))
        self.assertEqual(m.code, (1, 31))
        cs = m.code_support()
        self.assertTrue(m.code_support() is None)
        self.assertTrue(Message._type_for_code(m.code) is None)


class TestMessage (unittest.TestCase):
    def testType(self):
        m = Message()
        self.assertEqual(m.messageType, Message.Type_NON)
        self.assertTrue(m.source_defines_messageID())
        self.assertFalse(m.is_confirmable())
        self.assertTrue(m.is_non_confirmable())
        self.assertFalse(m.is_acknowledgement())
        self.assertFalse(m.is_reset())
        m = Message(confirmable=True)
        self.assertEqual(m.messageType, Message.Type_CON)
        self.assertTrue(m.source_defines_messageID())
        self.assertTrue(m.is_confirmable())
        self.assertFalse(m.is_non_confirmable())
        self.assertFalse(m.is_acknowledgement())
        self.assertFalse(m.is_reset())
        m = Message(acknowledgement=True)
        self.assertEqual(m.messageType, Message.Type_ACK)
        self.assertFalse(m.source_defines_messageID())
        self.assertFalse(m.is_confirmable())
        self.assertFalse(m.is_non_confirmable())
        self.assertTrue(m.is_acknowledgement())
        self.assertFalse(m.is_reset())
        m = Message(reset=True)
        self.assertEqual(m.messageType, Message.Type_RST)
        self.assertFalse(m.source_defines_messageID())
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
        m.token = b''
        self.assertEqual(b'', m.token)
        m.token = b'123'
        self.assertEqual(b'123', m.token)
        m = Message(token=b'234')
        self.assertEqual(b'234', m.token)
        self.assertRaises(TypeError, self.setToken, m, None)
        self.assertRaises(TypeError, self.setToken, m, 'text')
        self.assertRaises(TypeError, Message, token='text')
        self.assertRaises(ValueError, self.setToken, m, b'123456789')
        self.assertRaises(ValueError, Message, token=b'123456789')

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
        m = Message()
        self.assertEqual(unicode(m), '''[*INVALID None*] NON ?.?? (*INVALID None*)
Token: **INVALID None**''')
        m = Message(confirmable=True, token=b'123', messageID=12345, code=Request.GET,
                    options=[coapy.option.UriPath('sensor'),
                             coapy.option.UriPath('temp')],
                    payload=b'20 C')
        m.source_endpoint = Endpoint(host='2001:db8:0::2:1')
        m.destination_endpoint = Endpoint(host='2001:db8:0::2:2')
        self.assertEqual(unicode(m), '''[12345] CON 0.01 (GET)
Source: [2001:db8::2:1]:5683
Destination: [2001:db8::2:2]:5683
Token: 123
Option Uri-Path: sensor
Option Uri-Path: temp
Payload: 20 C''')

    def testValidation(self):
        lh = TestHandler(8192, coapy.message)
        try:
            m = Request()
            with self.assertRaises(MessageValidationError) as cm:
                m.validate()
            self.assertEqual(cm.exception.args[0], MessageValidationError.CODE_UNDEFINED)

            for (k, v) in {'token': b'tok',
                           'payload': b'payload',
                           'options': [coapy.option.ETag(b'tag')]}.iteritems():
                m = Message(code=Message.Empty, **{k: v})
                with self.assertRaises(MessageValidationError) as cm:
                    m.validate()
                self.assertEqual(cm.exception.args[0],
                                 MessageValidationError.EMPTY_MESSAGE_NOT_EMPTY)

            m = Message(reset=True, code=SuccessResponse.Created)
            with self.assertRaises(MessageValidationError) as cm:
                m.validate()
            self.assertEqual(cm.exception.args[0], MessageValidationError.CODE_TYPE_CONFLICT)
            m = Message(acknowledgement=True, code=Request.GET)
            with self.assertRaises(MessageValidationError) as cm:
                m.validate()
            self.assertEqual(cm.exception.args[0], MessageValidationError.CODE_TYPE_CONFLICT)
            m = Message(code=Request.GET)
            with self.assertRaises(MessageValidationError) as cm:
                m.validate()
            self.assertEqual(cm.exception.args[0], MessageValidationError.CODE_TYPE_CONFLICT)
            m = Request(code=SuccessResponse.Created)
            with self.assertRaises(MessageValidationError) as cm:
                m.validate()
            self.assertEqual(cm.exception.args[0], MessageValidationError.CODE_INSTANCE_CONFLICT)

            m = Request(code=Request.GET, options=[coapy.option.ProxyUri('coap://localhost/foo'),
                                                   coapy.option.UriHost('localhost')])
            with self.assertRaises(MessageValidationError) as cm:
                m.validate()
            self.assertEqual(cm.exception.args[0], MessageValidationError.PROXY_URI_CONFLICT)

            m = Request(code=Request.GET, options=[coapy.option.UriHost('localhost'),
                                                   coapy.option.UriHost('bogus')])
            lh.flush()
            logmsgs = list(lh.records())
            self.assertEqual(0, len(logmsgs))
            m.validate()
            logmsgs = list(lh.records())
            self.assertEqual(1, len(logmsgs))
            self.assertEqual(logmsgs[0],
                             'Unrecognized option in message: UnrecognizedOption<3>: 626f677573')
        finally:
            lh.detach()


class TestMessageEndpoints (unittest.TestCase):
    def testBasic(self):
        ep1 = Endpoint(host='ep1', family=None)
        ep2 = Endpoint(host='ep2', family=None)
        m = Message()
        self.assertTrue(m.source_endpoint is None)
        self.assertTrue(m.destination_endpoint is None)
        m.source_endpoint = ep1
        self.assertTrue(m.source_endpoint is ep1)
        self.assertTrue(m.destination_endpoint is None)
        m.destination_endpoint = ep2
        self.assertTrue(m.source_endpoint is ep1)
        self.assertTrue(m.destination_endpoint is ep2)
        # OK to re-assign same value
        m.source_endpoint = ep1
        m.destination_endpoint = ep2
        # Not ok to assign different value or remove value
        with self.assertRaises(TypeError):
            m.source_endpoint = None
        with self.assertRaises(ValueError):
            m.source_endpoint = ep2
        with self.assertRaises(TypeError):
            m.destination_endpoint = None
        with self.assertRaises(ValueError):
            m.destination_endpoint = ep1


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
        m = Message(confirmable=True, token=b'123', messageID=0x1234, code=Request.GET)
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
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(b'\x42\x00\x00\x00')
        self.assertEqual(cm.exception.args[0], MessageFormatError.EMPTY_MESSAGE_NOT_EMPTY)
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(b'\x40\x00\x00\x00\x01')
        self.assertEqual(cm.exception.args[0], MessageFormatError.EMPTY_MESSAGE_NOT_EMPTY)

    def testInvalid(self):
        self.assertRaises(TypeError, Message.from_packed, 'text')
        m = Message.from_packed(b'\x80')
        self.assertTrue(m is None)
        packed = b'\x53\x01\x12\x34123\xF0'
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(packed)
        self.assertEqual(cm.exception.args[0], MessageFormatError.INVALID_OPTION)
        self.assertEqual(cm.exception.args[1]['type'], Message.Type_NON)
        packed = b'\x63\x01\x12\x34123\xF0'
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(packed)
        self.assertEqual(cm.exception.args[0], MessageFormatError.INVALID_OPTION)
        self.assertEqual(cm.exception.args[1]['type'], Message.Type_ACK)
        packed = b'\x43\x01\x12\x34123\xFF'
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(packed)
        self.assertEqual(cm.exception.args[0], MessageFormatError.ZERO_LENGTH_PAYLOAD)
        packed = b'\x49\x01\x12\x34'
        with self.assertRaises(MessageFormatError) as cm:
            Message.from_packed(packed)
        self.assertEqual(cm.exception.args[0], MessageFormatError.TOKEN_TOO_LONG)

    def testUnrecognizedCodes(self):
        m = Message.from_packed(b'\x40\x8A\x12\x34')
        self.assertEqual((4, 10), m.code)
        self.assertTrue(isinstance(m, ClientErrorResponse))
        self.assertEqual(0x1234, m.messageID)

        m = Message.from_packed(b'\x40\x6A\x12\x34')
        self.assertEqual((3, 10), m.code)
        self.assertTrue(isinstance(m, Class3Response))
        self.assertEqual(0x1234, m.messageID)

        with self.assertRaises(MessageFormatError) as cm:
            m = Message.from_packed(b'\x40\x2A\x12\x34')
        self.assertEqual(cm.exception.args[0], MessageFormatError.UNRECOGNIZED_CODE_CLASS)
        self.assertEqual(cm.exception.args[1]['type'], Message.Type_CON)
        self.assertEqual(cm.exception.args[1]['code'], (1, 10))
        self.assertEqual(cm.exception.args[1]['messageID'], 0x1234)

    def testLibCoapRoot(self):
        p = b'\x60\x45\xd4\x48\xc0\x23\x02\xff\xff\xff' + b'This is a test server'
        m = Message.from_packed(p)
        self.assertEqual(unicode(m), '''[54344] ACK 2.05 (Content)
Option Content-Format: 0
Option Max-Age: 196607
Payload: This is a test server''')


class TestMessageIDCache (unittest.TestCase):

    def testDictionary(self):
        c = MessageIDCache()
        self.assertEqual(0, len(c))
        with self.assertRaises(KeyError):
            v = c[1]
        now = coapy.clock()
        e1 = MessageIDCacheEntry(message_id=1, time_due=now+5)
        e2 = MessageIDCacheEntry(message_id=2, time_due=now)
        e3 = MessageIDCacheEntry(message_id=3, time_due=now+2)
        c.add(e1)
        c.add(e2)
        c.add(e3)
        self.assertEqual(3, len(c))
        self.assertTrue(c[1] is e1)
        self.assertTrue(c[2] is e2)
        self.assertTrue(c[3] is e3)
        self.assertTrue(c.peek_oldest() is e2)
        self.assertTrue(c.pop_oldest() is e2)
        self.assertEqual(2, len(c))
        self.assertTrue(c[1] is e1)
        with self.assertRaises(KeyError):
            v = c[2]
        self.assertTrue(c[3] is e3)
        self.assertTrue(c.peek_oldest() is e3)
        e1b = MessageIDCacheEntry(message_id=1, time_due=now-5)
        c[e1b.message_id] = e1b
        self.assertEqual(2, len(c))
        self.assertTrue(c[1] is e1b)
        self.assertTrue(c[3] is e3)
        self.assertTrue(c.peek_oldest() is e1b)


if __name__ == '__main__':
    unittest.main()
