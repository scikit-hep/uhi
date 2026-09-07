.. meta::
   :description: UHI connects histogramming libraries with an indexing standard,
      the PlottableProtocol, and a serialization format.

UHI: Unified Histogram Interface
=================================

UHI is a library that helps connect other Histogramming libraries. It is
primarily indented to be a guide and static type check helper; you do not need
an runtime dependency on UHI. It currently does so with the following
components:

UHI Indexing, which describes a powerful indexing system for histograms,
designed to extend standard Array indexing for Histogram operations.

UHI Indexing+ (referred to as UHI+ for short), which describes a set of
extensions to the standard indexing that make it easier to use on the command
line.

The PlottableProtocol, which describes the minimal and complete set of
requirements for a source library to produce and a plotting library to consume
to plot a histogram, including error bars.


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
