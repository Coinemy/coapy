# -*- coding: utf-8 -*-
# Copyright 2013, Peter A. Bigot
# Parts Copyright © 2001-2013 Python Software Foundation; All Rights Reserved
#
# Excepting the small part of RequestHandler.handle_one_request that
# is copied from Python 2.7.3 BaseHTTPServer.py and is subject to the
# PSF License:
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
To simplify comparison between CoAP and HTTP, these classes are
provided to support resources with an HTTP interface.

:copyright: Copyright 2013, Peter A. Bigot
:license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
_log = logging.getLogger(__name__)

import sys
import urllib
import BaseHTTPServer
import socket
import urlparse
import time
import coapy.util


class HTTPServer(BaseHTTPServer.HTTPServer):
    """Modifications required to provide the server development
    interface we want.
    """

    def make_uri(self, path, query='', fragment=''):
        """Create an absolute URI for something hosted on this server.

        Needed for things like a `Location
        <http://tools.ietf.org/html/rfc2616#section-14.30>`_ header.

        .. note::

           This function will not return a usable URI if
           :attr:`python:BaseHTTPServer.HTTPServer.socket` is bound to
           a wildcard address.
        """
        (sa, port) = self.socket.getsockname()[:2]
        if 80 != port:
            netloc = '{0}:{1}'.format(sa, port)
        else:
            netloc = sa
        return urlparse.urlunsplit(('http', netloc, path, query, fragment))


class HTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Modifications required to provide the server development
    interface we want.

    This version inverts control relative to the Python standard web
    server hierarchy: Rather than have the supported methods defined
    by the generic handler, we follow REST principles and delegate the
    selection of supported methods to the resources.  A
    :class:`HTTPRequestHandler` class retains in :attr:`_Resources` a
    map from path prefixes to instances of :class:`HTTPResource` which
    in turn provide the methods that are appropriate to that resource.
    Processing is delegated to the registered resource whose
    :attr:`HTTPResource.path` is the longest segment prefix of the
    request URI ``path``.
    """

    split_uri = None
    """The results of invoking :func:`python:urlparse.urlsplit` on
    :attr:`path<python:BaseHTTPServer.BaseHTTPRequestHandler.path>`.
    """

    _Resources = None
    """A map from absolute path segment prefixes to instances of
    :class:`HTTPResource`.
    """

    @classmethod
    def add_resource(cls, resource):
        """Add *resource* to the registry for this class at
        :attr:`resource.path<HTTPResource.path>`.  This function is
        automatically invoked in the constructor for
        :class:`HTTPResource`.
        """
        if cls._Resources is None:
            cls._Resources = {}
        if not isinstance(resource, HTTPResource):
            raise TypeError(resource)
        if resource.path in cls._Resources:
            raise ValueError(resource)
        cls._Resources[resource.path] = resource

    @classmethod
    def remove_resource(cls, resource):
        """Remove *resource* from the registry."""
        del cls._Resources[resource.path]

    @classmethod
    def lookup_resource(cls, path):
        """Find the best registered resource at *path*.

        *path* is a slash-separated hierarchy of path segments.  The
        registered resource for which :attr:`HTTPResource.path`
        matches a segmented prefix of *path* is returned.  If no
        prefix matches, ``None`` is returned.
        """
        segments = path.split('/')
        while segments:
            path = '/'.join(segments)
            resource = cls._Resources.get(path)
            if resource is not None:
                return resource
            segments.pop()
        return None

    # NOTE: The implementation of this method is from Python 2.7
    # BaseHTTPServer.py, modified as marked in the code.
    def handle_one_request(self):
        """Handle a single HTTP request.

        Replace parts of
        :meth:`python:BaseHTTPServer.BaseHTTPRequestHandler.handle_one_request`
        to identify a :class:`HTTPResource` instance using the ``path``
        part of the URI, and delegate all processing (including
        checking for supported methods) to that resource.  If no
        segment prefix of ``path`` is associated with a registered
        resource a 404 error is returned to the client.

        This function assigns :attr:`split_uri`.

        .. note::

           Resource lookup uses the the `path part of the URI
           <http://tools.ietf.org/html/rfc3986.html#section-3.3>`_,
           exclusive of any query or fragment components that may also
           be present in
           :attr:`path<python:BaseHTTPServer.BaseHTTPRequestHandler.path>`.
        """
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                return
            if not self.raw_requestline:
                self.close_connection = 1
                return
            if not self.parse_request():
                # An error code has been sent, just exit
                return
            # >>> Modifications begin here:
            self.split_uri = urlparse.urlsplit(self.path)
            resource = self.lookup_resource(self.split_uri.path)
            if resource is None:
                self.send_error(404)
                return
            resource.handle_request(self)
            # <<< Modifications end here
            self.wfile.flush()  # actually send the response if not already done.
        except socket.timeout, e:
            #a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return


class HTTPResource(object):
    """Class supporting a resource with specific methods.

    Instances of this class are delegates from
    :class:`HTTPRequestHandler` (or a subclass).  The appropriate
    resource is identified by a segment prefix of the
    :attr:`path<HTTPRequestHandler.path>`.  ``do_FOO`` methods are
    implemented in the resource rather than in the request handler.

    *path* is the absolute path to the resource.  *handler_class* is
    (the subclass of) :class:`HTTPRequestHandler` into which the
    created resource will be registered at *path*.

    Note that the architectural model supports multiple instances of a
    resource class at different paths.
    """

    @property
    def path(self):
        """A read-only property specifying the prefix under which
        this resource is registered within :attr:`handler_class`.
        """
        return self.__path

    @property
    def handler_class(self):
        """A read-only property providing the subclass of
        :class:`HTTPRequestHandler` within which this resource is
        registered.
        """
        return self.__handler_class

    def __init__(self, path, handler_class=HTTPRequestHandler):
        if not issubclass(handler_class, HTTPRequestHandler):
            raise TypeError(handler_class)
        self.__path = path
        self.__handler_class = handler_class
        handler_class.add_resource(self)

    def handle_request(self, request):
        """Process a single request.

        The :attr:`command<python:BaseHTTPRequestHandler.command>`
        from the request is append to ``do_`` and the resulting method
        is invoked to execute the operation.  If the command is not
        implemented, a 501 Unsupported Method error is returned to the
        client.
        """
        self.request = request
        mname = 'do_' + request.command
        meth = getattr(self, mname, None)
        if meth is None:
            request.send_error(501, "Unsupported method (%r)" % request.command)
            return
        try:
            meth(request)
        except NotImplementedError:
            request.send_error(501, "Unsupported method (%r)" % request.command)

    def do_HEAD(self, request):
        """Default implementation delegates to :meth:`do_GET` with
        ``head_only=True``.
        """
        self.do_GET(request, head_only=True)

    def do_GET(self, request, head_only=False):
        """Stub for a `GET
        <http://tools.ietf.org/html/rfc2616#section-9.3>`_ method.

        *request* is the instance of :class:`HTTPRequestHandler` that
        has the request-specific data and ability to communicate
        results to the client.  *head_only* is ``False`` normally, but
        may be set to ``True`` to allow this function to also
        implement the `HEAD
        <http://tools.ietf.org/html/rfc2616#section-9.4>`_ method: the
        implementation is responsible for eliding the body of the
        response in that case.
        """
        raise NotImplementedError
