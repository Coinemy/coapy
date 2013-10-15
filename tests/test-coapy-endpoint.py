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
from tests.support import *
import coapy.option
import urlparse


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
        ep = SocketEndpoint.create_bound_endpoint(host='127.0.0.1', port=0)
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
        ep = SocketEndpoint.create_bound_endpoint(host=localhost, port=0)
        self.assertEqual(socket.AF_INET, ep.family)
        self.assertNotEqual(0, ep.port)
        self.assertFalse(ep.bound_socket is None)
        self.assertEqual(ep.sockaddr, ep.bound_socket.getsockname())
        ep2 = Endpoint(host=localhost)
        self.assertFalse(isinstance(ep2, SocketEndpoint))
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
        ep1 = SocketEndpoint.create_bound_endpoint(host='localhost', port=0)
        ep1.bound_socket.setblocking(0)
        with self.assertRaises(socket.error) as cm:
            (data, sep) = ep1.rawrecvfrom(2048)
        e = cm.exception
        self.assertEqual(e.args[0], errno.EAGAIN)
        self.assertEqual(e.args[1], 'Resource temporarily unavailable')
        s1 = ep1.set_bound_socket(None)
        s1.close()


class TestMessageCache (ManagedClock_mixin,
                        unittest.TestCase):

    def testDictionary(self):
        from coapy.message import Message
        ep = Endpoint(host='localhost')
        c = MessageCache(ep, True)
        self.assertEqual(0, len(c))
        with self.assertRaises(KeyError):
            v = c[1]
        now = coapy.clock()
        e1 = MessageCacheEntry(cache=c, message=Message(messageID=1))
        self.assertTrue(e1.message.is_non_confirmable())
        self.assertEqual(e1.message.messageID, 1)
        self.assertEqual(e1.message_id, 1)
        self.assertEqual(e1.created_clk, now)
        self.assertEqual(e1.time_due, now + coapy.transmissionParameters.NON_LIFETIME)
        e2 = MessageCacheEntry(cache=c, message=Message(messageID=2), time_due_offset=0)
        self.assertTrue(e2.message.is_non_confirmable())
        self.assertEqual(e2.message.messageID, 2)
        self.assertEqual(e2.message_id, 2)
        self.assertEqual(e2.created_clk, now)
        self.assertEqual(e2.time_due, now)
        e3 = MessageCacheEntry(cache=c, message=Message(messageID=3, confirmable=True))
        self.assertTrue(e3.message.is_confirmable())
        self.assertEqual(e3.message.messageID, 3)
        self.assertEqual(e3.message_id, 3)
        self.assertEqual(e1.created_clk, now)
        self.assertEqual(e3.time_due, now + coapy.transmissionParameters.EXCHANGE_LIFETIME)
        self.assertEqual(3, len(c))
        queue = c.queue()
        self.assertTrue(queue[0] is e2)
        self.assertTrue(queue[1] is e1)
        self.assertTrue(queue[2] is e3)
        self.assertTrue(c[1] is e1)
        self.assertTrue(c[2] is e2)
        self.assertTrue(c[3] is e3)

        e1.time_due = now + 5
        e2.time_due = now
        e3.time_due = now + 2
        self.assertEqual(3, len(c))
        self.assertTrue(c[1] is e1)
        self.assertTrue(c[2] is e2)
        self.assertTrue(c[3] is e3)

        self.assertTrue(queue[0] is e2)
        self.assertTrue(e2.cache is c)
        c._remove(e2)
        self.assertTrue(e2.cache is None)
        self.assertEqual(2, len(c))

        self.assertTrue(c[1] is e1)
        with self.assertRaises(KeyError):
            v = c[2]
        self.assertTrue(c[3] is e3)

        self.assertTrue(queue[0] is e3)
        e1.time_due = e3.time_due - 1
        self.assertTrue(queue[0] is e1)

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


