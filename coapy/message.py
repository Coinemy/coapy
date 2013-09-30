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
Something

:copyright: Copyright 2013, Peter A. Bigot
:license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


import random
import struct
import coapy
import coapy.option
import coapy.util


class Message(object):
    """A CoAP message, per :coapsect:`3`.

    A message may be created as *confirmable*, an *acknowledgement*,
    or a *reset* message.  If none of these is specified, it is
    created as a non-confirmable message.

    *code*, *token*, *options*, and *payload* all initialize the
    corresponding attributes of this class and must be acceptable
    values for those attributes.
    """

    __metaclass__ = coapy.util.ReadOnlyMeta

    Ver = coapy.util.ClassReadOnly(1)
    """Version of the CoAP protocol."""

    Type_CON = coapy.util.ClassReadOnly(0)
    """Type for a :meth:`confirmable<is_confirmable>` message."""
    Type_NON = coapy.util.ClassReadOnly(1)
    """Type for a :meth:`confirmable<is_non_confirmable>` message."""
    Type_ACK = coapy.util.ClassReadOnly(2)
    """Type for a :meth:`confirmable<is_acknowledgement>` message."""
    Type_RST = coapy.util.ClassReadOnly(3)
    """Type for a :meth:`confirmable<is_reset>` message."""

    def is_confirmable(self):
        """True if this message is :coapsect:`confirmable<2.1>`,
        i.e. will be :coapsect:`retransmitted<4.2>` for reliability,
        and an acknowledgement or reset is expected.
        """
        return self.Type_CON == self.__type

    def is_non_confirmable(self):
        """True if this message is :coapsect:`non-confirmable<2.1>`,
        meaning the CoAP layer :coapsect:`will not retransmit<4.3>`
        it, and an acknowledgement is not expected.
        """
        return self.Type_NON == self.__type

    def is_acknowledgement(self):
        """True if this message is an :coapsect:`acknowledgement<1.2>`
        that a particular confirmable message with :attr:`messageID`
        was
        received."""
        return self.Type_ACK == self.__type

    def is_reset(self):
        """True if this message is an indication that a particular
        message with :attr:`messageID` arrived but that the receiver
        could not process it."""
        return self.Type_RST == self.__type

    def _get_type(self):
        """The type of the message as :attr:`Type_CON`,
        :attr:`Type_NON`, :attr:`Type_ACK`, or :attr:`Type_RST`.  This
        is a read-only attribute."""
        return self.__type
    messageType = property(_get_type)

    def _get_code(self):
        """The message code, expressed as a tuple ``(class, detail)``
        where *class* is an integer value from 0 through 7 and
        *detail* is an integer value from 0 through 31.

        A code of ``None`` is allowed only when the message is
        created, and a valid code must be assigned before the message
        may be transmitted.

        For convenience, the code may also be set from its packed
        format defined by ``(class << 5) | detail``.  Decimal code
        representation such as ``4.03`` is not supported.
        """
        return self.__code

    def _set_code(self, code):
        if isinstance(code, tuple):
            if 2 != len(code):
                raise ValueError(code)
            (clazz, detail) = code
            if not (0 <= clazz and clazz <= 7):
                raise ValueError(code)
            if not (0 <= detail and detail <= 31):
                raise ValueError(code)
        elif isinstance(code, int):
            if (0 > code) or (255 < code):
                raise ValueError(code)
            code = (code >> 5, code & 0x1F)
        else:
            raise TypeError(code)
        self.__code = code

    code = property(_get_code, _set_code)

    def _get_packed_code(self):
        """Return :attr:`code` in its packed form as an unsigned 8-bit integer.

        This will raise
        :exc:`ValueError<python:exceptions.ValueError>` if
        :attr:`code` has not been assigned.
        """
        if self.__code is None:
            raise ValueError(None)
        return (self.__code[0] << 5) | self.__code[1]

    packed_code = property(_get_packed_code)

    def _get_messageID(self):
        """An integer between 0 and 65535, inclusive, uniquely
        identifying a confirmable or non-confirmable message among
        those recently transmitted by its sender.  This value is used
        to correlate confirmable and non-confirmable messages with
        acknowledgement and reset messages.  It is not used for
        request/response correlation.
        """
        return self.__messageID

    def _set_messageID(self, message_id):
        if not isinstance(message_id, int):
            raise TypeError(message_id)
        if not ((0 <= message_id) and (message_id <= 65535)):
            raise ValueError(message_id)
        self.__messageID = message_id

    messageID = property(_get_messageID, _set_messageID)

    def _get_token(self):
        """The :coapsect:`token<5.3.1>` associated with the message.

        Tokens are used to :coapsect:`match<5.3.2>` requests with
        responses.  ``None`` is used for a message that has no token.
        Otherwise the token must be a :class:`bytes` instance with
        length between 1 and 8 octets, inclusive."""
        return self.__token

    def _set_token(self, token):
        if token is not None:
            if not isinstance(token, bytes):
                raise TypeError(token)
            if not ((1 <= len(token)) and (len(token) <= 8)):
                raise ValueError(token)
        self.__token = token

    token = property(_get_token, _set_token)

    options = None
    """The set of option instances associated with the message.  This
    should be ``None`` or a list of :class:`coapy.option.UrOption`
    subclass instances."""

    def _get_payload(self):
        """The payload or content of the message.  This may be
        ``None`` if no payload exists; otherwise it must be a
        non-empty :class:`bytes` instance.  As a convenience, an empty
        :class:`bytes` string is equivalent to setting the payload to
        ``None``.

        The representation of the payload should be conveyed by a
        :class:`ContentFormat<coapy.option.ContentFormat>` option.
        """
        return self.__payload

    def _set_payload(self, payload):
        if (payload is not None) and not isinstance(payload, bytes):
            raise TypeError(payload)
        if (payload is not None) and (0 == len(payload)):
            payload = None
        self.__payload = payload

    payload = property(_get_payload, _set_payload)

    def __init__(self, confirmable=False, acknowledgement=False, reset=False,
                 code=None, message_id=None, token=None, options=None, payload=None):
        if confirmable:
            self.__type = self.Type_CON
        elif acknowledgement:
            self.__type = self.Type_ACK
        elif reset:
            self.__type = self.Type_RST
        else:
            self.__type = self.Type_NON
        if code is None:
            self.__code = None
        else:
            self.code = code
        if message_id is None:
            self.__messageID = None
        else:
            self.messageID = message_id
        self.token = token
        self.options = options
        self.payload = payload

    def to_packed(self):
        vttkl = (1 << 6) | (self.__type << 4)
        if self.__token is not None:
            vttkl |= 0x0F & len(self.__token)
        elements = []
        elements.append(struct.pack(str('!BBH'), vttkl, self.packed_code, self.messageID))
        if self.__token is not None:
            elements.append(self.__token)
        if self.options:
            elements.append(coapy.option.encode_options(self.options))
        elements.append(b'\xFF')
        if self.__payload:
            elements.append(self.__payload)
        return b''.join(elements)


