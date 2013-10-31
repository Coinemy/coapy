.. domain:

.. Sphinx standard indentations
   # with overline, for parts
   * with overline, for chapters
   =, for sections
   -, for subsections
   ^, for subsubsections
   ", for paragraphs

***************
Domain Concepts
***************

.. warning::

   This document is a work in progress and should not be taken as
   complete.

The `CoAP specification
<https://datatracker.ietf.org/doc/draft-ietf-core-coap/>`_ defines a
protocol, but does so with some terms that are not always used
precisely, and others that are left undefined beyond the implications of
their conventional meaning.  The result is an incomplete and ambiguous
specification that does not translate directly into a reference
implementation such as CoAPy.

This document refines and redefines terminology to support a domain
model for the communications patterns supported by CoAP.  It is further
informed by draft specifications for an `observation capability
<https://datatracker.ietf.org/doc/draft-ietf-core-observe/>`_ (which
relaxes the notion away from REST to allow a time series of responses to
a single query) and a `block transfer capabliity
<https://datatracker.ietf.org/doc/draft-ietf-core-block/>`_ (which
conveys large messages through a sequence of smaller message
transmissions).

For the most part concepts and names introduced derive from those
implicit in the CoAP specification.  In a few cases CoAP concepts are
refactored so the description of their behavior depends on more basic
concepts rather than being defined independently.

.. note::

   Within this document a reference to a technical term "concept"
   appears as `concept`.  Generally use of a term that has a technical
   meaning should be take to be that meaning, even if the specific use
   is not so marked.

   A technical term at its definition is denoted :dfn:`concept`.
   Whether this is visibly distinct from its use form `concept` depends
   on the style used when formatting this document.

   To avoid duplication, where a description supports multiple cases
   with slight variations, parentheses denote the alternatives.  Thus a
   sentence "A confirmable (non-confirmable) message transmission
   expires after ``EXCHANGE_LIFETIME`` (``NON_LIFETIME``) seconds"
   identifies a general concept (that message transmissions have time
   limit on their relevance) and its specific characteristics (that the
   duration is ``EXCHANGE_LIFETIME`` for confirmable messages and
   ``NON_LIFETIME`` for non-confirmable messages).


Overview of Concepts
====================

This section provides a brief introduction to the basic domain concepts.
They are described more completely in other sections.

Layers
------

CoAP envisions a two-layer protocol: a message layer and a
request/response layer.  Extension beyond base CoAP reveals the
request/response layer is too abstract, resulting in a recursive concept
of what a request/response exchange would be.  In this domain model
there are three CoAP layers, placed in context in this sequence (from
higher to lower layer similar to the OSI model):

* application layer
* transaction layer (requests paired with responses via Token)
* exchange layer (request message paired with response message via Token)
* message layer (CON/NON message paired with ACK/RST message via MID)
* transport layer (UDP, DTLS, etc.)

Working from the bottom layer up, a `message transmission` comprises:

* One `CON/NON message` with a given MID

* Zero or one `reply message` matching that MID

The primitive component of a request/response exchange (or REST
transaction) is an :dfn:`exchange`, comprising:

* One `request message` with a given Token

* Zero or one `response messages` matching that Token

In turn, a :dfn:`transaction` comprises:

* One `request` (potentially comprised of multiple request messages)
  with a given Token

* One or more `responses` (potentially comprised of multiple response
  messages) matching that Token

Depending on how the transaction is decomposed, it may consist of a
single exchange, a sequence of exchanges (as per the -block extension),
an initial exchange with additional response message transmissions (as
per the -observe extension), or some other abstraction (as per
the -groupcomm extension).

CoAP lacks the terminology to describe how exceptional behavior in lower
layers impacts the behavior of higher layers.  This domain model
introduces a concept of `resolution` to `success` or `failure` that
applies to message transmissions, exchanges, and transactions.  Failure
at a lower layer generally propagates to failure at a higher layer.

Messages
--------

A message comprises various fields (:coapsect:`3`) including:

* A Type being one of CON, NON, ACK, RST

* A Code comprising a integer :dfn:`class` and an integer :dfn:`detail`
  denoted herein by a dot-separated decimals, e.g. ``2.04``

* A Message ID (aka :dfn:`MID`) represented as integer in the range
  0..65535

* A Token representing an opaque sequence of zero to eight octets

* An emptiable set of Options

* An optional Payload

CoAP defines a byte encoding of a message; the details of that are
within the specification and are not relevant to the domain model.

Options
-------

An Option (:coapsect:`3.1`) comprises:

* An :dfn:`option number` as an unsigned integer in the range 0..65535

  .. note::
     The ability to express an option number greater than 65535 within
     an encoded message is assumed to be a flaw in the specification.

