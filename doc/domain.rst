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

Overview of Concepts
====================

Layer
-----

* application layer
* transaction layer (requests paired with responses via Token)
* exchange layer (request message paired with response message via Token)
* message layer (CON/NON message paired with ACK/RST message via MID)
* transport layer (UDP, DTLS, etc.)

A `message transmission` comprises:

* One `CON/NON message` with a given MID

* Zero or one `reply message` matching that MID

An :dfn:`exchange` comprises:

* One `request message` with a given Token

* Zero or one `response messages` matching that Token

A :dfn:`transaction` comprises:

* One `request` (potentially comprised of multiple request messages)
  with a given Token

* One or more `responses` (potentially comprised of multiple response
  messages) matching that Token

A concept of `resolution` to `success` or `failure` applies to message
transmissions, exchanges, and transactions.  Failure at a lower layer
propagates to failure at a higher layer.

Messages
--------

A message comprises various fields including:

* A Type being one of CON, NON, ACK, RST

* A Code comprising a integer :dfn:`class` and an integer :dfn:`detail`
  denoted by a dot-separated value, e.g. ``2.04``

* A Message ID (aka :dfn:`MID`) represented as integer in the range
  0..65535

* A Token representing an opaque sequence of zero to eight octets

* An emptiable set of Options

* An optional Payload

Options
-------

An Option comprises:

* An :dfn:`option number` as an unsigned integer in the range 0..65535

  .. note::
     The ability to express an option number greater than 65535 within
     an encoded message is assumed to be a flaw in the specification.

* An :dfn:`option format` specified externally for a given option number

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

Congestion
----------

A Binary Exponential Back-Off (BEBO) state comprises:

* A retransmission counter, initialized to zero

* A timeout, initialized to a value between ``ACK_TIMEOUT`` and
  ``(ACK_TIMEOUT * ACK_RANDOM_FACTOR)``


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

* An :dfn:`empty message` is a message with Code 0.00.  A message that
  is not empty is a :dfn:`non-empty message`.

  .. note::

     * An empty message is represented by a four-octet sequence.  It
       carries no Token, Options, nor Payload.

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
:dfn:`CON/NON message`, and generic `message` will include ACK and RST
messages.  `Sender` and `receiver` are generally used as roles defined
relative to a CON/NON message, hence take care when speaking of them in
the context of a reply message.

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
  RST may evoke replies.  A CoAP message transmission should evoke at
  most one CoAP message reply.

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
  involve up to ``1+MAX_RETRANSMIT`` transport layer transmissions,
  terminating when the timeout of the last transmission completes or
  when the message transmission has been `resolved`.

* A message transmission may be :dfn:`cancelled` by the sender.

  + Cancellation may occur at any time prior to the first
    transport-layer transmission.  In that situation the behavior is
    operationally equivalent to having never submitted the message for
    transmission.

  + If a confirmable message transmission has not been `resolved` it may
    be cancelled at (instead of) transport-layer retransmission.  In
    this situation the sole effect of cancellation is to inhibit further
    transport-layer retransmissions: it has no effect on whether the
    transmission is considered to have `succeeded` or `failed`, or on
    when the transmission `expires`.

  + A message transmission cannot be cancelled after it has been
    resolved or the last permitted retransmission has occurred.

  .. note::

     Message cancellation is an action performed by the sender.  The
     receiver may not be able to determine that the transmission was
     cancelled.

* A message transmission :dfn:`expires` at a specific time to provide a
  deadline by which it is `resolved`:

  + A confirmable request message transmission `expires` at
    ``EXCHANGE_LIFETIME`` seconds after the first transport-layer
    transmission.

  + A confirmable non-request message transmission `expires` at
    ``MAX_TRANSMIT_WAIT`` seconds after the first transport-layer
    transmission.

  + A non-confirmable request message transmission `expires` at
    ``NON_LIFETIME`` seconds after the first transport-layer
    transmission. (Refines CoAP)

  + A non-confirmable non-request message transmission `expires` at
    ``ACK_TIMEOUT*ACK_RANDOM_FACTOR`` seconds after the first
    transport-layer transmission.

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
  reply message type, and transport-layer information.

  + If the received `reply message` has type RST, the transmission has
    failed.

  + If the received `reply message` has type ACK, the transmission has
    succeeded.

  + Success and failure may be communicated through transport-layer
    notifications (e.g., a message may fail if it is rejected by
    transport security checks).

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

* A message transmission is :dfn:`resolved` once its disposition is
  determined to be `success` or `failure`.  Prior to that point the
  message transmission is `unresolved`.

* A :dfn:`duplicate` message is a confirmable (non-confirmable) message
  received from the same source endpoint within ``EXCHANGE_LIFETIME``
  (``NON_LIFETIME``) seconds after receipt of another CON/NON message
  with the same MID.

* If a `duplicate` message is received, then:

  + if a reply had been sent for the first message, that reply should be
    re-transmitted unchanged; and

  + the duplicate is otherwise ignored

  .. note::

     This refines :coapsect:`4.5`

* A message transmission is :dfn:`outstanding (at the message layer)` if
  it is unresolved.

* An endpoint R :dfn:`responds to` (or :dfn:`is responsive to`) endpoint
  S with respect to a message transmission to R if

  + S receives a reply to the message transmission; or

  + S `resolves` the message transmission as `successful` through a
    notification from a higher layer (exchange, transaction,
    application)


Exchange Layer
==============

TBD

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

TBD

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

* Congestion rules apply to observe responses from servers per
  observe-11.

Commentary:

* The "BEBO (binary exponential back-off) state" of a confirmable
  message specifies when additional transport layer transmissions may be
  allowed.  The BEBO "span" for an initial timeout of ITO is::

        ((2 ** (1 + MAX_RETRANSMIT)) - 1) * ITO

  The BEBO span shall not exceed MAX_TRANSMIT_WAIT.