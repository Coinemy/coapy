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
    *****
    coapy
    *****

    :copyright: Copyright 2013, Peter A. Bigot
    :license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
_log = logging.getLogger(__name__)


COAP_PORT = 5683
"""The IANA-assigned default port number for unsecured CoAP (the
"coap" URI scheme).
"""

COAPS_PORT = 0
"""The IANA-assigned default port number for secured CoAP (the "coaps"
URI scheme).
"""


class CoAPyException (Exception):
    pass


class InfrastructureError (CoAPyException):
    pass


transmissionParameters = None
"""The default instance of
:class:`TransmissionParameters<coapy.message.TransmissionParameters>`
for the system.

This is initialized when :mod:`coapy.message` is first loaded.
"""


import time
clock = time.time
"""The system clock.

This is a callable that returns a non-decreasing ordinal (probably a
:class:`python:float` but possibly an :class:`python:int`).  The
integer part increments in "seconds".  It is used for
:class:`Max-Age<coapy.option.MaxAge>`, state related to
:coapsect:`congestion control<4.7>` and :coapsect:`message
retransmission<4.2>`, and other time-related phenomena.

.. note::
   The default value is :func:`python:time.time`, but this may be
   overridden for the purposes of simulation or testing.  Unless
   you're doing this sort of thing, you should assume it increments in
   lock step with real-world time.
"""


# In sphinx 1.2 use :novalue: to prevent the documentation from
# claiming this is a constant 1380879789.119847 or similar silliness.
epoch = clock()
"""The value of :data:`clock()<clock>` at a point corresponding to
"system start".

Set implicitly when the :mod:`coapy` module is first loaded.
"""
