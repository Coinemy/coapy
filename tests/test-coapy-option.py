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
from coapy.option import *


class TestOptionInfrastructure (unittest.TestCase):
    def testClasses(self):
        self.assertEqual(IfMatch.number, 1)
        self.assertTrue(isinstance(IfMatch.format, UrOption.opaque))
        self.assertEqual(UriHost.number, 3)
        self.assertTrue(isinstance(UriHost.format, UrOption.string))
        with self.assertRaises(AttributeError):
            IfMatch.number = 2
        with self.assertRaises(AttributeError):
            IfMatch.format = UrOption.empty

    def testInstances(self):
        im = IfMatch()
        self.assertEqual(im.number, 1)
        self.assertTrue(isinstance(im.format, UrOption.opaque))
        with self.assertRaises(AttributeError):
            im.number = 2
        with self.assertRaises(AttributeError):
            im.format = UrOption.empty
        uh = UriHost()
        self.assertEqual(uh.number, 3)
        self.assertTrue(isinstance(uh.format, UrOption.string))

    def testRegistry(self):
        with self.assertRaises(OptionRegistryConflictError):
            class ConflictingOption(UrOption):
                number = IfMatch.number
                format = UrOption.string(100)

    def testDeclaration(self):
        with self.assertRaises(InvalidOptionTypeError):
            class MissingFormatOption(UrOption):
                number = IfMatch.number
        with self.assertRaises(InvalidOptionTypeError):
            class MissingNumberOption(UrOption):
                number = IfMatch.number
        with self.assertRaises(InvalidOptionTypeError):
            class MissingBothOption(UrOption):
                pass

    def testFindOption(self):
        self.assertEqual(IfMatch, find_option(IfMatch.number))
        self.assertTrue(find_option(-3) is None)

    def testUnknownOption(self):
        with self.assertRaises(ValueError):
            instance = UnknownOption(IfMatch.number)
        with self.assertRaises(ValueError):
            instance = UnknownOption(65536)
        instance = UnknownOption(1234)
        self.assertEqual(1234, instance.number)
        with self.assertRaises(AttributeError):
            instance.number = 4321


