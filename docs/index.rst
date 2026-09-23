.. meta::
   :description: UHI connects histogramming libraries with an indexing standard,
      the PlottableProtocol, and a serialization format.

UHI: Unified Histogram Interface
=================================

UHI is a library that helps connect other histogramming libraries. It is
primarily intended to be a guide and static type check helper; you do not need
a runtime dependency on UHI. It currently does so with the following
components:

UHI Indexing, which describes a powerful indexing system for histograms,
designed to extend standard Array indexing for Histogram operations.

UHI Indexing+ (referred to as UHI+ for short), which describes a set of
extensions to the standard indexing that make it easier to use on the command
line.

The PlottableProtocol, which describes the minimal and complete set of
requirements for a source library to produce and a plotting library to consume
to plot a histogram, including error bars.

The serialization format, which describes how to store histograms in JSON, ZIP,
HDF5, and ROOT files, with a JSON schema and reference readers and writers in
``uhi.io``.

The ``uhi`` command line tool, which can add histograms from several files
(``uhi add``) and check files against the schema (``uhi validate``).

The testing helpers in ``uhi.testing``, which a library can use to check that
it follows UHI indexing.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   indexing.rst
   indexing+.rst
   plotting.rst
   serialization.md
   testing.md
   changelog.md



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
