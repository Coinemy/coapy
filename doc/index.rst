.. CoAPy documentation master file

.. Sphinx standard indentations
   # with overline, for parts
   * with overline, for chapters
   =, for sections
   -, for subsections
   ^, for subsubsections
   ", for paragraphs

################################################################
CoAPy: Python Implementation of Constrained Application Protocol
################################################################

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

********
Contents
********

.. toctree::
   :maxdepth: 2

   vision
   releases

******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

**********
References
**********

General Resources
=================
* The `Constrained RESTful Environments (core) Working Group
  <https://datatracker.ietf.org/wg/core/>`_ at IETF.
* `Architectural Styles and the Design of Network-based Software
  <http://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm>`_, Roy
  Fielding's dissertation which defines the concepts underlying
  Representational State Transfer (REST).

CoRE Internet Drafts
====================
* `Constrained Application Protocol (CoAP)
  <https://datatracker.ietf.org/doc/draft-ietf-core-coap/>`_
* `Blockwise transfers in CoAP
  <https://datatracker.ietf.org/doc/draft-ietf-core-block/>`_
* `Observing Resources in CoAP
  <https://datatracker.ietf.org/doc/draft-ietf-core-observe/>`_
* `Group Communication for CoAP
  <https://datatracker.ietf.org/doc/draft-ietf-core-groupcomm/>`_

RFCs
====

* :rfc:`3986` Uniform Resource Identifier (URI): Generic Syntax
* :rfc:`5785` Defining Well-Known Uniform Resource Identifiers (URIs)
* :rfc:`5988` Web Linking
* :rfc:`5952` A Recommendation for IPv6 Address Text Representation
* :rfc:`6690` Constrained RESTful Environment (CoRE) Link Format