class TestOptionConformance (unittest.TestCase):
    def testIfMatch(self):
        opt = IfMatch()
        self.assertEqual(1, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertFalse(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertTrue(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.opaque))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(8, opt.format.max_length)

    def testUriHost(self):
        opt = UriHost()
        self.assertEqual(3, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertTrue(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.string))
        self.assertEqual(1, opt.format.min_length)
        self.assertEqual(255, opt.format.max_length)

    def testETag(self):
        opt = ETag()
        self.assertEqual(4, opt.number)
        self.assertFalse(opt.is_critical())
        self.assertFalse(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertTrue(opt.valid_multiple_in_request())
        self.assertTrue(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.opaque))
        self.assertEqual(1, opt.format.min_length)
        self.assertEqual(8, opt.format.max_length)

    def testIfNoneMatch(self):
        opt = IfNoneMatch()
        self.assertEqual(5, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertFalse(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.empty))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(0, opt.format.max_length)

    def testUriPort(self):
        opt = UriPort()
        self.assertEqual(7, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertTrue(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.uint))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(2, opt.format.max_length)

    def testLocationPath(self):
        opt = LocationPath()
        self.assertEqual(8, opt.number)
        self.assertFalse(opt.is_critical())
        self.assertFalse(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertFalse(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertTrue(opt.valid_in_response())
        self.assertTrue(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.string))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(255, opt.format.max_length)

    def testUriPath(self):
        opt = UriPath()
        self.assertEqual(11, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertTrue(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertTrue(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.string))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(255, opt.format.max_length)

    def testContentFormat(self):
        opt = ContentFormat()
        self.assertEqual(12, opt.number)
        self.assertFalse(opt.is_critical())
        self.assertFalse(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertTrue(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.uint))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(2, opt.format.max_length)

    def testMaxAge(self):
        opt = MaxAge()
        self.assertEqual(14, opt.number)
        self.assertFalse(opt.is_critical())
        self.assertTrue(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertFalse(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertTrue(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.uint))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(4, opt.format.max_length)

    def testUriQuery(self):
        opt = UriQuery()
        self.assertEqual(15, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertTrue(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertTrue(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.string))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(255, opt.format.max_length)

    def testAccept(self):
        opt = Accept()
        self.assertEqual(17, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertFalse(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.uint))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(2, opt.format.max_length)

    def testLocationQuery(self):
        opt = LocationQuery()
        self.assertEqual(20, opt.number)
        self.assertFalse(opt.is_critical())
        self.assertFalse(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertFalse(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertTrue(opt.valid_in_response())
        self.assertTrue(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.string))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(255, opt.format.max_length)

    def testProxyUri(self):
        opt = ProxyUri()
        self.assertEqual(35, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertTrue(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.string))
        self.assertEqual(1, opt.format.min_length)
        self.assertEqual(1034, opt.format.max_length)

    def testProxyUri(self):
        opt = ProxyUri()
        self.assertEqual(35, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertTrue(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.string))
        self.assertEqual(1, opt.format.min_length)
        self.assertEqual(1034, opt.format.max_length)

    def testProxyScheme(self):
        opt = ProxyScheme()
        self.assertEqual(39, opt.number)
        self.assertTrue(opt.is_critical())
        self.assertTrue(opt.is_unsafe())
        self.assertFalse(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertFalse(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.string))
        self.assertEqual(1, opt.format.min_length)
        self.assertEqual(255, opt.format.max_length)

    def testSize1(self):
        opt = Size1()
        self.assertEqual(60, opt.number)
        self.assertFalse(opt.is_critical())
        self.assertFalse(opt.is_unsafe())
        self.assertTrue(opt.is_no_cache_key())
        self.assertTrue(opt.valid_in_request())
        self.assertFalse(opt.valid_multiple_in_request())
        self.assertTrue(opt.valid_in_response())
        self.assertFalse(opt.valid_multiple_in_response())
        self.assertTrue(isinstance(opt.format, opt.uint))
        self.assertEqual(0, opt.format.min_length)
        self.assertEqual(4, opt.format.max_length)


class TestEmptyFormat (unittest.TestCase):
    @staticmethod
    def setValue(instance, value):
        instance.value = value

    def testPack(self):
        empty = UrOption.empty()
        self.assertEqual(empty.min_length, 0)
        self.assertEqual(empty.max_length, 0)
        self.assertEqual(b'', empty.to_packed(None))
        self.assertRaises(ValueError, empty.to_packed, 0)

    def testUnpack(self):
        empty = UrOption.empty()
        self.assertEqual(None, empty.from_packed(b''))
        self.assertRaises(ValueError, empty.from_packed, b'\x00')

    def testOptionValues(self):
        opt = IfNoneMatch()
        self.assertTrue(opt.value is None)
        opt.value = None
        self.assertRaises(ValueError, self.setValue, opt, 0)


class TestUintFormat (unittest.TestCase):
    @staticmethod
    def setValue(instance, value):
        instance.value = value

    def testPack(self):
        uint = UrOption.uint(4)
        self.assertEqual(uint.min_length, 0)
        self.assertEqual(uint.max_length, 4)
        self.assertEqual(b'', uint.to_packed(0))
        self.assertEqual(b'\x01', uint.to_packed(1))
        self.assertEqual(b'\x01\x02', uint.to_packed(0x102))
        self.assertEqual(b'\x01\x02\x03', uint.to_packed(0x10203))
        self.assertEqual(b'\x01\x02\x03\x04', uint.to_packed(0x1020304))
        self.assertRaises(OptionValueLengthError, uint.to_packed, 0x102030405)

    def testUnpack(self):
        uint = UrOption.uint(4)
        self.assertEqual(0, uint.from_packed(b''))
        self.assertEqual(0, uint.from_packed(b'\x00'))
        self.assertEqual(0, uint.from_packed(b'\x00\x00'))
        self.assertEqual(0, uint.from_packed(b'\x00\x00\x00'))
        self.assertEqual(0, uint.from_packed(b'\x00\x00\x00\x00'))
        self.assertRaises(OptionValueLengthError, uint.from_packed, b'\x00\x00\x00\x00\x00')
        self.assertEqual(1, uint.from_packed(b'\x01'))
        self.assertEqual(1, uint.from_packed(b'\x00\x01'))
        self.assertEqual(1, uint.from_packed(b'\x00\x00\x01'))
        self.assertEqual(1, uint.from_packed(b'\x00\x00\x00\x01'))
        self.assertEqual(0x0102, uint.from_packed(b'\x01\x02'))
        self.assertEqual(0x0102, uint.from_packed(b'\x00\x01\x02'))
        self.assertEqual(0x0102, uint.from_packed(b'\x00\x00\x01\x02'))
        self.assertEqual(0x010203, uint.from_packed(b'\x01\x02\x03'))
        self.assertEqual(0x010203, uint.from_packed(b'\x00\x01\x02\x03'))
        self.assertEqual(0x01020304, uint.from_packed(b'\x01\x02\x03\x04'))
        self.assertRaises(OptionValueLengthError, uint.from_packed, b'\x01\x02\x03\x04\x05')

    def testOptionValues(self):
        opt = UriPort()
        self.assertTrue(opt.value is None)
        self.assertRaises(ValueError, self.setValue, opt, None)
        opt.value = 3
        self.assertEqual(3, opt.value)
        self.assertRaises(OptionValueLengthError, self.setValue, opt, 65536)


class TestOpaqueFormat (unittest.TestCase):
    @staticmethod
    def setValue(instance, value):
        instance.value = value

    def testPackUnpack(self):
        opaque = UrOption.opaque(4, min_length=1)
        for v in (b'\x01', b'\x01\x02', b'\x01\x02\x03', b'\x01\x02\x03\x04'):
            self.assertEqual(v, opaque.to_packed(v))
            self.assertEqual(v, opaque.from_packed(v))
        for v in (b'', b'\x01\x02\x03\x04\x05'):
            self.assertRaises(OptionValueLengthError, opaque.from_packed, v)
            self.assertRaises(OptionValueLengthError, opaque.to_packed, v)

    def testOptionValues(self):
        opt = ETag()
        self.assertTrue(opt.value is None)
        self.assertRaises(ValueError, self.setValue, opt, 0)
        self.assertRaises(OptionValueLengthError, self.setValue, opt, b'')
        opt.value = b'1234'
        self.assertEqual(b'1234', opt.value)


class TestStringFormat (unittest.TestCase):
    @staticmethod
    def setValue(instance, value):
        instance.value = value

    def testPack(self):
        string = UrOption.string(8, min_length=1)
        self.assertEqual(1, string.min_length)
        self.assertEqual(8, string.max_length)
        ustr = u'Trélat'
        self.assertEqual(6, len(ustr))
        pstr = b'Tr\xc3\xa9lat'
        self.assertEqual(7, len(pstr))
        self.assertEqual(ustr, pstr.decode('utf-8'))
        self.assertEqual(pstr, ustr.encode('utf-8'))
        self.assertEqual(pstr, string.to_packed(ustr))
        self.assertRaises(OptionValueLengthError, string.to_packed, u'')
        self.assertRaises(OptionValueLengthError, string.to_packed, u'123456789')

    def testPack2(self):
        string = UrOption.string(6)
        self.assertEqual(0, string.min_length)
        self.assertEqual(6, string.max_length)
        ustr = u'Trélat'
        ustr2 = u'Trelat'
        self.assertEqual(6, len(ustr))
        self.assertEqual(6, len(ustr2))
        pstr = ustr.encode('utf-8')
        self.assertEqual(7, len(pstr))
        pstr = ustr2.encode('utf-8')
        self.assertEqual(6, len(pstr))
        self.assertRaises(OptionValueLengthError, string.to_packed, ustr)
        self.assertEqual(pstr, string.to_packed(ustr2))

    def testUnpack(self):
        string = UrOption.string(8, min_length=1)
        self.assertEqual(u'Trélat', string.from_packed(b'Tr\xc3\xa9lat'))
        self.assertRaises(OptionValueLengthError, string.from_packed, b'')
        self.assertRaises(OptionValueLengthError, string.from_packed, b'123456789')

    def testOptionValues(self):
        opt = UriHost()
        self.assertTrue(opt.value is None)
        self.assertRaises(ValueError, self.setValue, opt, b'1234')
        self.assertRaises(OptionValueLengthError, self.setValue, opt, u'')
        opt.value = u'localhost'
        self.assertEqual(opt.value, u'localhost')

if __name__ == '__main__':
    unittest.main()
