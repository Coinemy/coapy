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
"""
:copyright: Copyright 2013, Peter A. Bigot
:license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
_log = logging.getLogger(__name__)

import socket
import urlparse
import urllib
import random
import itertools
import coapy
import coapy.message

# Gross Hack: Update urlparse so it knows about the coap and coaps
# schemes, specifically that it should support joining relative URIs
# and process netloc and query.
urlparse.uses_relative.extend(['coap', 'coaps'])
urlparse.uses_netloc.extend(['coap', 'coaps'])
urlparse.uses_query.extend(['coap', 'coaps'])


class URIError (coapy.CoAPyException):
    pass


class ReplyMessageError (coapy.CoAPyException):
    """Exception raised when :meth:`RcvdMessageCacheEntry.reply` is
    invoked improperly.

    The *args* are ``(diagnostic, cache_entry, message)`` where
    *diagnostic* is one of the string values in this class,
    *cache_entry* is the :class:`RcvdMessageCacheEntry`, and *message* is
    the proposed reply message that was rejected.
    """

    ID_MISMATCH = 'Message IDs do not match'
    """A reply message must match using the
    :attr:`messageID<coapy.message.Message.messageID>` attributes.
    """

    TOKEN_MISMATCH = 'Tokens do not match'
    """A piggy-backed response must match the
    :attr:`Token<coapy.message.Message.token>` of the request.
    """

    NOT_RESPONSE = 'Non-empty reply is not a response'
    """A piggy-backed response must be a :class:`response
    message<coapy.message.Response>`.
    """

    RESPONSE_NOT_ACK = 'Piggy-backed response is not ACK'
    """A piggy-backed response must have type
    :attr:`ACK<coapy.message.Message.Type_ACK>`.
    """

    ALREADY_GIVEN = 'Message already has reply'
    """A :attr:`reply_message<RcvdMessageCacheEntry.reply_message>`
    has already been assigned.
    """


class MessageCache (object):
    """Dual-view collection used for caches of
    :class:`MessageCacheEntry` instances.

    The class simulates a dictionary allowing lookup of items using
    the integer :coapsect:`message ID<3>`.  Most lookup
    :class:`python:dict` operations are supported on the message ID.
    If a message is used as the key its
    :attr:`messageID<coapy.message.Message.messageID>` is substituted
    automatically.

    The collection also implements a priority queue, allowing
    time-driven events to be processed for cache elements based on
    :attr:`time_due<coapy.util.TimeDueOrdinal.time_due>`.

    Cache entries are placed in a cache when they are created.  It
    is an error to create a new cache entry when one with the same
    :attr:`MessageCacheEntry.message_id` is already present in that
    cache.

    Entry content may be updated while in the cache (in particular,
    modifying :attr:`MessageCacheEntry.time_due` will reposition the
    entry within the :meth:`queue`).  Entries proceed through a
    defined life cycle; after all active stages have been completed an
    event to automatically remove the entry from its cache will be
    scheduled to occur at :attr:`expire<expiry_due>`.
    """

    __queue = None
    __dict = None

    @property
    def endpoint(self):
        """The :class:`Endpoint` to which the cache belongs."""
        return self.__endpoint

    @property
    def is_sent_cache(self):
        """``True`` if this cache is the sent-message cache for its
        :attr:`endpoint`.  ``False`` if this is the received-message
        cache."""
        return self.__is_sent_cache

    def __init__(self, endpoint, is_sent_cache):
        if not isinstance(endpoint, Endpoint):
            raise ValueError(endpoint)
        self.__endpoint = endpoint
        self.__is_sent_cache = is_sent_cache
        self.__queue = []
        self.__dict = {}
        self.keys = self.__dict.keys
        self.values = self.__dict.values
        self.items = self.__dict.items
        self.get = self.__dict.get
        # clear
        # setdefault
        import sys
        if sys.version_info < (3, 0):
            self.has_key = self.__dict.has_key
            self.iterkeys = self.__dict.iterkeys
            self.itervalues = self.__dict.itervalues
            self.iteritems = self.__dict.iteritems
        # pop
        # popitem
        # copy
        # update

    def queue(self):
        """The queue of cache entries sorted by
        :attr:`MessageCacheEntry.time_due`.

        .. warning::

           This method returns a reference to the underlying sorted
           list.  Callers are expected to refrain from changing the
           list in any way other than through methods exposed on the
           cache itself.
        """
        return self.__queue

    def clear(self):
        """Remove all entries in the cache."""
        while self.__queue:
            self._remove(self.__queue[0])

    def _add(self, value):
        """Add *value* to the cache.
        """
        if not isinstance(value, MessageCacheEntry):
            raise ValueError(value)
        if value.message_id in self.__dict:
            raise ValueError(value)
        if value.cache != self:
            raise ValueError(value)
        value.queue_insert(self.__queue)
        self.__dict[value.message_id] = value

    def _remove(self, value):
        """Remove *value* from the cache.
        """
        if not isinstance(value, MessageCacheEntry):
            raise ValueError(value)
        value.queue_remove(self.__queue)
        del self.__dict[value.message_id]
        value._dissociate()
        return value

    def _reposition(self, value):
        """Re-place *value* at its correct location in the queue.

        This must be invoked whenever the underlying
        :attr:`coapy.util.TimeDueOrdinal.time_due` attribute value is
        changed."""
        value.queue_reposition(self.__queue)

    def __len__(self):
        return len(self.__queue)

    def __getitem__(self, key):
        if isinstance(key, coapy.message.Message):
            key = key.messageID
        return self.__dict[key]

    def __contains__(self, key):
        return key in self.__dict


class MessageCacheEntry (coapy.util.TimeDueOrdinal):
    """A class holding data stored in a :class:`MessageCache`.

    Instances sort based on
    :attr:`coapy.util.TimeDueOrdinal.time_due`, and may be looked up
    based on :attr:`message_id`.

    *cache* identifies the :class:`MessageCache` instance to which
    this entry will belong.  Entries are associated with *cache* when
    they are created, and can be removed from that cache.  Once
    removed, an entry cannot be inserted into another cache.

    *message* is a :class:`coapy.message.Message` instance of type
    :attr:`CON<coapy.message.Message.Type_CON>` or
    :attr:`NON<coapy.message.Message.Type_NON>`.
    :attr:`ACK<coapy.message.Message.Type_ACK>` and
    :attr:`RST<coapy.message.Message.Type_RST>` messages cannot be
    cached.
    :attr:`message.messageID<coapy.message.Message.messageID>` is used
    as the key for cache entry lookups.

    *time_due_offset*, if provided, is used to initialize
    :attr:`time_due` by adding it to :attr:`created_clk`.  If
    *time_due_offset* is not provided, the initial :attr:`time_due` is
    :attr:`expiry_due`.
    """

    @property
    def cache(self):
        """The :class:`MessageCache` to which this entry belongs.
        This is a read-only property, set when the entry is created
        and cleared when it has been removed from its cache.
        """
        return self.__cache
    __cache = None

    def _dissociate(self):
        """Remove the connection between the instance and the cache.

        This is invoked by :class:`MessageCache` when the entry is
        removed from its cache.
        """
        self.__cache = None

    @property
    def created_clk(self):
        """The :func:`coapy.clock` value at the time the cache entry
        was created.
        """
        return self.__created_clk
    __created_clk = None

    @property
    def expiry_due(self):
        """The :func:`coapy.clock` value at the time the cache entry
        is obsolete.

        This is calculated on construction by adding
        :attr:`EXCHANGE_LIFETIME<coapy.message.TransmissionParameters.EXCHANGE_LIFETIME>`
        (for :attr:`CON<coapy.message.Message.Type_CON>` messages) or
        :attr:`NON_LIFETIME<coapy.message.TransmissionParameters.NON_LIFETIME>`
        (for :attr:`NON<coapy.message.Message.Type_NON>` messages) to
        :attr:`created_clk`.  Entries must remain in the cache for
        this period to avoid duplicates.
        """
        return self.__expiry_due
    __expiry_due = None

    @property
    def message(self):
        """The :class:`coapy.message.Message` being cached."""
        return self.__message
    __message = None

    def _get_time_due(self):
        """See :attr:`coapy.util.TimeDueOrdinal.time_due`.  In this
        class, modification of the value has the side-effect of moving
        the entry within the :attr:`cache` queue.
        """
        return self.__time_due

    def _set_time_due(self, value):
        self.__time_due = value
        # If we're in the superclass constructor the cache has not
        # yet been assigned (nor has the message_id that must be
        # assigned prior to insertion).  So don't do anything yet.
        if self.__cache is not None:
            self.__cache._reposition(self)
    time_due = property(_get_time_due, _set_time_due)

    @property
    def message_id(self):
        """Short-cut access to :attr:`message.messageID<coapy.message.Message.messageID>`.
        """
        return self.__message.messageID

    def process_timeout(self):
        """Process a timeout at the cache entry.

        This should normally be invoked on an entry by some external
        system as a consequence of :func:`coapy.clock` having reached
        :attr:`time_due`.  Operations performed by this method depend
        on the state of the entry within its lifecycle.  It is an
        error to invoke this on an entry that is no longer present in
        its cache.  Invoking this may cause an entry to be removed
        from its cache.

        The implementation is provided by a subclass.  There is no
        return value.

        .. note::

           The implementation does not attempt to verify that the
           current :attr:`time_due` has been reached; an entry may be
           processed early or late.  The caller is responsible for
           determining whether it is appropriate to invoke this
           method.
        """
        raise NotImplementedError

    def __init__(self, cache, message, time_due_offset=None):
        if not isinstance(cache, MessageCache):
            raise TypeError(cache)
        if not isinstance(message, coapy.message.Message):
            raise TypeError(message)
        super(MessageCacheEntry, self).__init__()
        if message.messageID is None:
            raise ValueError(message)
        if message.is_confirmable():
            expiry_offset = coapy.transmissionParameters.EXCHANGE_LIFETIME
        elif message.is_non_confirmable():
            expiry_offset = coapy.transmissionParameters.NON_LIFETIME
        else:
            # ACK and RST messages should not be cached
            raise ValueError(message)
        if not isinstance(cache, MessageCache):
            raise TypeError(cache)
        self.__message = message
        self.__created_clk = coapy.clock()
        self.__expiry_due = self.__created_clk + expiry_offset

        # Assign the time due first, then associate with the cache, so
        # the infrastructure doesn't attempt to either reposition an
        # entry that is not in the cache, or add an entry that does
        # not have a due time.
        if time_due_offset is None:
            self.time_due = self.__expiry_due
        else:
            self.time_due = self.__created_clk + time_due_offset
        self.__cache = cache
        cache._add(self)


class SentMessageCacheEntry (MessageCacheEntry):
    """Data related to a message sent from a specific endpoint.

    This cache holds a message that originated from a local
    :attr:`coapy.message.Message.source_endpoint`, along with the
    necessary state to retransmit it if it is
    :meth:`confirmable<coapy.message.Message.is_confirmable>`.
    """

    ST_untransmitted = 0
    ST_unacknowledged = 1
    ST_final_ack_wait = 2
    ST_completed = 3
    ST_removed = 4

    @property
    def state(self):
        return self.__state
    __state = None

    @property
    def transmissions(self):
        """Number of times this message has been transmitted."""
        return self.__transmissions
    __transmissions = None

    __bebo = None

    @property
    def reply_message(self):
        """The :class:`coapy.message.Message` that was received in response to :attr:`message`.

        The value is ``None`` unless either an
        :attr:`acknowledgement<coapy.message.Message.Type_ACK>` (empty
        or with a piggy-backed response) or a
        :attr:`reset<coapy.message.Message.Type_RST>` has been
        received.
        """
        return self.__reply
    __reply = None

    @property
    def destination_endpoint(self):
        """The endpoint to which the message is being sent."""
        return self.__destination_endpoint
    __destination_endpoint = None

    @property
    def stale_at(self):
        """Return the time at which the content of a response message is outdated.

        This is calculated at the time the cache entry is created by
        adding the :class:`coapy.option.MaxAge` option value to
        :attr:`created_clk<MessageCacheEntry.created_clk>`.  Prior to
        retransmission callers may wish to update the
        :attr:`message<MessageCacheEntry.message>` options to reflect
        the change in age on subsequent retransmissions.

        The value is ``None`` if the message is not a response.
        """
        return self.__stale_at
    __stale_at = None

    def __init__(self, cache, message, destination_endpoint):
        if not isinstance(message, coapy.message.Message):
            raise ValueError(message)
        self.__destination_endpoint = destination_endpoint
        self.__state = self.ST_untransmitted
        self.__transmissions = 0
        self.__timeout = 0
        super(SentMessageCacheEntry, self).__init__(cache, message,
                                                    time_due_offset=0)
        if isinstance(self.message, coapy.message.Response):
            self.__stale_at = self.created_clk + self.message.maxAge()
        if self.message.is_confirmable():
            self.__bebo = coapy.transmissionParameters.make_bebo()

    def __complete(self):
        self.__state = self.ST_completed
        self.time_due = self.expiry_due

    def process_timeout(self):
        if self.cache is None:
            raise Exception
        if self.__state == self.ST_completed:
            self.cache._remove(self)
            self.__state = self.ST_removed
            return None
        ep = self.cache.endpoint
        data = self.message.to_packed()
        ep.rawsendto(data, self.destination_endpoint)
        self.__transmissions += 1
        if self.ST_untransmitted == self.__state:
            if self.__bebo is None:
                self.__complete()
            else:
                self.__state = self.ST_unacknowledged
        if self.ST_unacknowledged == self.__state:
            try:
                self.__timeout = next(self.__bebo)
            except StopIteration:
                self.__bebo = None
                # Double last timeout (4.2) to wait for
                # acknowledgement to final transmission
                self.__timeout += self.__timeout
                self.__state = self.ST_final_ack_wait
            self.time_due += self.__timeout
        elif self.ST_final_ack_wait == self.__state:
            self.__complete()

    def process_reply(self, msg):
        if self.__reply is not None:
            _log.warning('Multiple replies')
            return
        if msg.is_reset() or ((self.ST_unacknowledged == self.__state) and msg.is_acknowledgement):
            self.__reply = msg
            self.__complete()
            return self
        raise ValueError(msg)


class RcvdMessageCacheEntry (MessageCacheEntry):
    """Data related to a message received by a specific endpoint.

    This cache holds a message that originated from a remote
    :attr:`coapy.message.Message.source_endpoint`, along with the
    necessary state to cache the reply to that message.

    *cache* must be the source endpoint cache for received messages.

    *message* must be a message that originated on that host, and is
    either a :meth:`confirmable<coapy.message.Message.is_confirmable>`
    or
    :meth:`non-confirmable<coapy.message.Message.is_non_confirmable>`
    message.  Acknowledgements and Resets are not recorded in the
    cache.
    """

    @property
    def reception_count(self):
        """The number of times a message with this entry's
        :attr:`message_id<MessageCacheEntry.message_id>` has been
        received while this cache entry is live.  Diagnostics may be
        emitted in a situation where it appears a message ID has been
        re-used prematurely.
        """
        return self.__reception_count
    __reception_count = None

    @property
    def reply_message(self):
        """The :class:`coapy.message.Message` that was sent in
        response to this message.  ``None`` until a response is sent,
        then either an
        :meth:`acknowledgement<coapy.message.Message.is_acknowledgement>`
        (which may or may not have a :coapsect:`piggy-backed
        response<>`) or a
        :meth:`reset<coapy.message.Message.is_reset>` message.  A
        non-confirmable message may have no response at all.
        """
        return self.__reply_message
    __reply_message = None

    def reply(self, reset=False, message=None):
        """Create the :attr:`reply_message` for the reception in this entry.

        If *message* is provided, it should be an
        :class:`coapy.message.Response` message with type
        :attr:`ACK<coapy.message.Message.Type_ACK>` that is to be sent
        as a :coapsect:`piggy-backed response<5.2.1>`.

        If *message* is ``None``, this method will create an empty
        :attr:`ACK<coapy.message.Message.Type_ACK>` (*reset* is
        ``False``) or
        :attr:`RST<coapy.message.Message.Type_RST>` (*reset* is
        ``True``) message.

        The reply message will be transmitted to the source endpoint
        of the received message.

        Erroneous use will raise :exc:`ReplyMessageError`.
        """

        if self.__reply_message is not None:
            raise ReplyMessageError(ReplyMessageError.ALREADY_GIVEN, self, message)
        if message is None:
            message = self.message.create_reply(reset=reset)
        if message.messageID is None:
            message.messageID = self.message.messageID
        if message.messageID != self.message.messageID:
            raise ReplyMessageError(ReplyMessageError.ID_MISMATCH, self, message)
        if coapy.message.Message.Empty != message.code:
            if not isinstance(message, coapy.message.Response):
                raise ReplyMessageError(ReplyMessageError.NOT_RESPONSE, self, message)
            if not message.is_acknowledgement():
                raise ReplyMessageError(ReplyMessageError.RESPONSE_NOT_ACK, self, message)
            if message.token != self.message.token:
                raise ReplyMessageError(ReplyMessageError.TOKEN_MISMATCH, self, message)
        if message.source_endpoint is None:
            message.source_endpoint = self.message.destination_endpoint
        if message.destination_endpoint is None:
            message.destination_endpoint = self.message.source_endpoint
        self.__reply_message = message
        self._transmit_reply()

    def _transmit_reply(self):
        rm = self.__reply_message
        rm.source_endpoint.rawsendto(rm.to_packed(), rm.destination_endpoint)

    def __init__(self, cache, message):
        if not isinstance(message, coapy.message.Message):
            raise ValueError(message)
        self.__reception_count = 1
        super(RcvdMessageCacheEntry, self).__init__(cache, message)

    def process_timeout(self):
        if self.cache is None:
            raise Exception
        # The only time-based event in a received message's lifecycle
        # is its removal from the cache.
        self.cache._remove(self)


class Endpoint (object):
    """A CoAP endpoint.

    Per :coapsect:`1.2` this is an entity participating in the CoAP
    protocol.  In CoAPy it is used to aggregate all material related
    to such an endpoint, which is uniquely identified by an IP
    address, port, and security information.  Various constraints in
    CoAP such as :coapsect:`congestion control<4.7>`,
    :coapsect:`default values for options<5.10.1>`, and re-usability
    of message IDs, are associated with specific endpoints.

    Note that although all endpoints have socket addresses, the base
    :class:`Endpoint` class does not provide any communications
    infrastructure.  Subclasses of :class:`LocalEndpoint` provide
    the communication methods.

    *sockaddr*, if not ``None``, must be a tuple the first two
    elements of which are ``host, port`` which override the
    user-provided *host* and *port*.

    *host* specifies the host of the endpoint as a Unicode string,
    representing a host name, an IP address literal, or other unique
    key.

    *family* is by default :data:`python:socket.AF_UNSPEC` supporting
    resolution of *host* to any address family.  A non-``None`` value
    is passed to :func:`python:socket.getaddrinfo` when attempting to
    resolve *host* as an address; the actual *family* value will be
    the one selected by the resolution process (normally
    :data:`python:socket.AF_INET` or :data:`python:socket.AF_INET6`)
    Failure to successfully resolve *host* will raise
    :exc:`python:socket.gaierror`.  If you want a dummy endpoint
    associated with *host* but that does not have an IP host
    associated with it, make sure that *family* is ``None`` so that
    *host* is left unresolved and instead serves as an *name* as
    described in :attr:`sockaddr`.

    *port* is the integer transport-layer port of the endpoint.  This
    would normally be either :const:`coapy.COAP_PORT` or
    :const:`coapy.COAPS_PORT`.

    *security_mode* is used to determine the DTLS protocol used for
    secure CoAP, and at this time had probably better be left as
    ``None``.

    To ensure consistency, :class:`Endpoint` instances are unique for
    a given key comprising :attr:`family`, :attr:`ip_addr`,
    :attr:`port`, and :attr:`security_mode`.  Attempts to instantiate
    a new endpoint with parameters that match a previously-created one
    will return a reference to the original instance.
    """

    # NOTE To Developer: Because Endpoint controls object allocation
    # through the __new__ method, subclasses should not extend
    # __new__, but instead must make sure that any subclass
    # construction is done with a factory method that ensures its
    # __init__() call takes the same arguments as Endpoint's init
    # (which are the same as Endpoint's __new__).  Subclasses should
    # not initialize any local state in __init__ but instead do so
    # inside _reset(), which Endpoint's __init__ conditionally invokes
    # when the endpoint is first created.  You can ignore this if you
    # know exactly what you're doing, but you probably shouldn't.

    @property
    def sockaddr(self):
        """The Python :mod:`python:socket` address of the endpoint.

        When :attr:`family` is :data:`python:socket.AF_INET` this is
        the tuple ``(host, port)``.

        When :attr:`family` is :data:`python:socket.AF_INET6` this is
        the tuple ``(host, port, flowinfo, scopeid)``.

        When :attr:`family` is ``None`` this is the tuple ``(name,
        port)``.  *name* functions like *host* but is not a resolvable
        host name.

        *host* will be the text representation of :attr:`in_addr`; it
        will not be a host name.  *port* will be a numeric port
        *number*.
        """
        return self.__sockaddr

    @property
    def family(self):
        """The address family used for :attr:`sockaddr`.

        This is normally :data:`python:socket.AF_INET` or
        :data:`python:socket.AF_INET6`.  It may be ``None`` for
        testing situations where the actual endpoint does not
        correspond to an network node.
        """
        return self.__family

    @property
    def in_addr(self):
        """The address of the endpoint.

        The representation is binary data encoding part of
        :attr:`sockaddr`.  Decoding it depends on :attr:`family`:

        When :attr:`family` is :data:`python:socket.AF_INET` this is
        the IPv4 address in network byte order.

        When :attr:`family` is :data:`python:socket.AF_INET6` this is
        the IPv6 address in network byte order.

        When :attr:`family` is ``None`` this is the *name* in
        Net-Unicode format.
        """
        return self.__in_addr

    @property
    def port(self):
        """The transport-level port of the endpoint."""
        return self.__port

    @property
    def security_mode(self):
        """The security mode of the endpoint.  Generally ``None``
        though if :coapsect:`DTLS<9>` CoAP is used it would be some
        other value.
        """
        return self.__security_mode

    @property
    def uri_host(self):
        """The text value for the ``host`` subcomponent of the
        authority part of a URI involving this endpoint.

        This is almost always either an ``IPv4address`` or
        ``IP-literal`` as defined by `section 3.2.2 of RFC3986`_.  If
        an :class:`Endpoint` is created by an application using a host
        name, the resolved address of the host is used for
        :attr:`sockaddr` and for this property.

        .. _section 3.2.2 of RFC3986: http://tools.ietf.org/html/rfc3986#section-3.2.2
        """
        return self.__uri_host

    @property
    def base_uri(self):
        """The base CoAP URI for resources on this endpoint.

        This is used by :meth:`uri_to_options` to avoid the need to
        specify the protocol and netloc when creating option lists.
        """
        return self.__base_uri
    __base_uri = None

    __EndpointRegistry = {}
    __nonInetIndex = 0

    @staticmethod
    def _key_for_sockaddr(sockaddr, family, security_mode=None):
        """Create the key used to look up endpoints.

        *sockaddr* must be a tuple the first two elements of which are
        ``(host, port)``.  Unless *family* is ``None``, *host* must be
        a text representation of an IP address that can be converted
        with :func:`python:socket.inet_pton` using *family*, not a
        hostname.  *port* must be a numeric port number.

        If *family* is :data:`python:socket.AF_UNSPEC` a
        :exc:`python:exception.ValueError` exception will be raised as
        the system does not know how to decode the *host*.
        """
        if not isinstance(sockaddr, tuple):
            raise TypeError(sockaddr)
        ip_literal = sockaddr[0]
        if family is None:
            in_addr = coapy.util.to_net_unicode(ip_literal)
        elif family is socket.AF_UNSPEC:
            raise ValueError
        else:
            # Use the network-byte-order binary representation of the
            # IP address, to having to deal with non-canonical IPv6
            # text representations.  See RFC5952 for why this is
            # necessary.
            in_addr = socket.inet_pton(family, ip_literal)
        return (family, in_addr, sockaddr[1], security_mode)

    @staticmethod
    def _canonical_sockinfo(sockaddr=None, family=socket.AF_UNSPEC,
                            security_mode=None,
                            host=None, port=coapy.COAP_PORT):
        """Get canonical socket information for an endpoint.

        Returns a tuple ``(family, sockaddr)`` where *sockaddr* is a
        an :attr:`address<sockaddr>` as constrained by *family*.

        Failure to resolve the socket *host* to a numeric IP literal
        within *family* (if required) will raise
        :exc:`python:socket.gaierror`.
        """
        if sockaddr is not None:
            try:
                key = Endpoint._key_for_sockaddr(sockaddr, family, security_mode)
                ep = Endpoint.__EndpointRegistry.get(key)
                if ep is not None:
                    return (ep.family, ep.sockaddr)
            except:
                pass
            if not isinstance(sockaddr, tuple):
                raise TypeError(sockaddr)
            if 2 > len(sockaddr):
                raise ValueError(sockaddr)
            (host, port) = sockaddr[:2]
        if host is None:
            raise ValueError(host)
        if not isinstance(port, int):
            raise TypeError(port)
        if family is None:
            gai = (family, None, None, host, (host, port))
        else:
            gais = socket.getaddrinfo(host, port, family, socket.SOCK_DGRAM, 0,
                                      (socket.AI_ADDRCONFIG | socket.AI_V4MAPPED
                                       | socket.AI_NUMERICSERV))
            gai = gais.pop(0)
        return (gai[0], gai[4])

    @classmethod
    def lookup_endpoint(cls, sockaddr=None, family=socket.AF_UNSPEC,
                        security_mode=None,
                        host=None, port=coapy.COAP_PORT):
        """Look up an endpoint using the same algorithm as endpoint
        creation.

        Returns ``None`` if passing these parameters to
        :class:`Endpoint` would result in creation of a new endpoint.
        """
        instance = None
        if sockaddr is not None:
            try:
                key = Endpoint._key_for_sockaddr(sockaddr, family, security_mode)
                instance = Endpoint.__EndpointRegistry.get(key)
            except:
                pass
        if instance is None:
            (family, sockaddr) = Endpoint._canonical_sockinfo(sockaddr, family,
                                                              security_mode, host, port)
            key = Endpoint._key_for_sockaddr(sockaddr, family, security_mode)
            instance = Endpoint.__EndpointRegistry.get(key)
        return instance

    def __new__(cls, sockaddr=None, family=socket.AF_UNSPEC,
                security_mode=None,
                host=None, port=coapy.COAP_PORT):
        instance = None
        if sockaddr is not None:
            try:
                key = Endpoint._key_for_sockaddr(sockaddr, family, security_mode)
                instance = Endpoint.__EndpointRegistry.get(key)
            except:
                pass
        if instance is None:
            (family, sockaddr) = Endpoint._canonical_sockinfo(sockaddr, family,
                                                              security_mode, host, port)
            key = Endpoint._key_for_sockaddr(sockaddr, family, security_mode)
            instance = Endpoint.__EndpointRegistry.get(key)
        if instance is None:
            instance = super(Endpoint, cls).__new__(cls)
            host = sockaddr[0]
            port = sockaddr[1]
            cls.__EndpointRegistry[key] = instance
            instance.__family = family
            instance.__in_addr = key[1]
            instance.__port = port
            instance.__security_mode = security_mode
            instance.__sockaddr = sockaddr
            if socket.AF_INET == family:
                instance.__uri_host = '{0}'.format(socket.inet_ntop(instance.family,
                                                                    instance.in_addr))
            elif socket.AF_INET6 == family:
                instance.__uri_host = '[{0}]'.format(socket.inet_ntop(instance.family,
                                                                      instance.in_addr))
            else:
                instance.__uri_host = host
        return instance

    def __del__(self):
        self._reset()
        super(Endpoint, self).__del__(self)

    def _reset(self):
        """Return all data to its initial state.

        This is a back-door for unit-testing from a known state.  It's
        also used when a new Endpoint is constructed for the first
        time.  Only mutable state is reset; immutable values like
        :attr:`family` and :attr:`sockaddr` are not affected.

        .. note::

           This method uses cooperative super-calling for subclass
           extension.
        """
        self._reset_next_messageID(random.randint(0, 65535))
        self._sent_cache = MessageCache(self, True)
        self._rcvd_cache = MessageCache(self, False)

    def __init__(self, sockaddr=None, family=socket.AF_UNSPEC,
                 security_mode=None,
                 host=None, port=coapy.COAP_PORT):
        # None of these arguments are used here; they apply in
        # __new__.
        super(Endpoint, self).__init__()
        # Note: Only re-initialize if the instance was newly created.
        if self.__base_uri is None:
            self.__base_uri = self.uri_from_options([])
            self._reset()

    def next_messageID(self):
        """Return a new messageID suitable for a message to this endpoint.

        This is sequentially generated starting from an initial value
        that was randomly generated when the endpoint was created.  It
        is filtered so message IDs still present in the sent message
        cache are not re-used.
        """
        while True:
            mid = next(self.__messageID_iter)
            if not (mid in self._sent_cache):
                return mid

    def _reset_next_messageID(self, start):
        # Back-door for unit testing from known starting point
        self.__messageID_iter = itertools.imap(lambda _v: _v % 65536, itertools.count(start))

    def get_peer_endpoint(self, sockaddr=None, host=None, port=coapy.COAP_PORT):
        """Find the endpoint at *sockaddr* that this endpoint can talk to.

        This invokes :class:`Endpoint` with *family* and
        *security_mode* set to the parameters used by this endpoint.
        It is used to identify the source endpoint of a message
        received by :meth:`python:socket.socket.recvfrom`.  *sockaddr*
        will be constructed from *host* and *port* if not provided
        explicitly; at least one of *sockaddr* and *host* must be
        given.
        """
        if sockaddr is None:
            if host is None:
                raise ValueError
            if not isinstance(port, int):
                raise TypeError
            sockaddr = (host, port)
        return type(self)(sockaddr=sockaddr, family=self.family, security_mode=self.security_mode)

    def is_same_host(self, host):
        """Determine whether *host* resolves to the same address as
        this endpoint.

        This is used for the algorithm in :coapsect:`6.4` to determine
        that a :class:`UriHost<coapy.option.UriHost>` option may be
        elided in favor of the default derived from an endpoint.  This
        can only be done if *host* is an ``IP-literal`` or
        ``IPv4address`` equivalent to :attr:`in_addr` in
        :attr:`family`.  DNS resolution is not used.
        """
        if self.family is None:
            return self.uri_host == host
        try:
            in_addr = socket.inet_pton(self.family, host)
            return self.in_addr == in_addr
        except socket.error:
            pass
        return False

    @staticmethod
    def _port_for_scheme(scheme):
        return {'coap': coapy.COAP_PORT,
                'coaps': coapy.COAPS_PORT}[scheme]

    def uri_to_options(self, uri, base_uri=None):
        """Convert a URI to a list of CoAP options relative to this endpoint.

        *uri* should be an :rfc:`3986` conformant absolute URI.  For
        convenience, if *base_uri* is not None the value of *uri* will
        be recalculated assuming it is relative to *base_uri*.
        *base_uri* itself will default to :attr:`base_uri` if no
        non-``None`` value is provided.

        The scheme part of *uri* must be either "coap" or "coaps".

        Options will be returned in a list in the following order.

        * :class:`coapy.option.UriHost`, absent if the URI host
          matches the endpoint :attr:`family` and :attr:`in_addr`;
        * :class:`coapy.option.UriPort`, absent if the URI port
          matches the endpoint :attr:`port`;
        * :class:`coapy.option.UriPath`, absent if the path is empty,
          otherwise occurs once per path segment;
        * :class:`coapy.option.UriQuery`, absent if there is no query
          part, otherwise occurs once per ``&``-separated query
          element.
        """

        if base_uri is None:
            base_uri = self.base_uri
        if base_uri is not None:
            uri = urlparse.urljoin(base_uri, uri)
        res = urlparse.urlsplit(uri)
        opts = []
        # 6.4.1. absolute-URI = scheme ":" hier-part [ "?" query ]
        if (not res.scheme) \
           or ((res.netloc is None) and (res.path is None)) \
           or res.fragment:
            raise URIError('not absolute', uri)
        # 6.4.2. Make this user's job or done by urljoin
        # 6.4.3. Check scheme
        scheme = res.scheme.lower()
        if not (scheme in ('coap', 'coaps')):
            raise URIError('invalid scheme', res.scheme)
        # 6.4.4. Unnecessary: fragments aren't allowed in absolute-URIs,
        # or in the restrictions for coap-URI and coaps-URI.

        # 6.4.5. authority = [ userinfo "@" ] host [ ":" port] CoAP
        # doesn't provide a way to pass userinfo, so defer to the
        # ParseResult hostname and port values rather than try to re-parse
        # netloc locally.
        if res.hostname:
            host = coapy.util.url_unquote(res.hostname)
            if not self.is_same_host(host):
                opts.append(coapy.option.UriHost(host))

        # 6.4.6.  Set port from URI or default from scheme
        port = res.port
        if port is None:
            port = self._port_for_scheme(scheme)

        # 6.4.7.
        if port != self.port:
            opts.append(coapy.option.UriPort(port))

        # 6.4.8
        path = res.path
        if path and not ('/' == path):
            if path.startswith('/'):
                path = path[1:]
            for segment in path.split('/'):
                segment = coapy.util.url_unquote(segment)
                opts.append(coapy.option.UriPath(segment))

        # 6.4.9
        query = res.query
        if query:
            for qseg in query.split('&'):
                qseg = coapy.util.url_unquote(qseg)
                opts.append(coapy.option.UriQuery(qseg))
        return opts

    def uri_from_options(self, opts):
        """Create a URI from endpoint data and the options.

        The resulting URI scheme is "coap" unless
        :attr:`security_mode` is set (in which case it is "coaps").

        The authority is derived from
        :class:`UriHost<coapy.option.UriHost>` and
        :class:`UriPort<coapy.option.UriPort>` options in *opts*,
        defaulting to :attr:`uri_host` and :attr:`port` if the
        respective options are not provided.

        The remainder of the URI is built up from
        :class:`UriPath<coapy.option.UriPath>` and
        :class:`UriQuery<coapy.option.UriQuery>` options in *opts*.
        """
        scheme = 'coap'
        if self.security_mode is not None:
            scheme = 'coaps'
        host = None
        opt = coapy.option.UriHost.first_match(opts)
        if opt is not None:
            host = opt.value
            if host is None:
                raise URIError('empty Uri-Host')
            if host and ('[' != host[0]):
                host = coapy.util.url_quote(host)
        if host is None:
            host = self.uri_host
        port = self.port
        opt = coapy.option.UriPort.first_match(opts)
        if opt is not None:
            port = opt.value
            if port is None:
                raise URIError('empty Uri-Port')
        if port == self._port_for_scheme(scheme):
            netloc = host
        else:
            netloc = '{0}:{1}'.format(host, port)
        # Paths are always absolute, so start with an empty segment so the
        # encoded version begins with a slash.
        elts = ['']
        for segment_opt in coapy.option.UriPath.all_match(opts):
            segment = segment_opt.value
            segment = coapy.util.url_quote(segment, '')
            elts.append(segment)
        path = '/'.join(elts)
        if not path:
            # Make sure we still have the leading slash
            path = '/'
        elts = []
        for qseg_opt in coapy.option.UriQuery.all_match(opts):
            qseg = qseg_opt.value
            qseg = coapy.util.url_quote(qseg, '?')
            elts.append(qseg)
        query = '&'.join(elts)
        return urlparse.urlunsplit((scheme, netloc, path, query, None))

    def finalize_message(self, message):
        """Final checks and refinements for *message* relative to this
        endpoint.

        The *message* is
        :meth:`validated<coapy.message.Message.validate>`, then the
        following final cleanup in its
        :attr:`options<coapy.message.Message.options>` is done:

        * A :class:`coapy.option.UriHost` that is the :meth:`same
          host<is_same_host>` as the endpoint will be removed.
        * A :class:`coapy.option.UriPort` that is the same port as the
          endpoint is removed.

        The finalized message is returned.
        """
        message.validate()
        nopt = []
        for oi in xrange(len(message.options)):
            opt = message.options[oi]
            if isinstance(opt, coapy.option.UriHost) and self.is_same_host(opt.value):
                continue
            elif isinstance(opt, coapy.option.UriPort) and (opt.value == self.port):
                continue
            nopt.append(opt)
        if len(nopt) != len(message.options):
            message.options = nopt
        return message

    def create_request(self, uri,
                       confirmable=False,
                       code=coapy.message.Request.GET,
                       messageID=None,
                       token=None,
                       options=None,
                       payload=None):
        """Create and return a :class:`Request<coapy.message.Request>`
        instance to retrieve *uri* from this endpoint.

        *uri* should generally be a relative URI hosted on the
        endpoint.

        By default this creates a non-confirmable
        :attr:`GET<coapy.message.Request.GET>` message.  These
        features can be overridden with *confirmable* and *code*.
        *messageID* will default to :meth:`next_messageID`.  The
        caller may specify a token; if none is provided, an empty
        token will be used.  Any *options* are appended to the options
        derived from *uri*, and *payload* is as in the
        :class:`coapy.message.Message` constructor.  The message
        :attr:`destination_endpoint<coapy.message.Message.destination_endpoint>`
        is set to *self*, and finally the message is returned to the
        caller.
        """
        uri_options = []
        if uri is not None:
            uri_options = self.uri_to_options(uri)
        if messageID is None:
            messageID = self.next_messageID()
        if token is None:
            token = b''
        if options is not None:
            uri_options.extend(options)
        m = coapy.message.Request(confirmable=confirmable,
                                  code=code, messageID=messageID,
                                  token=token, options=uri_options,
                                  payload=payload)
        m.destination_endpoint = self
        return m

    def __unicode__(self):
        return '{s.uri_host}:{s.port:d}'.format(s=self)
    __str__ = __unicode__


class LocalEndpoint(Endpoint):
    """Extends :class:`Endpoint` with methods to send and receive messages.

    This is an abstract class; a subclass must implement the
    underlying communications operations invoked through
    :meth:`rawsendto` and :meth:`rawrecvfrom`.  The most likely
    subclass is :class:`SocketEndpoint`, but for simulation and
    testing purposes alternative implementations like
    :class:`tests.support.FIFOEndpoint` may be used.
    """

    def _reset(self):
        """Return all data to its initial state.

        """
        self._sent_cache = MessageCache(self, True)
        self._rcvd_cache = MessageCache(self, False)
        super(LocalEndpoint, self)._reset()

    def rawsendto(self, data, destination_endpoint):
        """Send *data* from this endpoint to *destination_endpoint*.

        *data* is :class:`bytes` data.  *destination_endpoint* is an
        instance of :class:`Endpoint`.

        The mechanism by which the data is transferred depends on
        subclass support for communications, and a subclass must
        override this method.
        """
        raise NotImplementedError

    def rawrecvfrom(self, bufsize):
        """Receive *data* from a *source_endpoint*.

        Returns tuple ``(data, source_endpoint)`` where *data* is
        :class:`bytes` data and *source_endpoint* is the instance
        :class:`Endpoint` associated with the origin of *data*.

        Subclasses must override this method.  The method of
        communication is determined by the subclass.  Whether the call
        blocks or raises an exception if communication is unavailable
        is not specified, but if no exception is raised the return
        value must be as described above.
        """
        raise NotImplementedError

    def receive(self):
        """Receive and decode a message from another endpoint.

        Returns ``None`` if the message is so corrupt it should be
        ignored, or if the received message is a duplicate.  Raises
        :exc:`coapy.message.MessageFormatError` if the message cannot
        be fully decoded.  Otherwise returns the message, in which
        :attr:`destination_endpoint<coapy.message.Message.destination_endpoint>`
        will be set to *self* and
        :attr:`source_endpoint<coapy.message.Message.source_endpoint>`
        will be set to *source_endpoint*.

        Any message-layer processing (e.g. re-sending duplicate ACK or
        RST, or sending a RST due to a message format error) will have
        been done before this call returns.
        """
        m = None
        dkw = None
        (data, source_endpoint) = self.rawrecvfrom(8192)
        try:
            m = coapy.message.Message.from_packed(data)
            m.destination_endpoint = self
            m.source_endpoint = source_endpoint
        except coapy.message.MessageFormatError as e:
            _log.exception('receive')
            dkw = e.args[1]
        if m is None:
            mid = dkw['messageID']
            mtype = dkw['type']
        else:
            mid = m.messageID
            mtype = m.messageType
        local_origin = not coapy.message.Message.source_originates_type(mtype)
        if local_origin:
            # local_origin means ACK or RST; look in send cache.
            ce = self._sent_cache.get(mid)
            if ce is None:
                _log.error('Reply to unrecognized message')
                return None
            if m is None:
                _log.error('Invalid reply to message')
                return None
            ce.process_reply(m)
            return None
        # not local origin means CON or NON; look in receive cache
        ce = source_endpoint._rcvd_cache.get(mid)
        if ce is not None:
            _log.error('Received duplicate')
            return None
        if m is None:
            _log.error('Need send RST')
        return RcvdMessageCacheEntry(source_endpoint._rcvd_cache, m)

    def send(self, msg, destination_endpoint=None):
        """Send *msg* to *destination_endpoint*.

        *msg* must be an instance of :class:`coapy.message.Message`.

        *destination_endpoint* specifies where the packed message will
        be sent and defaults to *msg*'s
        :attr:`destination_endpoint<coapy.message.Message.destination_endpoint>`.

        The return value is the :class:`SentMessageCacheEntry` that
        has message-level transmission state.
        """
        if not isinstance(msg, coapy.message.Message):
            raise TypeError(msg)
        if destination_endpoint is None:
            destination_endpoint = msg.destination_endpoint
        return SentMessageCacheEntry(self._sent_cache, msg, destination_endpoint)


class SocketEndpoint (LocalEndpoint):
    """An endpoint that has a Python :func:`python:socket.socket`
    bound to it to be used for network communications.

    While all :class:`Endpoint` instances have a socket address, only
    endpoints that belong to the local node have sockets associated
    with them.  These sockets are used to exchange messages with
    remote endpoints.
    """

    __bound_socket = None

    def set_bound_socket(self, socket):
        """Set the :attr:`bound_socket`.

        *socket* may be ``None``, in which case the endpoint is
        disassociated from any socket.

        If *socket* is not ``None`` it must be an object suitable for
        assignment to :attr:`bound_socket`.  The endpoint adopts the
        socket, in that if/when the endpoint is destroyed the socket
        will be closed if it remains bound to the endpoint.  (Since
        :class:`Endpoint` instances are almost impossible to destroy,
        this has little relevance at this time.)

        In either case if the assignment succeed the previous value of
        :attr:`bound_socket` is returned, with the caller taking
        responsibility to close it when finished.

        .. note::
           For simulation and testing purposes *socket* might not be
           a :func:`socket object<python:socket.socket>`, but it must
           act like one with respect to the methods CoAPy expects it
           to provide, including but not limited to:

           * :meth:`getsockname()<python:socket.socket.getsockname>`
           * :meth:`sendto()<python:socket.socket.sendto>`
        """
        obs = self.__bound_socket
        if (socket is not None) and (self.sockaddr != socket.getsockname()):
            raise ValueError(socket)
        self.__bound_socket = socket
        return obs

    @property
    def bound_socket(self):
        """Return a :func:`socket object<python:socket.socket>`
        instance that is bound to :attr:`sockaddr`.

        This may only be set for endpoints that are local to the host.
        It may set to ``None`` to disassociate the endpoint from a
        socket, and may be changed from ``None`` to an object that
        returns :attr:`sockaddr` when
        :meth:`socket.getsockname<python:socket.socket.getsockname>`
        is invoked on it.

        See :meth:`create_bound_endpoint` and
        :meth:`set_bound_socket`.
        """
        return self.__bound_socket

    def rawsendto(self, data, destination_endpoint):
        """Send *data* from this endpoint to *destination_endpoint*.

        This invokes :meth:`sendto<python:socket.socket.sendto>` on
        :attr:`bound_socket` to transmit *data* to the
        *destination_endpoint* at its :attr:`sockaddr`.
        """
        return self.bound_socket.sendto(data, destination_endpoint.sockaddr)

    def rawrecvfrom(self, bufsize):
        """Receive *data* from a *source_endpoint*.

        Invokes :meth:`recvfrom<python:socket.socket.recvfrom>` on
        :attr:`bound_socket` and uses the resulting source address to
        identify the corresponding :class:`Endpoint` instance as
        *source_endpoint*.  Returns ``(data, source_endpoint)``.
        """
        (data, addr) = self.bound_socket.recvfrom(bufsize)
        return (data, Endpoint(sockaddr=addr, family=self.family))

    @classmethod
    def create_bound_endpoint(cls, sockaddr=None, family=socket.AF_UNSPEC,
                              security_mode=None,
                              host=None, port=coapy.COAP_PORT):
        """Create an endpoint with a local socket bound to it.

        *sockaddr*, *family*, *security_mode*, *host*, and *port* are
        all as used with :class:`Endpoint`.

        For use with a CoAP service on the local host (*host* as
        ``127.0.0.1`` or ``::1``), *port* may be 0 in this call.  This
        allows the bind operation to select an unused local port.

        Returns the created endpoint with :attr:`bound_socket`
        initialized and ready to send and receive messages.
        """
        # First, figure out the resolved family and host/port part of
        # the socket address.
        (family, sockaddr) = cls._canonical_sockinfo(sockaddr=sockaddr,
                                                     family=family,
                                                     security_mode=security_mode,
                                                     host=host,
                                                     port=port)
        if (family is None) or (family is socket.AF_UNSPEC):
            raise ValueError
        # Create a socket, bind it to the proposed socket address, then use
        # the result as the endpoint socket address: this is necessary because
        # if port was passed as 0 the act of binding assigned a local
        # port which we need to obtain.
        s = socket.socket(family, socket.SOCK_DGRAM)
        s.bind(sockaddr)
        sockaddr = s.getsockname()
        # Now we can create the instance and associate the socket with it.
        ep = cls(sockaddr=sockaddr, family=family, security_mode=security_mode)
        ep.set_bound_socket(s)
        return ep

    def _reset(self):
        if self.__bound_socket is not None:
            try:
                self.__bound_socket.close()
            except:
                pass
            self.__bound_socket = None
        super(SocketEndpoint, self)._reset()
