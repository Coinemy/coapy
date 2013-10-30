.. _vision:

********************
Architectural Vision
********************

This chapter specifies the underlying requirements and motivations for
CoAPy.

* The implementation should be suitable as a reference implementation,
  supporting exactly the specification as detailed in the to-be RFC.

* The architecture should be highly abstracted so as to decouple key
  concepts such as messages and requests/responses.

* A well-defined and complete logging infrastructure should support tracing
  all protocol operations, including timestamps.

* All protocol-defined configuration constants (such as congestion controls)
  should be mutable within the ranges allowed.

* The implementation should be extensible to handle new options and
  behaviors that are described in additional specifications such as block_
  and observe_.

* The target environment is Python 2.6 and higher including Python 3.  The
  implementation may require may require Python 3 features that were not
  originally available in Python 2, as long as they are present in Python
  2.6.8 and Python 2.7.5.  Supporting infrastructure such as unit tests may
  additionally use any Python 3 features available in Python 2.7.3.

.. _block: https://datatracker.ietf.org/doc/draft-ietf-core-block/
.. _observe: https://datatracker.ietf.org/doc/draft-ietf-core-observe/
