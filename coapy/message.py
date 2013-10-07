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

import logging
_log = logging.getLogger(__name__)

import random
import struct
import bisect
import coapy
import coapy.option
import coapy.util


class MessageError (coapy.CoAPyException):
    pass


class MessageValidationError (MessageError):
    """Exception raised by :meth:`Message.validate`.  :attr:`args`
    will be ``(diagnostic, message)`` where *diagnostic* is a
    human-readable description of the failure cause matching one of
    the codes in this class, and *message* is the invalid message.
    """
    CODE_UNDEFINED = 'missing code'
    """*diagnostic* value when caller failed to assign a value to
    :attr:`Message.code`
    """

    CODE_INSTANCE_CONFLICT = 'code inconsistent with message class'
    """*diagnostic* value when the *class* in :attr:`Message.code` is
    not compatible with the Python class of the message instance.
    """

    CODE_TYPE_CONFLICT = 'code and messageType conflict'
    """*diagnostic* value when :attr:`Message.code` and
    :attr:`Message.messageType` are not consistent:

    * :attr:`CON<Message.Type_CON>` and :attr:`NON<Message.Type_NON>`
      allowed only in :class:`Request` and :class:`Response` messages.

    * :attr:`ACK<Message.Type_ACK>` allowed only for
      :attr:`Empty<Message.Empty>` and :class:`Response` messages.

    * :attr:`RST<Message.Type_RST>` allowed only for
      :attr:`Empty<Message.Empty>` messages.
    """

    EMPTY_MESSAGE_NOT_EMPTY = 'excess content in Empty message'
    """*diagnostic* value when a message with code
    :attr:`Empty<Message.Empty>` has a non-empty
    :attr:`Message.token`, :attr:`Message.options`, or
    :attr:`Message.payload` attribute.
    """

    PROXY_URI_CONFLICT = 'Proxy-Uri mixed with Uri-*'
    """*diagnostic* value when *message* has both
    :class:`coapy.option.ProxyUri` and at least one of
    :class:`coapy.option.UriHost`, :class:`coapy.option.UriPort`,
    :class:`coapy.option.UriPath`, or :class:`coapy.option.UriQuery`.
    """


class MessageFormatError (MessageError):
    """Exception raised by :meth:`Message.from_packed` when the
    message cannot be decoded.  :attr:`args` will be ``(diagnostic,
    dkw)`` where *diagnostic* is a human-readable description of the
    failure cause matching one of the codes in this class, and *dkw*
    is a dictionary with entries for
    :attr:`type<Message.messageType>`, :attr:`code<Message.code>` and
    :attr:`messageID<Message.messageID>`.

    Justification for the diagnosis can be found in :coapsect:`3`.
    """

    TOKEN_TOO_LONG = 'token too long'
    """*diagnostic* value when the TKL field of the message is greater
    than 8.
    """

    ZERO_LENGTH_PAYLOAD = 'zero-length payload'
    """*diagnostic* value when a Payload Marker is present but not
    followed by data.
    """

    INVALID_OPTION = 'option decode error'
    """*diagnostic* value when an Option Delta is 15 in a value that
    is not a Payload Marker, or an Option Delta is 15 in a value that
    is not a Payload Marker.
    """

    EMPTY_MESSAGE_NOT_EMPTY = 'excess content in Empty message'
    """*diagnostic* value when a message with code
    :attr:`Empty<Message.Empty>` has bytes after the Message ID
    field.
    """

    UNRECOGNIZED_CODE_CLASS = 'unrecognized code class'
    """*diagnostic* when the :attr:`code<Message.code>` has no generic
    handler (e.g. the message code class is 1, 6, and 7 which are
    currently reserved).

    Technically this is not a message format error, but CoAP requires
    that it be treated the same way wherever the possibility is
    explicitly recognized (:coapsect:`4.2` and :coapsect:`4.3`).
    """


