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
from coapy.resource import *


class TestLinkValue(unittest.TestCase):

    def testDQUOTED(self):
        self.assertIsNone(LinkValue._DQUOTED_re.match('token'))
        mo = LinkValue._DQUOTED_re.match('"quoted"')
        self.assertEqual('quoted', mo.group('text'))
        mo = LinkValue._DQUOTED_re.match(r'"\t\r"')
        self.assertEqual(r'\t\r', mo.group('text'))
        mo = LinkValue._DQUOTED_re.match(r'"one\"two"')
        self.assertEqual(r'one\"two', mo.group('text'))

    def testPTOKEN(self):
        self.assertTrue(LinkValue._PTOKEN_re.match('token'))
        self.assertFalse(LinkValue._PTOKEN_re.match('"quoted"'))
        self.assertFalse(LinkValue._PTOKEN_re.match('with spaces'))
        self.assertFalse(LinkValue._PTOKEN_re.match('token,comma'))
        self.assertFalse(LinkValue._PTOKEN_re.match('token;semic'))

    def testConstructor(self):
        lf = LinkValue('/path', {'title': 'something'})
        self.assertEqual(lf.target_uri, '/path')
        self.assertEqual(1, len(lf.params))
        self.assertEqual('something', lf.params['title'])

    def testWellKnown(self):
        lvs = LinkValue.from_link_format('</>;title="General Info";ct=0,</time>;if="clock";rt="Ticks";title="Quote\\"Clock";ct=0;obs,</async>;ct=0')  # nopep8
        self.assertEqual(3, len(lvs))
        lv = lvs.pop(0)
        self.assertEqual('/', lv.target_uri)
        self.assertEqual(2, len(lv.params))
        self.assertEqual('General Info', lv.params['title'])
        self.assertEqual('0', lv.params['ct'])
        lv = lvs.pop(0)
        self.assertEqual('/time', lv.target_uri)
        self.assertEqual(5, len(lv.params))
        self.assertEqual('Ticks', lv.params['rt'])
        self.assertEqual(r'Quote\"Clock', lv.params['title'])
        self.assertEqual('0', lv.params['ct'])
        self.assertIsNone(lv.params['obs'])
        lv = lvs.pop(0)
        self.assertEqual('/async', lv.target_uri)
        self.assertEqual(1, len(lv.params))

    def testToLinkFormat(self):
        lv = LinkValue('/path', {})
        self.assertEqual('</path>', lv.to_link_format())
        lv = LinkValue('/path', {'tok': 'value'})
        self.assertEqual('</path>;tok=value', lv.to_link_format())
        lv = LinkValue('/path', {'noval': None, 'quoted': 'with spaces', 'tok': 'token'})
        self.assertEqual('</path>;noval;quoted="with spaces";tok=token', lv.to_link_format())
        lv = LinkValue('/path', {'t': 'one"two'})
        self.assertEqual(r'</path>;t="one\"two"', lv.to_link_format())


if __name__ == '__main__':
    unittest.main()
