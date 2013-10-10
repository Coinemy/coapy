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
from coapy.endpoint import *
import coapy.option


class TestEndpoint (unittest.TestCase):
    def testBasic6(self):
        ep = Endpoint(host='2001:db8:0::2:1')
        self.assertEqual(b'\x20\x01\x0d\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x01',
                         ep.in_addr)
        self.assertEqual('[2001:db8::2:1]', ep.uri_host)
        self.assertEqual(5683, ep.port)
        ep2 = Endpoint(host='2001:db8:0::2:1')
        self.assertTrue(ep is ep2)
        ep2 = ep.get_peer_endpoint(('2001:db8:0::2:2', 1234))
        self.assertFalse(ep is ep2)
        self.assertEqual(b'\x20\x01\x0d\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x02',
                         ep2.in_addr)
        self.assertEqual(1234, ep2.port)
        self.assertEqual(ep.family, ep2.family)
        self.assertEqual(ep.security_mode, ep2.security_mode)
        ep3 = ep.get_peer_endpoint(host='2001:db8:0::2:2', port=1234)
        self.assertTrue(ep3 is ep2)

    def testBasic4(self):
        ep = Endpoint(host='10.0.1.2', port=1234)
        self.assertEqual(b'\x0a\x00\x01\x02', ep.in_addr)
        self.assertEqual('10.0.1.2', ep.uri_host)
        self.assertEqual(1234, ep.port)
        ep2 = Endpoint(host='10.0.1.2', port=1234)
        self.assertTrue(ep is ep2)
        ep2 = ep.get_peer_endpoint(('10.0.1.5', 52342))
        self.assertFalse(ep is ep2)
        self.assertEqual(b'\x0a\x00\x01\x05', ep2.in_addr)
        self.assertEqual('10.0.1.5', ep2.uri_host)
        self.assertEqual(52342, ep2.port)
        self.assertEqual(ep.family, ep2.family)
        self.assertEqual(ep.security_mode, ep2.security_mode)
        ep3 = ep.get_peer_endpoint(host=ep.uri_host)
        self.assertFalse(ep is ep3)
        self.assertEqual(ep.in_addr, ep3.in_addr)
        self.assertEqual(coapy.COAP_PORT, ep3.port)
        self.assertEqual(ep.family, ep3.family)
        self.assertEqual(ep.security_mode, ep3.security_mode)

    def testNotAnInetAddr(self):
        naa = 'not an address'
        with self.assertRaises(socket.gaierror) as cm:
            ep = Endpoint.lookup_endpoint(host=naa)
        ep = Endpoint.lookup_endpoint(host=naa, family=None)
        self.assertTrue(ep is None)
        with self.assertRaises(socket.gaierror) as cm:
            ep = Endpoint(host=naa)
        ep = Endpoint(host=naa, family=None)
        lep = Endpoint.lookup_endpoint(host=naa, family=None)
        self.assertTrue(lep is ep)
        ep2 = Endpoint(host=naa, family=None)
        self.assertTrue(ep is ep2)
        self.assertTrue(ep.family is None)
        self.assertEqual(ep.in_addr, naa.encode('utf-8'))
        self.assertEqual(ep.port, coapy.COAP_PORT)
        self.assertTrue(ep.security_mode is None)
        ana = 'another non-address'
        self.assertEqual((naa, coapy.COAP_PORT), ep.sockaddr)
        ep2 = ep.get_peer_endpoint((ana, 24))
        self.assertFalse(ep is ep2)
        self.assertEqual(ana, ep2.uri_host)
        self.assertEqual(24, ep2.port)
        self.assertEqual(ep.family, ep2.family)
        self.assertEqual(ep.security_mode, ep2.security_mode)

    def testUnspecFamily(self):
        ep = Endpoint.lookup_endpoint(('::1', 1234))
        ep = Endpoint(('::1', 1234))
        ep2 = Endpoint.lookup_endpoint(('::1', 1234))
        self.assertEqual(ep, ep2)
        ep = Endpoint.lookup_endpoint(('192.168.0.1', 1234))
        ep = Endpoint(('192.168.0.1', 1234))
        ep2 = Endpoint.lookup_endpoint(('192.168.0.1', 1234))
        self.assertEqual(ep, ep2)

    def testStringize(self):
        naa = 'not an address'
        ep = Endpoint(host=naa, family=None)
        self.assertEqual('not an address:5683', unicode(ep))
        ep = Endpoint(host='::1', port=1234)
        self.assertEqual('[::1]:1234', unicode(ep))
        ep = Endpoint(sockaddr=('192.168.0.1', 12345))
        self.assertEqual('192.168.0.1:12345', unicode(ep))

    def testIsSameHost(self):
        ep = Endpoint(host='127.0.0.1')
        self.assertEqual(ep.family, socket.AF_INET)
        ep2 = Endpoint(host='localhost')
        self.assertTrue(ep is ep2)
        self.assertTrue(ep.is_same_host('127.0.0.1'))
        self.assertFalse(ep.is_same_host('localhost'))

    def testFinalize(self):
        ep = Endpoint(host='localhost')
        m = ep.create_request('/path')
        m.options.append(coapy.option.UriHost(ep.uri_host))
        m.options.append(coapy.option.UriPort(ep.port))
        self.assertEqual(3, len(m.options))
        ep.finalize_message(m)
        self.assertEqual(1, len(m.options))
        opt = m.options[0]
        self.assertTrue(isinstance(opt, coapy.option.UriPath))
        self.assertTrue(m.destination_endpoint is ep)

    def testReset(self):
        ep = Endpoint.create_bound_endpoint(host='127.0.0.1', port=0)
        self.assertFalse(ep.bound_socket is None)
        ep._reset()
        self.assertTrue(ep.bound_socket is None)