class MessageIDCacheEntry (coapy.util.TimeDueOrdinal):
    """A class holding data stored in a :class:`MessageIDCache`.

    Instances sort based on
    :attr:`coapy.util.TimeDueOrdinal.time_due`, and may be looked up
    based on :attr:`message_id`.

    Keyword parameters recognized:

    * *cache* identifies the
      :class:`MessageIDCache` instance to which this entry will
      belong.
    * *message* is a :class:`Message` instance from which :attr:`Message.messageID`
      is used to initialize :attr:`message_id`
    * *message_id* is used to initialize :attr:`message_id` if
      *message* is absent
    * *time_due* is used to initialize :attr:`coapy.util.TimeDueOrdinal.time_due`

    *cache* is a required keyword parameter.  One of *message* and
     *message_id* must also be provided.  The created cache entry is
     automatically inserted into the cache upon creation.
    """

    __cache = None

    def _dissociate(self):
        """Remove the connection between the instance and the cache.

        This is invoked by :class:`MessageIDCache` operations that
        remove the entry from its cache.
        """
        self.__cache = None

    @property
    def cache(self):
        """The :class:`MessageIDCache` to which this entry belongs.
        This is a read-only property, set when the entry is created
        and cleared when it has been removed from its cache.
        """
        return self.__cache

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

    message_id = None
    """The :attr:`Message.messageID` value associated with the cache
    entry.
    """

    def __init__(self, **kw):
        cache = kw.pop('cache', None)
        message = kw.pop('message', None)
        message_id = kw.pop('message_id', None)
        super(MessageIDCacheEntry, self).__init__(**kw)
        if isinstance(message, Message):
            self.message_id = message.messageID
        elif isinstance(message_id, int):
            self.message_id = message_id
        else:
            raise TypeError(message_id)
        if not isinstance(cache, MessageIDCache):
            raise TypeError(cache)
        self.__cache = cache
        cache._add(self)


class MessageIDCache (object):
    """Dual-view collection used for caches based on :attr:`Message.messageID`.

    This class implements a cache.  It simulates a dictionary allowing
    lookup of items using :attr:`Message.messageID` values as keys.  It also
    simulates a priority queue, allowing items to be removed from the
    cache based on age.

    Elements in the cache are expected to be instances of
    :class:`MessageIDCacheEntry`.  Most lookup :class:`python:dict`
    operations are supported.

    Cache entries are placed in the cache when they are created.  It
    is an error to create a new cache entry when one with the same
    :attr:`MessageIDCacheEntry.message_id` is already present.

    Entries are removed from the cache by using :meth:`pop_oldest`.

    Entry content may be updated while in the cache, but once removed
    from the cache an entry cannot be re-inserted.
    """
    __queue = None
    __dict = None

    def __init__(self):
        self.__queue = []
        self.__dict = {}
        self.keys = self.__dict.keys
        self.values = self.__dict.values
        self.items = self.__dict.items
        self.has_key = self.__dict.has_key
        self.get = self.__dict.get
        # clear
        # setdefault
        self.iterkeys = self.__dict.iterkeys
        self.itervalues = self.__dict.itervalues
        self.iteritems = self.__dict.iteritems
        # pop
        # popitem
        # copy
        # update

    def queue(self):
        """The queue of cache entries sorted by :attr:`MessageIDCacheEntry.time_due`.

        .. warning::
           This method returns a reference to the underlying sorted
           list.  Callers are expected to refrain from changing the
           list in any way other than through methods exposed on the
           cache itself.
        """
        return self.__queue

    def peek_oldest(self):
        """Return the oldest item in the cache without removing it."""
        return self.__queue[0]

    def pop_oldest(self):
        """Return the oldest item in the cache after removing it."""
        rv = self.__queue.pop(0)
        del self.__dict[rv.message_id]
        rv._dissociate()
        return rv

    def _add(self, value):
        """Add *value* to the cache.
        """
        if not isinstance(value, MessageIDCacheEntry):
            raise ValueError(value)
        if value.message_id in self.__dict:
            raise ValueError(value)
        bisect.insort(self.__queue, value)
        self.__dict[value.message_id] = value

    def _reposition(self, value):
        """Re-place *value* at its correct location in the queue.

        This must be invoked whenever the underlying
        :attr:`coapy.util.TimeDueOrdinal.time_due` attribute value is
        changed."""
        bisect.insort(self.__queue, self.__queue.pop(self.__queue.index(value)))

    def __len__(self):
        return len(self.__queue)

    def __getitem__(self, key):
        return self.__dict[key]

    def __contains__(self, key):
        return key in self.__dict