* An :dfn:`option format` (:coapsect:`3.1`) specified externally for a
  given option number

* An :dfn:`option length` specified in bytes (octets).  Constraints on
  the length are defined externally for a specific option number

* An :dfn:`option value` within the domain of the format as constrained
  by the length

Endpoints
---------

An Endpoint comprises:

* A unicast IP host address

* A host port

* A security context

Related concepts:

* A :dfn:`source endpoint` is the endpoint that transmits a CoAP message

* A :dfn:`destination endpoint` is the endpoint to which a CoAP message
  is transmitted.

* A :dfn:`client` is an endpoint that initiates a CoAP request.

* A :dfn:`server` is an endpoint that receives and responds to a CoAP
  request.

Other concepts related to endpoints may be derived when the groupcomm
extension is considered.

Congestion
----------

The :dfn:`transmission parameters` (:coapsect:`4.8`) describe features
related to congestion management, including number of outstanding
interactions permitted, maximum data rate, etc.  References to those
parameters are denoted thus: ``EXCHANGE_LIFETIME``.

Unlike transmission parameters, which are simple values, the domain
model requires understanding of the means by which retransmission of
confirmable messages is authorized.  A :dfn:`Binary Exponential Back-Off
(BEBO) state` comprises:

* A retransmission counter, initialized to zero

* A timeout, initialized to a value between ``ACK_TIMEOUT`` and
  ``(ACK_TIMEOUT * ACK_RANDOM_FACTOR)``

The process by which these values are used is described in
:coapsect:`4.2`.  This document refines the description to clarify what
a transmission is at a given layer, and the conditions under which
retransmission becomes unnecessary or disallowed.

Message-Layer Concepts
======================

Taxonomy by Type
----------------

* A :dfn:`confirmable message` is one with Type CON.

* A :dfn:`non-confirmable message` is one with Type NON.

* An :dfn:`acknowledgement message` is one with Type ACK.

* A :dfn:`reset message` is one with Type RST.

.. note::

  * A confirmable message may be `empty` or may be a `request message`
    or a `response message`.

  * A non-confirmable message may be `empty` or may be a `request
    message` or a `response message`.

  * An acknowledgement message may be `empty` or may be a `response
    message`.

  * A reset message must be `empty`.

Taxonomy by Code
----------------

* An :dfn:`empty message` is a message with Code ``0.00``.  A message
  that is not empty is a :dfn:`non-empty message`.

  .. note::

     * An empty message is encoded to a four-octet sequence.  It carries
       no Token, Options, nor Payload.

* A :dfn:`request message` is a message with Code in class 1.

* A :dfn:`response message` is a message with Code in class 2, 4, or 5.
  It is a message-layer component of a transaction-layer concept.

  .. note::
     Although a `response message` may also be a `reply message`, these
     concepts are orthogonal: there are response messages that are not
     reply messages, and reply messages that are not response messages.

There is no generic terminology for messages with Code in class 0, 3, 6,
or 7.

General Use
-----------

In most uses an unqualified :dfn:`message` is a message with type CON or
NON.  Where disambiguation is critical, such a message is called a
:dfn:`CON/NON message`, and the term "message" may include ACK and RST
messages.  `Sender` and `receiver` are generally used as roles defined
relative to a CON/NON message.  Take care when speaking of them in the
context of a `reply message`.

A :dfn:`reply message` is a message with type ACK or RST.  It is coupled
with the message to which it is a reply through a shared MID value.  A
reply message is transmitted by the receiver of a message to that
message's sender.

Operations
----------

* A (CoAP) :dfn:`message transmission` is the act of sending a `CON/NON
  message`.  The source endpoint is the message :dfn:`sender`; the
  destination endpoint is the message :dfn:`receiver`.  The message transmission event occurs
  once for each message.

* A (CoAP) :dfn:`message reply` is the act of sending a `reply message`.
  A message of type CON may evoke a reply of type ACK or RST; a CoAP
  message of type NON may evoke a reply of type RST.  Neither ACK nor
  RST may evoke replies.  A CoAP message transmission will evoke at most
  one CoAP message reply.

* The MID of a `CON/NON message` is determined by the sender.  The
  sender of a message should not re-use a MID for another confirmable
  (non-confirmable) message until at least ``EXCHANGE_LIFETIME``
  (``NON_LIFETIME``) seconds have passed since the first transport layer
  transmission of the message.

* A :dfn:`transport layer transmission` is the act of submitting to the
  transport layer a block of data that is to be conveyed to a
  destination endpoint.  Messages of type NON, ACK, and RST normally
  have exactly one transport layer transmission (an exception occurs for
  reply messages under deduplication rules).  Messages of type CON may
  be transmitted up to ``1+MAX_RETRANSMIT`` transport layer
  transmissions per BEBO state rules while the message transmision
  remains `unresolved`.

