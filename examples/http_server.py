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
This is not a CoAP service, but rather an example of using Python's
HTTP interfaces to create a customized service similar to what we want
CoAP to support.  It serves as an architectural bridge, prototyping
the desired interfaces within an existing framework.

The ``/time`` Resource
======================

  wget -q -S -O- 'http://localhost:8000/time?jdn'

  curl -I -D- 'http://localhost:8000/time?mod'

:copyright: Copyright 2013, Peter A. Bigot
:license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
_log = logging.getLogger(__name__)

import BaseHTTPServer
import urlparse
import time
import socket

import coapy.util
from coapy.httputil import *

class TimeResource(HTTPResource):
    """A resource providing a date/time value in various formats.

    This is a wrapper around :func:`coapy.util.format_time`.

    If :attr:`timestamp` is ``None``, the current time will be used.
    An `Expires <http://tools.ietf.org/html/rfc2616#section-14.21>`_
    header will be added indicating the time at which the
    representation will become invalid.

    If :attr:`timestamp` is not ``None`` then that time will be
    formatted.  The ``Expires`` header will be set from a non-``None``
    :attr:`expiration` timestamp.

    The `query part <http://tools.ietf.org/html/rfc3986#section-3.4>`_
    of the request URI corresponds to the *format* argument of
    :func:`coapy.util.format_time`.  For example::

        llc[442]$ curl -D- 'http://localhost:8000/time?ord'
        HTTP/1.0 200 OK
        Server: BaseHTTP/0.3 Python/2.7.3
        Date: Sat, 12 Oct 2013 06:05:55 GMT
        Content-Type: text/plain
        Content-Length: 9
        Expires: Sun, 13 Oct 2013 00:00:00 GMT

        2013-285
    """

    timestamp = None
    """The timestamp that is the resource value."""

    expiration = None
    """The time at which the resource value becomes obsolete."""

    def do_GET(self, request, head_only=False):
        format = request.split_uri.query
        if not format:
            format = 'iso'
        timestamp = self.timestamp
        expiration = self.expiration
        if timestamp is None:
            timestamp = time.time()
        try:
            (rep, vsec) = coapy.util.format_time(timestamp, format=format)
        except ValueError:
            request.send_error(400, 'Bad format {0}'.format(format))
            return
        content = coapy.util.to_display_text('{0!s}\n'.format(rep)).encode('ascii')
        request.send_response(200)
        request.send_header('Content-Type', 'text/plain')
        request.send_header('Content-Length', len(content))
        if self.timestamp is None:
            expiration = timestamp + vsec
        if expiration is not None:
            request.send_header('Expires', request.date_time_string(expiration))
        request.end_headers()
        if not head_only:
            request.wfile.write(content)

TimeResource('/time')

# Can't use wildcard here since Python server doesn't tell you which
# interface the request came in on, and we need a valid host to
# provide the URI for newly created resources.
server_address = ('localhost', 8000)
httpd = HTTPServer(server_address, HTTPRequestHandler)

while True:
    httpd.handle_request()
