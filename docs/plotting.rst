.. _usage-plotting:

Plotting
========

This is a description of the ``PlottableProtocol``,. Any plotting library that
accepts an object that follows the ``PlottableProtocol`` can plot object that
follow this protocol, and libraries that follow this protocol are compatible
with plotters.


Using the protocol:
^^^^^^^^^^^^^^^^^^^

Plotters should only depend on the methods and attributes listed below. In short, they are:

* ``h.kind``: The ``bh.Kind`` of the histogram (COUNT or MEAN)
* ``h.values()``: The value (as given by the kind)
* ``h.variances()``: The variance in the value (None if an unweighed histogram was filled with weights)
* ``h.counts()``: How many fills the bin received or the effective number of fills if the histogram is weighted
* ``h.axes``: A Sequence of axes

Axes have:

* ``ax[i]``: A sequence of lower, upper bin, or the discrete bin value (integer or sting)
* ``len(ax)``: The number of bins
* ``ax.traits.circular``: True if circular
* ``ax.traits.discrete``: True if the bin represents a single value (e.g. Integer or Category axes) instead of an interval (e.g. Regular or Variable axes)

Plotters should see if ``.counts()`` is None; no boost-histogram objects currently
return None, but a future storage or different library could.

Also check ``.variances``; if not None, this storage holds variance information and
error bars should be included. Boost-histogram histograms will return something
unless they know that this is an invalid assumption (a weighted fill was made
on an unweighted histogram).

To statically restrict yourself to valid API usage, use ``PlottableHistogram``
as the parameter type to your function (Not needed at runtime).

Implementing the protocol:
^^^^^^^^^^^^^^^^^^^^^^^^^^

Add UHI to your MyPy environment; an example ``.pre-commit-config.yaml`` file:

.. code:: yaml

    - repo: https://github.com/pre-commit/mirrors-mypy
      rev: v0.812
      hooks:
      - id: mypy
        files: src
        additional_dependencies: [uhi, numpy~=1.20.1]


Then, check your library against the Protocol like this:

.. code:: python3

    from typing import TYPE_CHECKING, cast

    if TYPE_CHECKING:
        _: PlottableHistogram = cast(MyHistogram, None)


The full protocol version 1 follows:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

(Also available as ``uhi.typing.plottoble.PlottableProtocol``, for use in tests, etc.

.. literalinclude:: ../src/uhi/typing/plottable.py
   :language: python