* To reduce unnecessary retransmissions, a received confirmable message
  should be acknowledged within ``ACK_TIMEOUT`` seconds, where the
  acknowledgement message is `empty` unless a response message is
  permitted and available.

* A message transmission may be :dfn:`cancelled` by the sender.

  + Cancellation may occur at any time prior to the first
    transport-layer transmission.  In that situation the behavior is
    operationally equivalent to having never submitted the message for
    transmission.

  + If a confirmable message transmission has not been `resolved` it may
    be cancelled at (instead of) transport-layer retransmission.  In
    this situation the sole effect of cancellation is to inhibit further
    transport-layer retransmissions: it has no effect on whether the
    transmission is considered to have `succeeded` or `failed`, when the
    transmission `expires`, or (consequently) whether the message is
    still `outstanding`.

  + A message transmission cannot be cancelled after it has been
    resolved or the last permitted transmission has occurred.

  .. note::

     The only mention of cancellation from outside the message layer
     is in :coapsect:`4.2` in the context of stopping retransmission
     of a request to which the client no longer needs a response, or
     when there is "some other indication that the CON message did
     arrive".  The effect of cancellation is not defined by CoAP.

     The description here specifies cancellation for all messages
     regardless of type and does not attempt to restrict the situations
     where it may be appropriate.  The decision that a cancelled
     confirmable message does not circumvent the message being
     `outstanding` is based on the fact that past transmissions are
     congestion-related actions and the decision to not to use
     BEBO-authorized transmissions should not circumvent
     congestion-based restrictions on when a new message may be
     transmitted.  That cancellation does not immediately resolve the
     transmission to "failed" follows from the possibility a reply may
     yet arrive before the normal expiration of the transmission.

     Message cancellation is an action performed by the sender.  The
     receiver may not be able to determine that the transmission was
     cancelled.

* A message transmission :dfn:`expires` at a specific time to provide a
  deadline by which it will be `resolved`:

  + A confirmable request message transmission `expires` at
    ``EXCHANGE_LIFETIME`` seconds after the first transport-layer
    transmission.

  + A confirmable non-request message transmission `expires` at
    ``MAX_TRANSMIT_WAIT`` seconds after the first transport-layer
    transmission.

  + A non-confirmable request message transmission `expires` at
    ``NON_LIFETIME`` seconds after the first transport-layer
    transmission.

  + A non-confirmable non-request message transmission `expires` at
    ``ACK_TIMEOUT*ACK_RANDOM_FACTOR`` seconds after the first
    transport-layer transmission.

  .. note::

     :coapsect:`4.8.2` and :coapsect:`4.7` together imply the concept of
     an expiration time for message transmission, but leave the
     expiration for non-confirmable messages undefined.  The text above
     provides values based on the principles underlying the defined
     expiration for confirmable messages.

* A message transmission is :dfn:`resolved` once its disposition is
  determined to be `success` or `failure`.  Prior to that point the
  message transmission is `unresolved`.  Be aware that the sender and
  the receiver of a message transmission may reach conflicting
  dispositions for a given transmission.

* From the perspective of a message receiver, the disposition of the
  reception is either `accept` or `reject`.  Rejecting a message is used
  as a technical term within the CoAP protocol description for
  situations where a particular disposition is required.

  + :dfn:`Accept`: An accepted message may be made visible above the
    message layer.  An accepted confirmable message must evoke a reply
    with type ACK.  A message that is not rejected is assumed to be
    accepted.

  + :dfn:`Reject`: A rejected message is not directly visible above the
    message layer.  When a message is rejected a reset message must
    (CON) or may (NON) be sent as reply.  This message influences but
    does not define the sender's disposition of the transmission.

  .. note::

     Message rejection is an action performed by the receiver.  The
     sender may not be able to determine whether rejection has occurred.