class Request (Message):
    """Subclass for messages that are requests.

    The following table shows the pre-defined method code values ``(class,
    detail)`` as specified in :coapsect:`12.1.1`:

    =======  ===============  ==================
    Code     Name             Documentation
    =======  ===============  ==================
    (0, 1)   :attr:`GET`      :coapsect:`5.8.1`
    (0, 2)   :attr:`POST`     :coapsect:`5.8.2`
    (0, 3)   :attr:`PUT`      :coapsect:`5.8.3`
    (0, 4)   :attr:`DELETE`   :coapsect:`5.8.4`
    =======  ===============  ==================

    """

    Class = coapy.util.ClassReadOnly(0)
    """The :attr:`Message.code` class component for :class:`Request` messages."""

    GET = coapy.util.ClassReadOnly((0, 1))
    """Retrieve a representation for the requested resource.  See
    :coapsect:`5.8.1`."""

    POST = coapy.util.ClassReadOnly((0, 2))
    """Process the representation enclosed in the requested resource.
    See :coapsect:`5.8.2`."""

    PUT = coapy.util.ClassReadOnly((0, 3))
    """Update or create the resource using the enclosed representation.
    See :coapsect:`5.8.3`."""

    DELETE = coapy.util.ClassReadOnly((0, 4))
    """Delete the resource identified by the request URI.
    See :coapsect:`5.8.4`."""