class TestSentCache (DeterministicBEBO_mixin,
                     LogHandler_mixin,
                     ManagedClock_mixin,
                     unittest.TestCase):

    def testCONNoAck(self):
        tp = coapy.transmissionParameters
        self.assertEqual(tp.ACK_RANDOM_FACTOR, 1.0)
        clk = coapy.clock
        sep = FIFOEndpoint()
        dep = FIFOEndpoint()
        self.assertEqual(0, clk())
        sm = dep.create_request('/path', confirmable=True, token=b'x')

        # Send the request through a full message layer.  In the
        # current model, this creates the cache entry and sets an
        # event due immediately but does not actually transmit
        # anything.
        ce = sep.send(sm)
        self.assertEqual(0, ce.transmissions)
        self.assertTrue(clk() >= ce.time_due)
        self.assertEqual(ce.ST_untransmitted, ce.state)

        # Process one timeout.  This should send the message and
        # start the BEBO process.
        rv = ce.process_timeout()
        self.assertTrue(rv is ce)
        self.assertTrue(ce.stale_at is None)
        self.assertEqual(ce.created_clk, 0)
        self.assertTrue(ce.message is sm)
        self.assertTrue(ce.destination_endpoint is dep)
        self.assertEqual(1, ce.transmissions)
        self.assertEqual(len(dep.fifo), ce.transmissions)

        # Cycle through the BEBO with ACK_TIMEOUT base interval
        to = tp.ACK_TIMEOUT
        for s in xrange(tp.MAX_RETRANSMIT):
            self.assertEqual(ce.time_due, clk() + to)
            clk.adjust(to)
            self.assertEqual(ce.ST_unacknowledged, ce.state)
            rv = ce.process_timeout()
            self.assertTrue(rv is ce)
            self.assertEqual(len(dep.fifo), ce.transmissions)
            to += to

        # At the end of the retransmissions, the clock should be at
        # MAX_TRANSMIT_WAIT.  The state should still be
        # unacknowledged, and there should be a timeout due through
        # which the caller may deal with the failure to receive an
        # ACK.
        clk.adjust(to)
        self.assertEqual(clk(), tp.MAX_TRANSMIT_WAIT)
        self.assertEqual(ce.ST_final_ack_wait, ce.state)
        self.assertEqual(ce.time_due, clk())

        # Now process the timeout, which simply moves the entry into
        # its completed state with a final timeout at which the entry
        # should be removed from the cache.
        rv = ce.process_timeout()
        self.assertTrue(rv is ce)
        self.assertEqual(ce.ST_completed, ce.state)
        self.assertEqual(ce.time_due, tp.EXCHANGE_LIFETIME)
        clk.adjust(ce.time_due - clk())

        # Finally, process the last timeout which removes the cache
        # entry.
        cache = ce.cache
        self.assertEqual(1, len(cache))
        rv = ce.process_timeout()
        self.assertTrue(rv is None)
        self.assertEqual(0, len(cache))
        self.assertTrue(ce.cache is None)

    def testNONNoAck(self):
        tp = coapy.transmissionParameters
        self.assertEqual(tp.ACK_RANDOM_FACTOR, 1.0)
        clk = coapy.clock
        sep = FIFOEndpoint()
        dep = FIFOEndpoint()
        self.assertEqual(0, clk())
        sm = dep.create_request('/path', confirmable=False, token=b'x')

        # Send the request through a full message layer.  In the
        # current model, this creates the cache entry and sets an
        # event due immediately but does not actually transmit
        # anything.
        ce = sep.send(sm)
        self.assertEqual(0, ce.transmissions)
        self.assertTrue(clk() >= ce.time_due)
        self.assertEqual(ce.ST_untransmitted, ce.state)

        # Process one timeout.  This should send the message and put it
        # into completed state.
        rv = ce.process_timeout()
        self.assertTrue(rv is ce)
        self.assertTrue(ce.stale_at is None)
        self.assertEqual(ce.created_clk, 0)
        self.assertTrue(ce.message is sm)
        self.assertTrue(ce.destination_endpoint is dep)
        self.assertEqual(1, ce.transmissions)
        self.assertEqual(len(dep.fifo), ce.transmissions)
        self.assertEqual(ce.ST_completed, ce.state)
        self.assertEqual(ce.time_due, tp.NON_LIFETIME)
        clk.adjust(ce.time_due - clk())

        # Finally, process the last timeout which removes the cache
        # entry.
        cache = ce.cache
        self.assertEqual(1, len(cache))
        rv = ce.process_timeout()
        self.assertTrue(rv is None)
        self.assertEqual(0, len(cache))
        self.assertTrue(ce.cache is None)

    def testCONReset(self):
        from coapy.message import Message, Request, ServerErrorResponse

        tp = coapy.transmissionParameters
        self.assertEqual(tp.ACK_RANDOM_FACTOR, 1.0)
        clk = coapy.clock
        sep = FIFOEndpoint()
        dep = FIFOEndpoint()
        self.assertEqual(0, clk())
        sm = dep.create_request('/path', confirmable=True, token=b'x')

        # Prep the send, then execute it via the timeout.
        ce = sep.send(sm)
        self.assertEqual(0, ce.transmissions)
        self.assertTrue(clk() >= ce.time_due)
        self.assertEqual(ce.ST_untransmitted, ce.state)
        rv = ce.process_timeout()
        self.assertEqual(len(dep.fifo), ce.transmissions)

        # Process the receive
        self.assertTrue(ce.reply_message is None)
        self.assertEqual(0, len(sep._rcvd_cache))
        rce = dep.receive()
        rm = rce.message
        self.assertEqual(rm.source_endpoint, sep)
        self.assertEqual(rm.destination_endpoint, dep)
        self.assertEqual(len(dep.fifo), 0)
        self.assertEqual(sm.messageID, rm.messageID)
        self.assertEqual(1, len(sep._rcvd_cache))

        # Try some invalid replies
        m = ServerErrorResponse(acknowledgement=True,
                                messageID=rm.messageID+1,
                                code=ServerErrorResponse.NotImplemented)
        with self.assertRaises(ReplyMessageError) as cm:
            rce.reply(message=m)
        exc = cm.exception
        self.assertEqual(exc.args[0], exc.ID_MISMATCH)
        self.assertEqual(exc.args[1], rce)
        self.assertEqual(exc.args[2], m)

        m = Request(acknowledgement=True,
                    messageID=rm.messageID,
                    token=b'!'+rm.token,
                    code=Request.GET)
        with self.assertRaises(ReplyMessageError) as cm:
            rce.reply(message=m)
        exc = cm.exception
        self.assertEqual(exc.args[0], exc.NOT_RESPONSE)
        self.assertEqual(exc.args[1], rce)
        self.assertEqual(exc.args[2], m)

        m = ServerErrorResponse(messageID=rm.messageID,
                                token=rm.token,
                                code=ServerErrorResponse.NotImplemented)
        with self.assertRaises(ReplyMessageError) as cm:
            rce.reply(message=m)
        exc = cm.exception
        self.assertEqual(exc.args[0], exc.RESPONSE_NOT_ACK)
        self.assertEqual(exc.args[1], rce)
        self.assertEqual(exc.args[2], m)

        m = ServerErrorResponse(acknowledgement=True,
                                messageID=rm.messageID,
                                token=b'!'+rm.token,
                                code=ServerErrorResponse.NotImplemented)
        with self.assertRaises(ReplyMessageError) as cm:
            rce.reply(message=m)
        exc = cm.exception
        self.assertEqual(exc.args[0], exc.TOKEN_MISMATCH)
        self.assertEqual(exc.args[1], rce)
        self.assertEqual(exc.args[2], m)

        # Send the reply
        self.assertEqual(len(sep.fifo), 0)
        rce.reply(reset=True)

        with self.assertRaises(ReplyMessageError) as cm:
            rce.reply(reset=True)
        exc = cm.exception
        self.assertEqual(exc.args[0], exc.ALREADY_GIVEN)
        self.assertEqual(exc.args[1], rce)

        # Process the reply.  Make sure the RST aborts the BEBO.
        self.assertEqual(len(sep.fifo), 1)
        self.assertTrue(ce.reply_message is None)
        rrce = sep.receive()
        self.assertTrue(rrce is None)
        self.assertTrue(ce.reply_message is not None)
        self.assertTrue(ce.reply_message.is_reset())
        self.assertEqual(ce.ST_completed, ce.state)
        self.assertEqual(ce.time_due, tp.EXCHANGE_LIFETIME)

    def testCONPBReply(self):
        from coapy.message import Message, Request, SuccessResponse

        tp = coapy.transmissionParameters
        self.assertEqual(tp.ACK_RANDOM_FACTOR, 1.0)
        clk = coapy.clock
        sep = FIFOEndpoint()
        dep = FIFOEndpoint()
        self.assertEqual(0, clk())
        sm = dep.create_request('/path', confirmable=True, token=b'x')

        # Prep the send, then execute it via the timeout.
        ce = sep.send(sm)
        self.assertEqual(0, ce.transmissions)
        self.assertTrue(clk() >= ce.time_due)
        self.assertEqual(ce.ST_untransmitted, ce.state)
        rv = ce.process_timeout()
        self.assertEqual(len(dep.fifo), ce.transmissions)

        # Process the receive
        self.assertTrue(ce.reply_message is None)
        self.assertEqual(0, len(sep._rcvd_cache))
        rce = dep.receive()
        reqm = rce.message
        self.assertEqual(reqm.source_endpoint, sep)
        self.assertEqual(reqm.destination_endpoint, dep)
        self.assertEqual(len(dep.fifo), 0)
        self.assertEqual(sm.messageID, reqm.messageID)
        self.assertEqual(1, len(sep._rcvd_cache))

        # Create a response message
        rspm = reqm.create_response(SuccessResponse,
                                    code=SuccessResponse.Content)
        self.assertTrue(rspm.is_acknowledgement())

        # Send the response as a piggy-backed reply
        self.assertEqual(len(sep.fifo), 0)
        rce.reply(message=rspm)

        # Process the reply.  Make sure the ACK aborts the BEBO.
        self.assertEqual(len(sep.fifo), 1)
        self.assertTrue(ce.reply_message is None)
        rrce = sep.receive()
        self.assertTrue(rrce is None)
        self.assertTrue(ce.reply_message is not None)
        self.assertTrue(ce.reply_message.is_acknowledgement())
        self.assertEqual(ce.ST_completed, ce.state)
        self.assertEqual(ce.time_due, tp.EXCHANGE_LIFETIME)

if __name__ == '__main__':
    unittest.main()