class Message(object):
    """A CoAP message, per :coapsect:`3`.

    A message may be created as *confirmable*, an *acknowledgement*,
    or a *reset* message.  If none of these is specified, it is
    created as a non-confirmable message.

    *code*, *messageID*, *token*, *options*, and *payload* all
    initialize the corresponding attributes of this class and if
    provided must be acceptable values for those attributes.

    .. note::
       The default values for *code*, *messageID*, and *token* are not
       valid for :attr:`code`, :attr:`messageID`, and :attr:`token`
       respectively.  Valid values must be assigned before the message
       is used.
    """

    __metaclass__ = coapy.util.ReadOnlyMeta

    CodeClass = None
    """Identifier for message class.

    In subclasses this is a read-only attribute giving the numeric
    value of the *class* component of :attr:`code` values for classes.
    This serves as a key to identify the appropriate constructor when
    creating messages from packed format.
    """

    class _CodeSupport (object):
        code = None
        """The CoAP message code to which other attributes apply.
        This is the ``(class, detail)`` representation.
        """

        name = None
        """The text name of the particular code within its class."""

        constructor = None
        """The subclass of :class:`Message` that should be used to
        construct messages with :attr:`code`.
        """

        def __init__(self, code, name, constructor):
            self.code = code
            self.name = name
            self.constructor = constructor

    # Registry from code tuples to assorted information about messages
    # with that code.
    __CodeRegistry = {}

    @classmethod
    def RegisterClassCode(cls, clazz, constructor=None):
        """Register a fallback-constructor for messages in a code
        *class*.

        This is used when no more specific information can be resolved
        by using the *details* field of the message code.
        """
        if not isinstance(clazz, int):
            raise TypeError
        cls.__CodeClassRegistry[clazz] = cls

    # Registry from code classes to the primary Python type used for
    # messages in that class.  This is for fall-backs when the details
    # is unrecognized but we still have to do class-specific actions
    # on the message.
    __CodeClassRegistry = {}

    @classmethod
    def RegisterCode(cls, code, name, constructor=None):
        """Register some information about messages with a particular code.

        This allows extensions to add new codes as the IANA registries
        are updated.  It also allows the Python version of decoded
        messages to be created using the most appropriate subclass of
        :class:`Message`.

        *code* must be a valid code expressed in tuple form.  *name*
        is the standardized text name or description from the
        corresponding IANA registry.  *constructor* is the callable
        that takes the same arguments as :class:`Message` and creates
        a new instance of the class best suited for messages with code
        *code*.  The constructor defaults to *cls* if not provided.

        This method should be invoked through the subclass that is
        responsible for *code*, e.g. :class:`Request` for
        :attr:`Request.GET`.  See examples of use in the
        :mod:`coapy.message` source code.
        """
        assert code == cls.code_as_tuple(code)
        if constructor is None:
            constructor = cls
        if code in cls.__CodeRegistry:
            raise ValueError(code)
        if cls.CodeClass is not None:
            if code[0] != cls.CodeClass:
                raise ValueError(code)
            if code[0] not in cls.__CodeClassRegistry:
                cls.RegisterClassCode(cls.CodeClass, cls)
        cls.__CodeRegistry[code] = cls._CodeSupport(code, name, constructor)

    @classmethod
    def _code_support(cls, code):
        return cls.__CodeRegistry.get(cls.code_as_tuple(code))

    @classmethod
    def _type_for_code(cls, code):
        cs = cls._code_support(code)
        if cs is not None:
            return cs.constructor
        return cls.__CodeClassRegistry.get(code[0])

    def code_support(self):
        return self._code_support(self.code)

    Empty = coapy.util.ClassReadOnly((0, 0))
    """Code for a message that is neither a request nor a response.
    This is used for message-layer non-piggybacked ACK and for RST.
    """

    Ver = coapy.util.ClassReadOnly(1)
    """Version of the CoAP protocol."""

    Type_CON = coapy.util.ClassReadOnly(0)
    """Type for a :meth:`confirmable (CON)<is_confirmable>` message."""
    Type_NON = coapy.util.ClassReadOnly(1)
    """Type for a :meth:`non-confirmable (NON)<is_non_confirmable>` message."""
    Type_ACK = coapy.util.ClassReadOnly(2)
    """Type for a :meth:`acknowledgement (ACK)<is_acknowledgement>` message."""
    Type_RST = coapy.util.ClassReadOnly(3)
    """Type for a :meth:`reset (RST)<is_reset>` message."""

    def source_defines_messageID(self):
        """True if this message is :attr:`CON<Type_CON>` or :attr:`NON<Type_NON>`.

        :attr:`CON<Type_CON>` and :attr:`NON<Type_NON>` messages are
        responsible for selecting a :attr:`messageID` at the
        :attr:`source_endpoint`.

        :attr:`ACK<Type_ACK>` and :attr:`RST<Type_RST>` messages are
        message-level responses to a :attr:`messageID` that was
        selected by their :attr:`destination_endpoint`.
        """
        return 0 == (0x02 & self.__type)

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
        was received.
        """
        return self.Type_ACK == self.__type

    def is_reset(self):
        """True if this message is an indication that a particular
        message with :attr:`messageID` arrived but that the receiver
        could not process it.
        """
        return self.Type_RST == self.__type

    def _get_type(self):
        """The type of the message as :attr:`Type_CON`,
        :attr:`Type_NON`, :attr:`Type_ACK`, or :attr:`Type_RST`.  This
        is a read-only attribute.
        """
        return self.__type
    messageType = property(_get_type)

    def _get_type_name(self):
        """The type of the message as a three-letter descriptive name
        (:attr:`CON<Type_CON>`, :attr:`NON<Type_NON>`,
        :attr:`ACK<Type_ACK>`, :attr:`RST<Type_RST>`).  This is a
        read-only attribute.
        """
        return ('CON', 'NON', 'ACK', 'RST')[self.__type]
    messageTypeName = property(_get_type_name)

    @staticmethod
    def code_as_tuple(code):
        """Validate *code* and return it as a ``(class, detail)`` tuple."""
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
        return code

    @staticmethod
    def code_as_integer(code):
        """Validate *code* and return it as an integer.

        The packed encoding of ``(class, detail)`` has the 3-bit code
        class combined with the 5-bit code detail, as: ``(class << 5)
        | detail``.
        """
        (clazz, detail) = Message.code_as_tuple(code)
        return (clazz << 5) | detail

    def _get_code(self):
        """The message code, expressed as a tuple ``(class, detail)``
        where *class* is an integer value from 0 through 7 and
        *detail* is an integer value from 0 through 31.

        A code of ``None`` is allowed only when a raw :class:`Message`
        is created, and a valid code must be assigned before the
        message may be transmitted.

        For convenience, the code may also be set from its packed
        format defined by ``(class << 5) | detail``.  Decimal code
        representation such as ``4.03`` is not supported.
        """
        return self.__code

    def _set_code(self, code):
        self.__code = self.code_as_tuple(code)

    code = property(_get_code, _set_code)

    def _get_packed_code(self):
        """Return :attr:`code` in its packed form as an unsigned 8-bit integer.

        This will raise
        :exc:`ValueError<python:exceptions.ValueError>` if
        :attr:`code` has not been assigned.
        """
        if self.__code is None:
            raise ValueError(None)
        return self.code_as_integer(self.__code)

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
        responses.  The token must be a :class:`bytes` instance with
        length between 0 and 8 octets, inclusive.
        """
        return self.__token

    def _set_token(self, token):
        if not isinstance(token, bytes):
            raise TypeError(token)
        if len(token) > 8:
            raise ValueError(token)
        self.__token = token

    token = property(_get_token, _set_token)

    def _get_options(self):
        """The list of :coapsect:`options<5.10>` associated with the
        message.

        Absence of options is represented by an empty list.  Elements
        of the list must be :class:`coapy.option.UrOption` (subclass)
        instances.  The list object is owned by the message instance.
        Assignment to it will replace its contents.  The contents will
        be rearranged in a stable sort by option
        :attr:`number<coapy.option.UrOption.number>` as needed by
        operations performed on the message.
        """
        return self.__options

    def _set_options(self, value):
        self.__options[:] = coapy.option.sorted_options(value)

    def _sort_options(self):
        """Sort the :attr:`options` list and return a reference to it.
        """
        self.__options[:] = coapy.option.sorted_options(self.__options)
        return self.__options

    options = property(_get_options, _set_options)

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
                 code=None, messageID=None, token=None, options=None, payload=None):
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
        if messageID is None:
            self.__messageID = None
        else:
            self.messageID = messageID
        if token is None:
            self.__token = None
        else:
            self.token = token
        self.__options = []
        if options is not None:
            self.options = options
        self.payload = payload

    def to_packed(self):
        """Generate the packed representation of the message, per :coapsect:`3`.

        The result is a :class:`bytes` instance.
        """

        vttkl = (1 << 6) | (self.__type << 4)
        vttkl |= 0x0F & len(self.__token)
        elements = []
        elements.append(struct.pack(str('!BBH'), vttkl, self.packed_code, self.messageID))
        elements.append(self.__token)
        if self.options:
            elements.append(coapy.option.encode_options(self.options))
        if self.__payload:
            elements.append(b'\xFF')
            elements.append(self.__payload)
        return b''.join(elements)

    @classmethod
    def from_packed(cls, packed_message):
        """Create a :class:`Message` (or subclass) instance from the
        packed representation of a message, per :coapsect:`3`.

        This will return ``None`` if the first four octets cannot be
        successfully decoded; such messages should be silently ignored.

        It will raise a :exc:`MessageFormatError` when
        :attr:`type<messageType>`, :attr:`code` and :attr:`messageID`
        information can be extracted but the message as a whole is
        malformatted. :coapsect:`4` specifies the receiver MUST
        (:attr:`CON<Type_CON>`) or may (:attr:`NON<Type_NON>`) or MUST
        NOT (:attr:`ACK<Type_ACK>`, :attr:`RST<Type_RST>`) reply with
        a Reset message, and otherwise the message is ignored (from a
        protocol perspective; the receiver may use the failure as a
        cue to perform some other action; see :coapsect:`5.7.1` for
        example).

        Otherwise it will return an instance of :class:`Message` or a
        refined subclass based on the :attr:`code` within the packed
        representation.
        """

        if not isinstance(packed_message, bytes):
            raise TypeError(packed_message)
        data = bytearray(packed_message)
        vttkl = data.pop(0)
        ver = (vttkl >> 6)
        if ver != cls.Ver:
            # 3: Unknown version number: silently ignore
            return None
        message_type = 0x03 & (vttkl >> 4)
        tkl = 0x0F & vttkl
        code = cls.code_as_tuple(data.pop(0))
        message_id = data.pop(0)
        message_id = (message_id << 8) | data.pop(0)
        dkw = {'type': message_type,
               'code': code,
               'messageID': message_id}
        if 9 <= tkl:
            raise MessageFormatError(MessageFormatError.TOKEN_TOO_LONG, dkw)
        if ((cls.Empty == code) and ((0 != tkl) or (0 < len(data)))):
            raise MessageFormatError(MessageFormatError.EMPTY_MESSAGE_NOT_EMPTY, dkw)
        token = bytes(data[:tkl])
        if 0 < tkl:
            data[:tkl] = b''
        try:
            (options, remainder) = coapy.option.decode_options(bytes(data))
        except coapy.option.OptionDecodeError as e:
            # This can be an invalid delta or length in the first byte,
            # or a value field that does not conform to the requirements.
            # @todo@ refine this
            raise MessageFormatError(MessageFormatError.INVALID_OPTION, dkw)
        payload = None
        if 0 < len(remainder):
            data = bytearray(remainder)
            if 0xFF != data[0]:
                # This should have been interpreted as an option decode error
                raise MessageFormatError(MessageFormatError.INVALID_OPTION, dkw)
            payload = remainder[1:]
            if 0 == len(payload):
                raise MessageFormatError(MessageFormatError.ZERO_LENGTH_PAYLOAD, dkw)
        kw = {'confirmable': (cls.Type_CON == message_type),
              'acknowledgement': (cls.Type_ACK == message_type),
              'reset': (cls.Type_RST == message_type),
              'code': code,
              'messageID': message_id,
              'token': token,
              'options': options,
              'payload': payload
              }
        constructor = cls._type_for_code(code)
        if constructor is None:
            raise MessageFormatError(MessageFormatError.UNRECOGNIZED_CODE_CLASS, dkw)
        return constructor(**kw)

    __source_endpoint = None

    def _set_source_endpoint(self, ep):
        import coapy.endpoint
        if not isinstance(ep, coapy.endpoint.Endpoint):
            raise TypeError
        if (self.__source_endpoint is not None) and (self.__source_endpoint is not ep):
            raise ValueError
        self.__source_endpoint = ep

    def _get_source_endpoint(self):
        """Return the :coapsect:`source endpoint<1.2>` of the message.

        This is the :class:`coapy.endpoint.Endpoint` instance that
        sent (or will send) the message.  It starts as ``None``, and
        can be assigned a value once after which it is immutable.
        Generally the infrastructure should be responsible for
        assigning a source endpoint to a message.

        See also :attr:`destination_endpoint`.
        """
        return self.__source_endpoint

    source_endpoint = property(_get_source_endpoint, _set_source_endpoint)

    __destination_endpoint = None

    def _set_destination_endpoint(self, ep):
        import coapy.endpoint
        if not isinstance(ep, coapy.endpoint.Endpoint):
            raise TypeError
        if (self.__destination_endpoint is not None) and (self.__destination_endpoint is not ep):
            raise ValueError
        self.__destination_endpoint = ep

    def _get_destination_endpoint(self):
        """Return the :coapsect:`destination endpoint<1.2>` of the message.

        This is the :class:`coapy.endpoint.Endpoint` instance to which
        the message was (or will be) sent, i.e. the one on which it
        was (or should be) received.  It starts as ``None``, and can
        be assigned a value once after which it is immutable.
        Generally the infrastructure should be responsible for
        assigning a destination endpoint to a message.

        See also :attr:`source_endpoint`.
        """
        return self.__destination_endpoint

    destination_endpoint = property(_get_destination_endpoint, _set_destination_endpoint)

    def validate(self):
        """Validate a message against generic CoAP requirements.

        A :exc:`MessageValidationError` exception is raised if the
        validation fails.

        Diagnostics will be emitted for any
        :class:`coapy.option.UnrecognizedOption` remaining in the
        message after validation.
        """

        if self.code is None:
            raise MessageValidationError(MessageValidationError.CODE_UNDEFINED, self)

        if self.Empty == self.code:
            # Empty OK for all message types.
            # Empty OK for all message subclasses.
            if self.token or self.options or self.payload:
                raise MessageValidationError(MessageValidationError.EMPTY_MESSAGE_NOT_EMPTY, self)
        else:
            # Is code consistent with message (CoAP) type?
            if self.is_reset():
                raise MessageValidationError(MessageValidationError.CODE_TYPE_CONFLICT, self)
            elif self.is_acknowledgement():
                if not isinstance(self, Response):
                    raise MessageValidationError(MessageValidationError.CODE_TYPE_CONFLICT, self)
            else:
                if not isinstance(self, (Response, Request)):
                    raise MessageValidationError(MessageValidationError.CODE_TYPE_CONFLICT, self)
            # Is code consistent with message (Python) class?
            ctor = self._type_for_code(self.code)
            if (ctor is not None) and not isinstance(self, ctor):
                raise MessageValidationError(MessageValidationError.CODE_INSTANCE_CONFLICT, self)

        if isinstance(self, (Response, Request)):
            self.options[:] = coapy.option.replace_unacceptable_options(self.options,
                                                                        isinstance(self, Request))
        opts = self._sort_options()
        if isinstance(self, Request):
            for opt in filter(lambda _o: isinstance(_o, coapy.option.ProxyUri), opts):
                if 0 < len(list(filter(lambda _o: isinstance(_o,
                                                             (coapy.option.UriHost,
                                                              coapy.option.UriPort,
                                                              coapy.option.UriPath,
                                                              coapy.option.UriQuery,
                                                              )), opts))):
                    raise MessageValidationError(MessageValidationError.PROXY_URI_CONFLICT, self)
                break
        for opt in opts:
            if isinstance(opt, coapy.option.UnrecognizedOption):
                _log.warn('Unrecognized option in message: {0!s}'.format(opt))

    def __unicode__(self):
        elt = []
        if self.messageID is None:
            elt.append('[*INVALID None*]')
        else:
            elt.append('[{m.messageID:d}]'.format(m=self))
        elt.append(' {m.messageTypeName}'.format(m=self))
        if self.code is None:
            elt.append(' ?.?? (*INVALID None*)')
        else:
            elt.append(' {m.code[0]}.{m.code[1]:02d}'.format(m=self))
            cs = self.code_support()
            if cs is not None:
                elt.append(' ({cs.name})'.format(cs=cs))
        if self.source_endpoint is not None:
            elt.append('\nSource: {m.source_endpoint!s}'.format(m=self))
        if self.destination_endpoint is not None:
            elt.append('\nDestination: {m.destination_endpoint!s}'.format(m=self))
        if self.token is None:
            elt.append('\nToken: **INVALID None**')
        elif 0 < len(self.token):
            elt.append('\nToken: {m.token!s}'.format(m=self))
        for opt in self._sort_options():
            elt.append('\nOption {0!s}'.format(opt))
        if self.payload is not None:
            elt.append('\nPayload: {m.payload}'.format(m=self))
        return ''.join(elt)
    __str__ = __unicode__

