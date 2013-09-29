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
from coapy.util import *


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
        class B(object):
            __metaclass__ = ReadOnlyMeta
            Zero = ClassReadOnly(0)


if __name__ == '__main__':
    unittest.main()