class TestURLParse (unittest.TestCase):
    def testJoin(self):
        ep = Endpoint(host='::1')
        self.assertEqual('coap://[::1]/', ep.base_uri)
        base = ep.uri_from_options([])
        self.assertEqual('coap://[::1]/', base)
        self.assertEqual('coap://[::1]/path', urlparse.urljoin(base, '/path'))
        self.assertEqual('coap://[::1]/other', urlparse.urljoin(base + 'path/', '../other'))


class TestURLConversion (unittest.TestCase):
    def testB1(self):
        ep = Endpoint(host='2001:db8::2:1')
        url = 'coap://[2001:db8::2:1]/'
        opts = ep.uri_to_options(url)
        self.assertEqual(0, len(opts))
        durl = ep.uri_from_options(opts)
        self.assertEqual(url, durl)

    def testB2(self):
        ep = Endpoint(host='2001:db8::2:1')
        url = 'coap://example.net/'
        opts = ep.uri_to_options(url)
        self.assertEqual(1, len(opts))
        opt = opts[0]
        self.assertTrue(isinstance(opt, coapy.option.UriHost))
        self.assertEqual('example.net', opt.value)
        durl = ep.uri_from_options(opts)
        self.assertEqual(url, durl)

    def testB3(self):
        ep = Endpoint(host='2001:db8::2:1')
        url = 'coap://example.net/.well-known/core'
        opts = ep.uri_to_options(url)
        self.assertEqual(3, len(opts))
        opt = opts[0]
        self.assertTrue(isinstance(opt, coapy.option.UriHost))
        self.assertEqual('example.net', opt.value)
        opt = opts[1]
        self.assertTrue(isinstance(opt, coapy.option.UriPath))
        self.assertEqual('.well-known', opt.value)
        opt = opts[2]
        self.assertTrue(isinstance(opt, coapy.option.UriPath))
        self.assertEqual('core', opt.value)
        durl = ep.uri_from_options(opts)
        self.assertEqual(url, durl)

    def testB4(self):
        ep = Endpoint(host='2001:db8::2:1')
        url = 'coap://xn--18j4d.example/%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF'
        opts = ep.uri_to_options(url)
        self.assertEqual(2, len(opts))
        opt = opts[0]
        self.assertTrue(isinstance(opt, coapy.option.UriHost))
        self.assertEqual('xn--18j4d.example', opt.value)
        opt = opts[1]
        self.assertTrue(isinstance(opt, coapy.option.UriPath))
        self.assertEqual('こんにちは', opt.value)
        durl = ep.uri_from_options(opts)
        self.assertEqual(url, durl)

    def testB5(self):
        ep = Endpoint(host='198.51.100.1', port=61616)
        opts = (coapy.option.UriPath(''),
                coapy.option.UriPath('/'),
                coapy.option.UriPath(''),
                coapy.option.UriPath(''),
                coapy.option.UriQuery('//'),
                coapy.option.UriQuery('?&'))
        uri = ep.uri_from_options(opts)
        self.assertEqual('coap://198.51.100.1:61616//%2F//?%2F%2F&?%26', uri)
        uopts = ep.uri_to_options(uri)
        self.assertEqual(len(opts), len(uopts))
        for i in xrange(len(opts)):
            self.assertEqual(type(opts[i]), type(uopts[i]))
            self.assertEqual(opts[i].value, uopts[i].value)

    def testBasic(self):
        ep = Endpoint(host='::1')
        rel = '/.well-known/core'
        opts = ep.uri_to_options(rel)
        self.assertTrue(isinstance(opts, list))
        self.assertEqual(2, len(opts))
        opt = opts[0]
        self.assertTrue(isinstance(opt, coapy.option.UriPath))
        self.assertEqual('.well-known', opt.value)
        opt = opts[1]
        self.assertTrue(isinstance(opt, coapy.option.UriPath))
        self.assertEqual('core', opt.value)

    def testInvalidToOpts(self):
        ep = Endpoint(host='::1')
        with self.assertRaises(URIError) as cm:
            ep.uri_to_options('http://localhost/path')
        self.assertEqual(cm.exception.args[0], 'invalid scheme')
        self.assertEqual(cm.exception.args[1], 'http')

    def testInvalidFromOpts(self):
        ep = Endpoint(host='::1')
        with self.assertRaises(URIError) as cm:
            ep.uri_from_options([coapy.option.UriHost()])
        self.assertEqual(cm.exception.args[0], 'empty Uri-Host')
        with self.assertRaises(URIError) as cm:
            ep.uri_from_options([coapy.option.UriPort()])
        self.assertEqual(cm.exception.args[0], 'empty Uri-Port')


