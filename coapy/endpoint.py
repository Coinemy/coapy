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

import coapy
import socket
import urlparse
import urllib


class URIError (coapy.CoAPyException):
    pass


class Endpoint (object):
    """A CoAP endpoint.

    Per :coapsect:`1.2` this is an entity participating in the CoAP
    protocol.  In CoAPy it is used to aggregate all material related
    to such an endpoint, which is uniquely identified by an IP
    address, port, and security information.  Various constraints in
    CoAP such as :coapsect:`congestion control<4.7>`,
    :coapsect:`default values for options<5.10.1>`, and re-usability
    of message IDs, are associated with specific endpoints.

    *host* specifies the host of the endpoint, and should be something
    that resolves to an INET domain address using
    :func:`python:socket.getaddrinfo`.  If it is unresolvable,
    :attr:`family` will be ``None``, :attr:`ip_addr` will be the
    binary value of *host* encoded in UTF-8.

    *port* should be the transport-layer port of the endpoint.  This
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

    @property
    def sockaddr(self):
        """The Python :class:`python:socket.socket` address of the
        endpoint.

        When :attr:`family` is :data:`python:socket.AF_INET` this is the
        tuple ``(host, port)``.

        When :attr:`family` is :data:`python:socket.AF_INET6` this is
        the tuple ``(host, port, flowinfo, scopeid)``.

        When :attr:`family` is ``None`` this is the tuple ``(host,
        port)`` (but *host* probably cannot be resolved so this isn't
        very useful).
        """
        return self.__sockaddr

    @property
    def family(self):
        """The address family used for :attr:`sockaddr`.

        This is normally :data:`python:socket.AF_INET` or :data:`python:socket.AF_INET6`.
        """
        return self.__family

    @property
    def ip_addr(self):
        """The IP address of the endpoint as data in network byte order.

        The value can be decoded using :func:`python:socket.inet_pton` and :attr:`family`.
        """
        return self.__ip_addr

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

    @staticmethod
    def _get_addr_info(host, port):
        try:
            gai = socket.getaddrinfo(host, port, 0, socket.SOCK_DGRAM)
            return gai.pop(0)
        except socket.gaierror as e:
            return (None, None, None, host, (host, port))

    __EndpointRegistry = {}
    __nonInetIndex = 0

    def __new__(cls, host, port=coapy.COAP_PORT, security_mode=None):
        if not isinstance(host, unicode):
            raise TypeError
        address = cls._get_addr_info(host, port)
        (family, socktype, proto, canonname, sockaddr) = address
        # Ignore flowinfo and scopeid for IPv6
        (host, port) = sockaddr[:2]
        if family is None:
            ip_addr = host.encode('utf-8')
        else:
            ip_addr = socket.inet_pton(family, host)
        key = (family, ip_addr, port, security_mode)
        instance = cls.__EndpointRegistry.get(key)
        if instance is None:
            instance = super(Endpoint, cls).__new__(cls)
            cls.__EndpointRegistry[key] = instance
            instance.__family = family
            instance.__ip_addr = ip_addr
            instance.__port = port
            instance.__security_mode = security_mode
            instance.__sockaddr = sockaddr
            if socket.AF_INET == family:
                instance.__uri_host = '{0}'.format(socket.inet_ntop(family, ip_addr))
            elif socket.AF_INET6 == family:
                instance.__uri_host = '[{0}]'.format(socket.inet_ntop(family, ip_addr))
            else:
                instance.__uri_host = host
        return instance

    def __init__(self, host, port=coapy.COAP_PORT, security_mode=None):
        # None of these arguments are used here; they apply in
        # __new__.
        super(Endpoint, self).__init__()

    def is_same_host(self, host):
        """Determine whether *host* resolves to the same address as
        this endpoint.  Used to determine that a
        :class:`UriHost<coapy.option.UriHost>` option may be elided in
        favor of the default derived from an endpoint.
        """
        address = self._get_addr_info(host, self.port)
        family = address[0]
        sockaddr = address[4]
        return (self.family == family) and (self.sockaddr == sockaddr)

    @staticmethod
    def _port_for_scheme(scheme):
        return {'coap': coapy.COAP_PORT,
                'coaps': coapy.COAPS_PORT}[scheme]

    def uri_to_options(self, uri, base_uri=None):
        """Convert a URI to a list of CoAP options relative to this endpoint.

        *uri* should be an :rfc:`3986` conformant absolute URI.  For
        convenience, if *base_uri* is not None the value of *uri*
        will be recalculated assuming it is relative to *base_uri*.

        The scheme part of *uri* must be either "coap" or "coaps".

        Options will be returned in a list in the following order.

        * :class:`coapy.option.UriHost`, absent if the URI host
          matches the endpoint :attr:`family` and :attr:`ip_addr`;
        * :class:`coapy.option.UriPort`, absent if the URI port
          matches the endpoint :attr:`port`;
        * :class:`coapy.option.UriPath`, absent if the path is empty,
          otherwise occurs once per path segment;
        * :class:`coapy.option.UriQuery`, absent if there is no query
          part, otherwise occurs once per ``&``-separated query
          element.

        """

        if base_uri is not None:
            uri = urlparse.urljoin(base_uri, uri)
        res = urlparse.urlsplit(uri)
        opts = []
        # 6.4.1. absolute-URI = scheme ":" hier-part [ "?" query ]
        if (not res.scheme) \
           or ((res.netloc is None) and (res.path is None)) \
           or res.fragment:
            raise coapy.URIError('not absolute', uri)
        # 6.4.2. Make this user's job or done by urljoin
        # 6.4.3. Check scheme
        scheme = res.scheme.lower()
        if not (scheme in ('coap', 'coaps')):
            raise coapy.URIError('invalid scheme', res.scheme)
        # 6.4.4. Unnecessary: fragments aren't allowed in absolute-URIs,
        # or in the restrictions for coap-URI and coaps-URI.

        # 6.4.5. authority = [ userinfo "@" ] host [ ":" port] CoAP
        # doesn't provide a way to pass userinfo, so defer to the
        # ParseResult hostname and port values rather than try to re-parse
        # netloc locally.
        if res.hostname:
            host = urllib.unquote(res.hostname)
            if not self.is_same_host(host):
                opts.append(coapy.option.UriHost(host))

        # 6.4.6.  Set port from URI or default from scheme
        port = res.port
        if port is None:
            port = self._port_for_scheme(scheme)

        # 6.4.7.
        if port != self.port:
            opts.append(coapy.option.UriPort(port))

        # 6.4.8/9. OK, trickiness.  Python's urlparse won't separate the
        # query part from the path if the scheme isn't one that it thinks
        # should support query (coap is not such a one).  Do that first.
        path = res.path
        query = res.query
        splitq = path.split('?', 1)
        if (not query) and (1 < len(splitq)):
            (path, query) = splitq
        if path and not ('/' == path):
            if path.startswith('/'):
                path = path[1:]
            for segment in path.split('/'):
                segment = bytes(segment)
                segment = urllib.unquote(segment)
                segment = segment.decode('utf-8')
                opts.append(coapy.option.UriPath(segment))
        if query:
            for qseg in query.split('&'):
                qseg = bytes(qseg)
                qseg = urllib.unquote(qseg)
                qseg = qseg.decode('utf-8')
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
        for opt in filter(lambda _o: isinstance(_o, coapy.option.UriHost), opts):
            host = opt.value
            if host is None:
                raise coapy.URIError('empty Uri-Host')
            if host and ('[' != host[0]):
                host = urllib.quote(host.encode('utf-8'))
            break
        if host is None:
            host = self.uri_host
        port = self.port
        for opt in filter(lambda _o: isinstance(_o, coapy.option.UriPort), opts):
            port = opt.value
            if port is None:
                raise coapy.URIError('empty Uri-Port')
        if port == self._port_for_scheme(scheme):
            netloc = host
        else:
            netloc = '{0}:{1}'.format(host, port)
        # Paths are always absolute, so start with an empty segment so the
        # encoded version begins with a slash.
        elts = ['']
        for segment_opt in filter(lambda _o: isinstance(_o, coapy.option.UriPath), opts):
            segment = segment_opt.value
            segment = coapy.util.to_net_unicode(segment)
            segment = urllib.quote(segment, str(''))
            elts.append(segment)
        path = '/'.join(elts)
        if not path:
            # Make sure we still have the leading slash
            path = '/'
        elts = []
        for qseg_opt in filter(lambda _o: isinstance(_o, coapy.option.UriQuery), opts):
            qseg = qseg_opt.value
            qseg = coapy.util.to_net_unicode(qseg)
            qseg = urllib.quote(qseg, str('?'))
            elts.append(qseg)
        query = '&'.join(elts)
        return urlparse.urlunsplit((scheme, netloc, path, query, None))