Message.RegisterCode(Message.Empty, 'Empty')


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

    CodeClass = coapy.util.ClassReadOnly(0)
    """The :attr:`Message.code` *class* component for :class:`Request`
    messages.
    """

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
Request.RegisterCode(Request.GET, 'GET')
Request.RegisterCode(Request.POST, 'POST')
Request.RegisterCode(Request.PUT, 'PUT')
Request.RegisterCode(Request.DELETE, 'DELETE')


class Response (Message):
    """Subclass for messages that are responses.

    Some of the semantics of CoAP depends on distinguishing requests
    from responses; use this as an intermediary class for common
    handling of :class:`SuccessResponse`,
    :class:`ClientErrorResponse`, and :class:`ServerErrorResponse`.
    """
    pass


class SuccessResponse (Response):
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
    CodeClass = coapy.util.ClassReadOnly(2)
    """The :attr:`Message.code` *class* component for
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
SuccessResponse.RegisterCode(SuccessResponse.Created, 'Created')
SuccessResponse.RegisterCode(SuccessResponse.Deleted, 'Deleted')
SuccessResponse.RegisterCode(SuccessResponse.Valid, 'Valid')
SuccessResponse.RegisterCode(SuccessResponse.Changed, 'Changed')
SuccessResponse.RegisterCode(SuccessResponse.Content, 'Content')


class Class3Response (Message):
    """Subclass for messages that are responses but for which no
    class-level has been provided.

    :coapsect:`12.1.2` specifies that class 3 is a response class, but
    fails to define any unreserved code in the class.
    """

    CodeClass = coapy.util.ClassReadOnly(3)
    """The :attr:`Message.code` *class* component for
    :class:`Class3Response` messages.
    """
Class3Response.RegisterClassCode(Class3Response.CodeClass, Class3Response)


class ClientErrorResponse (Response):
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

    CodeClass = coapy.util.ClassReadOnly(4)
    """The :attr:`Message.code` *class* component for
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
ClientErrorResponse.RegisterCode(ClientErrorResponse.BadRequest, 'Bad Request')
ClientErrorResponse.RegisterCode(ClientErrorResponse.Unauthorized, 'Unauthorized')
ClientErrorResponse.RegisterCode(ClientErrorResponse.BadOption, 'Bad Option')
ClientErrorResponse.RegisterCode(ClientErrorResponse.Forbidden, 'Forbidden')
ClientErrorResponse.RegisterCode(ClientErrorResponse.NotFound, 'Not Found')
ClientErrorResponse.RegisterCode(ClientErrorResponse.MethodNotAllowed, 'Method Not Allowed')
ClientErrorResponse.RegisterCode(ClientErrorResponse.NotAcceptable, 'Not Acceptable')
ClientErrorResponse.RegisterCode(ClientErrorResponse.PreconditionFailed, 'Precondition Failed')
ClientErrorResponse.RegisterCode(ClientErrorResponse.RequestEntityTooLarge, 'Request Entity Too Large')  # nopep8
ClientErrorResponse.RegisterCode(ClientErrorResponse.UnsupportedContentFormat, 'Unsupported Content-Format')  # nopep8


class ServerErrorResponse (Response):
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

    CodeClass = coapy.util.ClassReadOnly(5)
    """The :attr:`Message.code` *class* component for
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
ServerErrorResponse.RegisterCode(ServerErrorResponse.InternalServerError, 'Internal Server Error')
ServerErrorResponse.RegisterCode(ServerErrorResponse.NotImplemented, 'Not Implemented')
ServerErrorResponse.RegisterCode(ServerErrorResponse.BadGateway, 'Bad Gateway')
ServerErrorResponse.RegisterCode(ServerErrorResponse.ServiceUnavailable, 'Service Unavailable')
ServerErrorResponse.RegisterCode(ServerErrorResponse.GatewayTimeout, 'Gateway Timeout')
ServerErrorResponse.RegisterCode(ServerErrorResponse.ProxyingNotSupported, 'Proxying Not Supported')  # nopep8


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


# Back-fill default transmission parameters
coapy.transmissionParameters = TransmissionParameters()


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
