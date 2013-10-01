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
from coapy.util import *


class TestCoAPy (unittest.TestCase):
    def testConstants(self):
        self.assertEqual(5683, coapy.COAP_PORT)


class TestReadOnlyMeta (unittest.TestCase):

    @staticmethod
    def setZero(obj, value):
        obj.Zero = value

    def testBasic(self):
        class C(object):
            __metaclass__ = ReadOnlyMeta
            Zero = ClassReadOnly(0)

        self.assertEqual(0, C.Zero)
        i = C()
        self.assertEqual(0, i.Zero)
        self.assertRaises(AttributeError, self.setZero, i, 3)
        self.assertRaises(AttributeError, self.setZero, C, 3)

    def testInheritance(self):
        class C (object):
            __metaclass__ = ReadOnlyMeta
            Zero = ClassReadOnly(0)

        class S1 (C):
            # Weirdness:  This creates a new attribute but it's
            # not visible at the class level, only at instances of
            # the class
            Zero = 1

        class S2 (C):
            One = ClassReadOnly(1)

        self.assertEqual(0, C.Zero)
        self.assertEqual(0, S1.Zero)
        self.assertEqual(0, S2.Zero)
        self.assertEqual(1, S2.One)
        c = C()
        s1 = S1()
        s2 = S2()
        self.assertEqual(0, c.Zero)
        self.assertEqual(1, s1.Zero)
        self.assertEqual(0, s2.Zero)
        self.assertEqual(1, s2.One)
        self.assertRaises(AttributeError, self.setZero, C, 3)
        self.assertRaises(AttributeError, self.setZero, S1, 3)
        self.assertRaises(AttributeError, self.setZero, S2, 3)
        self.assertRaises(AttributeError, self.setZero, c, 3)
        # Oddly, this works:
        s1.Zero = 3
        self.assertEqual(0, S1.Zero)
        self.assertEqual(3, s1.Zero)
        self.assertRaises(AttributeError, self.setZero, s2, 3)


class TestNetUnicode (unittest.TestCase):

    def testBasic(self):
        import urllib

        path = 'こんにちは'
        path_nu = to_net_unicode(path)
        self.assertEqual('%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF',
                         urllib.quote(path_nu))
        dpath_nu = urllib.unquote(bytes(urllib.quote(path_nu)))
        self.assertEqual(path_nu, dpath_nu)
        dpath = path_nu.decode('utf-8')
        self.assertEqual(path, dpath)


if __name__ == '__main__':
    unittest.main()