* From the perspective of a message sender, the disposition of a
  transmission is :dfn:`success` or :dfn:`failure`.  Success or failure
  of an message transmission is determined by a sender based on time,
  received reply message type, and information provided by other layers:

  + If the received `reply message` has type RST, the transmission has
    failed.

  + If the received `reply message` has type ACK, the transmission has
    succeeded.

  + Success and failure may be communicated through transport-layer
    notifications (e.g., a message transmission may fail if it is
    rejected by transport security checks).

  + Success and failure may be communicated through exchange-layer
    notifications (e.g., a request message transmission may succeed if a
    response message is received).

  + Success and failure may be communicated through transaction-layer
    notifications (e.g., a response message that conveys the URI of a
    created resource may succeed if a request to retrieve that resource
    is received).

  + Success and failure may be communicated through application-layer
    notifications.

  + A message transmission that has not been resolved by the time it
    `expires` has failed (succeeded) if it is confirmable
    (non-confirmable).

  .. note::

     :coapsect:`4.2` uses the uncapitalized term "acknowledgement" in a
     way that may variously be either an `acknowledgement message` or an
     external indication that the message transmission can be resolved
     as successful from external signals (e.g., the proposed case of
     receiving a `response message` signalling the success of a
     confirmable request message transmission).  Contrariwise it uses
     "reset" rather than then entertaining the possibility of an
     external signal indicative of failure (such as transport-layer
     rejection).

     Text in this section related to the need to keep for deduplication
     the transmitted acknowledgement replies for received requests even
     after a successful confirmable response message should not be read
     to suggest that the intent is that such external evidence does not
     eliminate the need to receive a reply message.  Instead note the
     specific authorization to stop retransmission if there is "some
     other indication that the CON message did arrive".  However the
     ambiguity is reflected in the above use of "may succeed",
     indicating that whether an acknowledgement (or failure) is inferred
     from any given external signal is left to the implementation of
     other layers.

* A :dfn:`duplicate` message is a confirmable (non-confirmable) message
  received from the same source endpoint within ``EXCHANGE_LIFETIME``
  (``NON_LIFETIME``) seconds after receipt of another CON/NON message
  with the same MID.

* If a `duplicate` message is received, then:

  + if a reply had been sent for the first message, that reply should be
    re-transmitted unchanged; and

  + the duplicate is otherwise ignored

  .. note::

     This refactors :coapsect:`4.5` by leveraging more precise
     terminology, and eliminates the unnecessary text related to relaxed
     rules that explicitly authorize an implementation to do things that
     result in behavior that is externally indistinguishable from having
     satisfied the requirement.

* A message transmission is :dfn:`outstanding (at the message layer)` if
  it is `unresolved`.

* An endpoint R :dfn:`responds to` (or :dfn:`is responsive to`) endpoint
  S with respect to a message transmission to R if

  + S receives a reply to the message transmission; or

  + S `resolves` the message transmission as `successful` through a
    notification from a higher layer (exchange, transaction,
    application)

  .. note::

     Responsiveness of an endpoint affects whether congestion rules
     apply to transmissions destined for that endpoint, but is not
     explicitly defined in CoAP.  The text here creates a definition
     consistent with the common use of the term "responsive".  On the
     theory that a transport layer might accept a message without
     properly conveying it to the CoAP server, confirmation from the
     transport layer is not a sign of responsiveness.

Exchange Layer
==============

.. warning::

   This section has not been completed.  Only a few concepts are
   described, and they have not been verified.

* An exchange is :dfn:`outstanding (at the exchange layer)` if a
  `response message` is still expected.

* A response message is `expected` for an exchange if the exchange has
  not `expired` and its request message has not `resolved` as `failure`.

* An exchange :dfn:`expires` at some time:

  + An exchange for which the `request message transmission` has not
    been `resolved` `expires` at the same time the request message
    transmission expires.

  + CoAP does not define an expiration for exchanges for which the
    request message transmission was successful.


Transaction Layer
=================

.. warning::

   This section has not been completed.


Congestion Management (Cross Layer; see also individual layers)
===============================================================

.. note::

  This section is intended to refine the text of :coapsect:`4.7`,
  paraphrased as:

  * A confirmable message transmission is `outstanding` at the message
    layer if the sender still expects an ACK.  An ACK is not expected if
    a reply message has been received or if MAX_TRANSMIT_WAIT has passed
    since the first transport layer transmission.

  * A non-confirmable message transmission is "outstanding" under
    undefined circumstances.

* An :dfn:`outstanding interaction` is one of:

   + an `outstanding exchange`; or

   + an `outstanding message transmission` that is not the request
     message transmission of an outstanding exchange.

* When congestion rules are in force:

  + A client must not allow more than ``NSTART`` simultaneous
    outstanding interactions to a given server (endpoint).

  + endpoint S must not transmit messages to endpoint R at a rate that
    exceeds ``PROBING_RATE`` bytes per second unless R responds to those
    messages.

* Congestion rules apply to client requests to servers per :coapsect:`4.7`

* Congestion rules apply to -observe responses from servers per
  observe-11.

  .. warning::

     Or not; as of current writing it appears -observe will define its
     own rules for congestion management instead of sharing the
     principles used by :coapsect:`4.7`.

Commentary:

* The `BEBO state` of a confirmable message transmission specifies when
  additional transport layer transmissions may be allowed.  The
  :dfn:`BEBO span` for an initial timeout of ITO is::

        ((2 ** (1 + MAX_RETRANSMIT)) - 1) * ITO

  The BEBO span shall not exceed ``MAX_TRANSMIT_WAIT``.

  .. note::

     At this time it is unclear whether the `BEBO span` is a necessary
     domain concept.
