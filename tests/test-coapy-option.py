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


class Test (unittest.TestCase):
    def testClasses(self):
        self.assertEqual(IfMatch.number, 1)
        self.assertEqual(IfMatch.format, UrOption.opaque)
        self.assertEqual(UriHost.number, 3)
        self.assertEqual(UriHost.format, UrOption.string)
        with self.assertRaises(AttributeError):
            IfMatch.number = 2

    def testInstances(self):
        im = IfMatch()
        self.assertEqual(im.number, 1)
        self.assertEqual(im.format, UrOption.opaque)
        with self.assertRaises(AttributeError):
            im.number = 2
        uh = UriHost()
        self.assertEqual(uh.number, 3)
        self.assertEqual(uh.format, UrOption.string)

    def testRegistry(self):
        with self.assertRaises(OptionRegistryConflict):
            class ConflictingOption(UrOption):
                number = IfMatch.number
                format = UrOption.string

    def testDeclaration(self):
        with self.assertRaises(InvalidOptionType):
            class MissingFormatOption(UrOption):
                number = IfMatch.number
        with self.assertRaises(InvalidOptionType):
            class MissingNumberOption(UrOption):
                number = IfMatch.number
        with self.assertRaises(InvalidOptionType):
            class MissingBothOption(UrOption):
                pass

    def testFindOption(self):
        self.assertEqual(IfMatch, find_option(IfMatch.number))
        self.assertTrue(find_option(-3) is None)


if __name__ == '__main__':
    unittest.main()