class SuccessResponse (Message):
    """Subclass for messages that are responses that indicate the
    request was successfully received, understood, and accepted.

    The following table shows the pre-defined :coapsect:`success
    response<5.9.1>` code values ``(class, detail)`` as specified in
    :coapsect:`12.1.2`:

    =======  ================  ====================
    Code     Name              Documentation
    =======  ================  ====================
    (2, 1)   :attr:`Created`   :coapsect:`5.9.1.1`
    (2, 2)   :attr:`Deleted`   :coapsect:`5.9.1.2`
    (2, 3)   :attr:`Valid`     :coapsect:`5.9.1.3`
    (2, 4)   :attr:`Changed`   :coapsect:`5.9.1.4`
    (2, 5)   :attr:`Content`   :coapsect:`5.9.1.4`
    =======  ================  ====================
    """
    Class = coapy.util.ClassReadOnly(2)
    """The :attr:`Message.code` class component for
    :class:`SuccessResponse` messages."""

    Created = coapy.util.ClassReadOnly((2, 1))
    """See :coapsect:`5.9.1.1`."""

    Deleted = coapy.util.ClassReadOnly((2, 2))
    """See :coapsect:`5.9.1.2`."""

    Valid = coapy.util.ClassReadOnly((2, 3))
    """See :coapsect:`5.9.1.3`."""

    Changed = coapy.util.ClassReadOnly((2, 4))
    """See :coapsect:`5.9.1.4`."""

    Content = coapy.util.ClassReadOnly((2, 5))
    """See :coapsect:`5.9.1.5`."""


class ClientErrorResponse (Message):
    """Subclass for messages that are responses in cases where the
    server detects an error in the client's request.

    The following table shows the pre-defined :coapsect:`client error
    response<5.9.2>` code values ``(class, detail)`` as specified in
    :coapsect:`12.1.2`:

    ========  =================================  =====================
    Code      Name                               Documentation
    ========  =================================  =====================
    (4, 0)    :attr:`BadRequest`                 :coapsect:`5.9.2.1`
    (4, 1)    :attr:`Unauthorized`               :coapsect:`5.9.2.2`
    (4, 2)    :attr:`BadOption`                  :coapsect:`5.9.2.3`
    (4, 3)    :attr:`Forbidden`                  :coapsect:`5.9.2.4`
    (4, 4)    :attr:`NotFound`                   :coapsect:`5.9.2.5`
    (4, 5)    :attr:`MethodNotAllowed`           :coapsect:`5.9.2.6`
    (4, 6)    :attr:`NotAcceptable`              :coapsect:`5.9.2.7`
    (4, 12)   :attr:`PreconditionFailed`         :coapsect:`5.9.2.8`
    (4, 13)   :attr:`RequestEntityTooLarge`      :coapsect:`5.9.2.9`
    (4, 15)   :attr:`UnsupportedContentFormat`   :coapsect:`5.9.2.10`
    ========  =================================  =====================
    """

    Class = coapy.util.ClassReadOnly(4)
    """The :attr:`Message.code` class component for
    :class:`ClientErrorResponse` messages."""

    BadRequest = coapy.util.ClassReadOnly((4, 0))
    """See :coapsect:`5.9.2.1`"""

    Unauthorized = coapy.util.ClassReadOnly((4, 1))
    """See :coapsect:`5.9.2.2`"""

    BadOption = coapy.util.ClassReadOnly((4, 2))
    """See :coapsect:`5.9.2.3`"""

    Forbidden = coapy.util.ClassReadOnly((4, 3))
    """See :coapsect:`5.9.2.4`"""

    NotFound = coapy.util.ClassReadOnly((4, 4))
    """See :coapsect:`5.9.2.5`"""

    MethodNotAllowed = coapy.util.ClassReadOnly((4, 5))
    """See :coapsect:`5.9.2.6`"""

    NotAcceptable = coapy.util.ClassReadOnly((4, 6))
    """See :coapsect:`5.9.2.7`"""

    PreconditionFailed = coapy.util.ClassReadOnly((4, 12))
    """See :coapsect:`5.9.2.8`"""

    RequestEntityTooLarge = coapy.util.ClassReadOnly((4, 13))
    """See :coapsect:`5.9.2.9`"""

    UnsupportedContentFormat = coapy.util.ClassReadOnly((4, 15))
    """See :coapsect:`5.9.2.10`"""


