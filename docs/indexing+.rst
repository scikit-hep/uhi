.. _usage-indexing+:

Indexing+
=========

This is an extended version of UHI, called UHI+. This is not implemented in boost-histogram, but is implemented in Hist.


Syntax extensions
-----------------

UHI+ avoids using the standard tags found in UHI by using more advanced Python syntax.

Location based slicing/access: numeric axes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can replace location based indexing ``loc(1.23) → 1.23j`` (a "j" suffix on a number literal). You can shift by an integer, just like with loc: ``2.3j + 1`` will be one bin past the one containing the location "2.3".

.. code:: python3

   v = h[2j)]    # Returns the bin containing "2.0"
   v = h[2j + 1] # Returns the bin above the one containing "2.0"
   h2 = h[2j:]   # Slices starting with the bin containing "2.0"

Location based slicing/access: string axis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have a string based axis, you can use a string directly ``loc("label") → "label"``.

.. code:: python3

   v = h["a"]    # Returns the "a" bin (string category axis)

Rebinning
^^^^^^^^^

You can replace ``rebin(2) → 2j`` in the third slot of a slice.

.. code:: python3

   h2 = h[::2j]    # Modification operations (rebin)
   h2 = h[a:b:2j]  # Modifications can combine with slices

Named based indexing
^^^^^^^^^^^^^^^^^^^^

An optional extension to indexing is expected for histogram implementations that support names. If named axes are supported, any expression that refers to an axis by an integer can also refer to it by a name string. ``.project(*axis: int | str)`` is probably the most common place to see this, but you can also use strings in the UHI dict access, such as:


.. code:: python3

    s = bh.tag.Slicer()

    h[{"a": s[::2j]}]       # rebin axis "a" by two
    h[{"x": s[0:3.5j]}]     # slice axis "x" from 0 to the data coordinate 3.5
    h[{"other": s[0:2:4j]}] # slice and rebin axis "other"
