################################################################
CoAPy: Python Implementation of Constrained Application Protocol
################################################################

Documentation for this project is at:  http://pabigot.github.io/coapy

.. warning::

   This project is a work in progress.  In its current state it supports
   most low level message operations, but lacks the infrastructure for
   REST transactions, automated management of cache state, or even
   primitive examples.

CoAP is an effort of the `Constrained RESTful Environments (core)
<https://datatracker.ietf.org/wg/core/>`_ working group of the Internet
Engineering Task Force (IETF).  From the charter:

  CoRE is providing a framework for resource-oriented applications intended
  to run on constrained IP networks. A constrained IP network has limited
  packet sizes, may exhibit a high degree of packet loss, and may have a
  substantial number of devices that may be powered off at any point in time
  but periodically "wake up" for brief periods of time.  These networks and
  the nodes within them are characterized by severe limits on throughput,
  available power, and particularly on the complexity that can be supported
  with limited code size and limited RAM per node.

`Constrained Application Protocol (CoAP)
<https://datatracker.ietf.org/doc/draft-ietf-core-coap/>`_ is a specialized
web transfer protocol for use with constrained nodes and constrained (e.g.,
low-power, lossy) networks.

CoAPy is a Python reference implementation of CoAP.

Pre-History
===========

One of the first implementations of CoAP under Python was also called CoAPy,
with the last public release 0.0.2 on July 22nd 2010 conformant to (perhaps)
draft 01 of the specification.  The committee soon changed the specification
so the implementation did not conform, and due to lack of value to the
sponsor `People Power Company <http://www.peoplepowerco.com>`_ the effort
was aborted.  The original effort is still available on `SourceForge
<https://sourceforge.net/projects/coapy/>`_.

The framework to which this documentation applies was developed from scratch
without reference to the previous implementation, and is asserted to not be
a derivative work.