class ServerErrorResponse (Message):
    """Subclass for messages that are responses that indicate the
    server is incapable of performing the request.

    The following table shows the pre-defined :coapsect:`server error
    response<5.9.3>` code values ``(class, detail)`` as specified in
    :coapsect:`12.1.2`:

    ========  =================================  =====================
    Code      Name                               Documentation
    ========  =================================  =====================
    (5, 0)    :attr:`InternalServerError`        :coapsect:`5.9.3.1`
    (5, 1)    :attr:`NotImplemented`             :coapsect:`5.9.3.2`
    (5, 2)    :attr:`BadGateway`                 :coapsect:`5.9.3.3`
    (5, 3)    :attr:`ServiceUnavailable`         :coapsect:`5.9.3.4`
    (5, 4)    :attr:`GatewayTimeout`             :coapsect:`5.9.3.5`
    (5, 5)    :attr:`ProxyingNotSupported`       :coapsect:`5.9.3.6`
    ========  =================================  =====================
    """

    Class = coapy.util.ClassReadOnly(5)
    """The :attr:`Message.code` class component for
    :class:`ServerErrorResponse` messages."""

    InternalServerError = coapy.util.ClassReadOnly((5, 0))
    """See :coapsect:`5.9.3.1`"""

    NotImplemented = coapy.util.ClassReadOnly((5, 1))
    """See :coapsect:`5.9.3.2`"""

    BadGateway = coapy.util.ClassReadOnly((5, 2))
    """See :coapsect:`5.9.3.3`"""

    ServiceUnavailable = coapy.util.ClassReadOnly((5, 3))
    """See :coapsect:`5.9.3.4`"""

    GatewayTimeout = coapy.util.ClassReadOnly((5, 4))
    """See :coapsect:`5.9.3.5`"""

    ProxyingNotSupported = coapy.util.ClassReadOnly((5, 5))
    """See :coapsect:`5.9.3.6`"""