class TestEndpointInterface (unittest.TestCase):
    def testNextMessageID(self):
        ep = Endpoint(host='::1')
        ep._reset_next_messageID(621)
        self.assertEqual(621, ep.next_messageID())
        self.assertEqual(622, ep.next_messageID())
        self.assertEqual(623, ep.next_messageID())
        ep._reset_next_messageID(65534)
        self.assertEqual(65534, ep.next_messageID())
        self.assertEqual(65535, ep.next_messageID())
        self.assertEqual(0, ep.next_messageID())
        self.assertEqual(1, ep.next_messageID())

    def testCreateRequest(self):
        ep = Endpoint(host='::1')
        m = ep.create_request('/path')
        self.assertTrue(isinstance(m, coapy.message.Request))
        self.assertEqual(coapy.message.Request.GET, m.code)
        self.assertTrue(m.destination_endpoint is ep)
        self.assertFalse(m.messageID is None)
        self.assertEqual(m.token, b'')
        opts = m.options
        self.assertTrue(isinstance(opts, list))
        self.assertEqual(1, len(opts))
        opt = opts[0]
        self.assertTrue(isinstance(opt, coapy.option.UriPath))
        self.assertEqual('path', opt.value)
        self.assertTrue(m.payload is None)


class TestBoundEndpoints (unittest.TestCase):
    def testBasic(self):
        localhost = '127.0.0.1'
        ep = Endpoint.create_bound_endpoint(host=localhost, port=0)
        self.assertEqual(socket.AF_INET, ep.family)
        self.assertNotEqual(0, ep.port)
        self.assertFalse(ep.bound_socket is None)
        self.assertEqual(ep.sockaddr, ep.bound_socket.getsockname())
        ep2 = Endpoint(host=localhost)
        self.assertTrue(ep2.bound_socket is None)
        self.assertFalse(ep is ep2)
        s = socket.socket(ep.family, socket.SOCK_DGRAM)
        with self.assertRaises(ValueError):
            ep.set_bound_socket(s)
        s.close()
        s = ep.bound_socket
        obs = ep.set_bound_socket(None)
        self.assertTrue(s is obs)
        self.assertTrue(ep.bound_socket is None)
        obs = ep.set_bound_socket(s)
        self.assertTrue(obs is None)
        self.assertTrue(s is ep.bound_socket)


class TestSocketSendRecv (unittest.TestCase):
    def testBasic(self):
        import socket
        import errno
        ep1 = Endpoint.create_bound_endpoint(host='localhost', port=0)
        ep1.bound_socket.setblocking(0)
        with self.assertRaises(socket.error) as cm:
            (data, sep) = ep1.rawrecvfrom(2048)
        e = cm.exception
        self.assertEqual(e.args[0], errno.EAGAIN)
        self.assertEqual(e.args[1], 'Resource temporarily unavailable')
        s1 = ep1.set_bound_socket(None)
        s1.close()


class TestMessageCache (unittest.TestCase):

    def testDictionary(self):
        c = MessageCache()
        self.assertEqual(0, len(c))
        with self.assertRaises(KeyError):
            v = c[1]
        now = coapy.clock()
        e1 = MessageCacheEntry(cache=c, message_id=1, time_due=now+5)
        e2 = MessageCacheEntry(cache=c, message_id=2, time_due=now)
        e3 = MessageCacheEntry(cache=c, message_id=3, time_due=now+2)
        self.assertEqual(3, len(c))
        self.assertTrue(c[1] is e1)
        self.assertTrue(c[2] is e2)
        self.assertTrue(c[3] is e3)

        self.assertTrue(c.peek_oldest() is e2)
        self.assertTrue(e2.cache is c)
        self.assertTrue(c.pop_oldest() is e2)
        self.assertTrue(e2.cache is None)
        self.assertEqual(2, len(c))

        self.assertTrue(c[1] is e1)
        with self.assertRaises(KeyError):
            v = c[2]
        self.assertTrue(c[3] is e3)

        self.assertTrue(c.peek_oldest() is e3)
        e1.time_due = e3.time_due - 1
        self.assertTrue(c.peek_oldest() is e1)

        self.assertTrue(c[1] is e1)
        self.assertTrue(c[3] is e3)
        self.assertEqual(2, len(c))

        rv = c._remove(e1)
        self.assertTrue(rv is e1)
        self.assertEqual(1, len(c))
        self.assertTrue(c[3] is e3)
        self.assertTrue(e3.cache is c)

        c.clear()
        self.assertTrue(e3.cache is None)
        self.assertEqual(0, len(c))


if __name__ == '__main__':
    unittest.main()