class TransmissionParameters(object):
    """The :coapsect:`transmission parameters<4.8>` that support
    message transmission behavior including :coapsect:`congestion
    control<4.7>` in CoAP.

    Some of these parameters are primitive, and some are derived.
    Consult :coapsect:`4.8.1` for information related to changing
    these parameters.  After changing the primitive parameters in an
    instance, invoke :func:`recalculate_derived` to update the derived
    parameters.

    ==========================  ==============  ==================  ==========
    Parameter                   Units           Documentation       Class
    ==========================  ==============  ==================  ==========
    :attr:`ACK_TIMEOUT`         seconds         :coapsect:`4.8`     Primitive
    :attr:`ACK_RANDOM_FACTOR`   seconds         :coapsect:`4.8`     Primitive
    :attr:`MAX_RETRANSMIT`      transmissions   :coapsect:`4.8`     Primitive
    :attr:`NSTART`              messages        :coapsect:`4.7`     Primitive
    :attr:`DEFAULT_LEISURE`     seconds         :coapsect:`8.2`     Primitive
    :attr:`PROBING_RATE`        bytes/second    :coapsect:`4.7`     Primitive
    :attr:`MAX_LATENCY`         seconds         :coapsect:`4.8.2`   Primitive
    :attr:`PROCESSING_DELAY`    seconds         :coapsect:`4.8.2`   Primitive
    :attr:`MAX_TRANSMIT_SPAN`   seconds         :coapsect:`4.8.2`   Derived
    :attr:`MAX_TRANSMIT_WAIT`   seconds         :coapsect:`4.8.2`   Derived
    :attr:`MAX_RTT`             seconds         :coapsect:`4.8.2`   Derived
    :attr:`EXCHANGE_LIFETIME`   seconds         :coapsect:`4.8.2`   Derived
    :attr:`NON_LIFETIME`        seconds         :coapsect:`4.8.2`   Derived
    ==========================  ==============  ==================  ==========

    """

    ACK_TIMEOUT = 2
    """The initial timeout waiting for an acknowledgement, in seconds."""

    ACK_RANDOM_FACTOR = 1.5
    """A randomization factor to avoid synchronization, in seconds."""

    MAX_RETRANSMIT = 4
    """The maximum number of retransmissions of a confirmable message.
    A value of 4 produces a maximum of 5 transmissions when the first
    transmission is included."""

    NSTART = 1
    """The maximum number of messages permitted to be outstanding for
    an endpoint."""

    DEFAULT_LEISURE = 5
    """A duration, in seconds, that a server may delay before
    responding to a multicast message."""

    PROBING_RATE = 1
    """The target maximum average data rate, in bytes per second, for
    transmissions to an endpoint that does not respond."""

    MAX_LATENCY = 100
    """The maximum time, in seconds, expected from the start of
    datagram transmission to completion of its reception.  This
    includes endpoint transport-, link-, and physical-layer
    processing, propagation delay through the communications medium,
    and intermediate routing overhead."""

    PROCESSING_DELAY = ACK_TIMEOUT
    """The maximum time, in seconds, that node requires to generate an
    acknowledgement to a confirmable message."""

    MAX_TRANSMIT_SPAN = 45
    """Maximum time, in seconds, from first transmission of a
    confirmable message to its last retransmission.."""

    MAX_TRANSMIT_WAIT = 93
    """Maximum time, in seconds, from first transmission of a
    confirmable message to when the sender may give up on receiving
    acknowledgement or reset."""

    MAX_RTT = 202
    """Maximum round-trip-time, in seconds, considering
    :attr:`MAX_LATENCY` and :attr:`PROCESSING_DELAY`."""

    EXCHANGE_LIFETIME = 247
    """Time, in seconds, from first transmission of a confirmable
    message to when an acknowledgement is no longer expected."""

    NON_LIFETIME = 145
    """Time, in seconds, from transmission of a non-confirmable
    message to when its Message-ID may be safely re-used."""

    def recalculate_derived(self):
        """Calculate values for parameters that may be derived.

        This uses the calculations in :coapsect:`4.8.2` to calculate
        :attr:`MAX_TRANSMIT_SPAN`, :attr:`MAX_TRANSMIT_WAIT`,
        :attr:`MAX_RTT`, :attr:`EXCHANGE_LIFETIME`, and
        :attr:`NON_LIFETIME` from other parameters in the instance.
        """
        self.MAX_TRANSMIT_SPAN = \
            self.ACK_TIMEOUT \
            * ((1 << self.MAX_RETRANSMIT) - 1) \
            * self.ACK_RANDOM_FACTOR
        self.MAX_TRANSMIT_WAIT = \
            self.ACK_TIMEOUT \
            * ((1 << (self.MAX_RETRANSMIT + 1)) - 1) \
            * self.ACK_RANDOM_FACTOR
        self.MAX_RTT = (2 * self.MAX_LATENCY) + self.PROCESSING_DELAY
        self.EXCHANGE_LIFETIME = self.MAX_TRANSMIT_SPAN + self.MAX_RTT
        self.NON_LIFETIME = self.MAX_TRANSMIT_SPAN + self.MAX_LATENCY

    def timeout_control(self, initial_timeout=None, max_retransmissions=None):
        return RetransmissionState(initial_timeout=initial_timeout,
                                   max_retransmissions=max_retransmissions,
                                   transmission_parameters=self)


class RetransmissionState (object):
    """An iterable that provides the time to the next retransmission.

    *initial_timeout* is the time, in seconds, to the first
    retransmission; a default is calculated from
    *transmission_parameters* if provided.

    *max_retransmissions* is the maximum number of re-transmissions; a
    default is obtained from *transmission_parameters* if provided.

    Thus::

      list(RetransmissionState(3,4))

    will produce::

      [3, 6, 12, 24]

    """
    def __init__(self, initial_timeout=None,
                 max_retransmissions=None, transmission_parameters=None):
        if (not isinstance(transmission_parameters, TransmissionParameters)
            and ((initial_timeout is None)
                 or (max_retransmissions is None))):
            raise ValueError
        if initial_timeout is None:
            initial_timeout = \
                transmission_parameters.ACK_TIMEOUT \
                + random.random() * transmission_parameters.ACK_RANDOM_FACTOR
        if max_retransmissions is None:
            max_retransmissions = transmission_parameters.MAX_RETRANSMIT
        self.timeout = initial_timeout
        self.max_retransmissions = max_retransmissions
        self.counter = 0

    def __iter__(self):
        return self

    def _get_remaining(self):
        """The number of retransmissions remaining in the iterator."""
        return self.max_retransmissions - self.counter
    retransmissions_remaining = property(_get_remaining)

    def next(self):
        if self.counter >= self.max_retransmissions:
            raise StopIteration
        rv = self.timeout
        self.counter += 1
        self.timeout += self.timeout
        return rv
