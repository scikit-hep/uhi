# Serialization


## Introduction

Histogram serialization has to cover a wide range of formats. As such, we
describe a form for serialization that covers the metadata structure as
JSON-like, with a provided JSON-schema. The data (bins and/or variable edges)
is stored out-of-band in a binary format based on what type of data file you
are in. For very small (primarily 1D) histograms, data is allowed inline as
well.

The following formats are being targeted:

```
┌────────┐ ┌────────┐ ┌────────────┐
│  ROOT  │ │  HDF5  │ │  ZIP/JSON  │
└────────┘ └────────┘ └────────────┘
```

Other formats can be used as well, assuming they support out-of-band data and
text attributes or files for the metadata. We are working on a Zarr backend in
the near future.

## Caveats

This structure was based heavily on boost-histogram, but it is intended to be
general, and can be expanded in the future as needed. As such, the following
limitations are required:

* Serialization followed by deserialization may cause axis changes. Axis types
  may change to an equivalent but less performant axis, growth status will be
  lost, etc. Libraries can record custom `"writer_info"` attributes to improve
  round trips, but histograms must always be openable without the extra info.
* Metadata should also be reasonably sized; some formats like HDF5 may limit
  the size of attributes to 64K.
* Floating point errors could be incurred on conversion, as the storage format
  uses a stable but different representation.
* Axis `name` is only part of the metadata, and is not standardized. This is
  due to lack of support from boost-histogram.

## Design

The following axes types are supported:

* `"regular"`: A regularly spaced set of even bins. Boost-histogram's "integer"
  axes maps to this axis as well. Has `upper`, `lower`, `bins`, `underflow`,
  `overflow`, and `circular` properties.
* `"variable"`: A continuous axis defined by bins+1 edges. Has `edges`, which
  is either an in-line list of numbers or a string pointing to an out-of-band data source.
  Also has `underflow`, `overflow`, and `circular` properties.
* `"category_int"`: A list of integer bins, non-continuous. Has `categories`,
  which is an in-line list of integers. Also has `flow`.
* `"category_str"`: A list of string bins. Has `categories`,
  which is an in-line list of strings. Also has `flow`.
* `"boolean"`: A true/false axis.

Axes with gaps are currently not supported.

All axes support `metadata`, a dictionary of arbitrary data. The values can be
strings, numbers, or booleans. Other value types are not supported. Libraries are encouraged to provide a way to indicate
unserializable metadata; our recommendation is to avoid adding any metadata
that starts with a `@` to the metadata dictionary. Libraries should not
include keys with `None` values, as some formats might not support null values.

The following storages are supported:

* `"int"`: A collection of integers. Boost-histogram's `Int64` and `AtomicInt64`
  map to this, and sometimes `Unlimited`.
* `"double"`: A collection of floating point values. Boost-histogram's
  `Double` storage maps to this, and sometimes `Unlimited`.
* `"weighted"`: A collection of two arrays of floating point values,
  `"values"` and `"variances"`. Boost-histogram's `Weight` storage maps to this.
* `"mean"`: A collection of three arrays of floating point values,
  `"counts"`, `"values"`, and `"variances"`. Boost-histogram's `Mean` storage maps to
  this.
* `"weighted_mean"`: A collection of four arrays of floating point
  values, `"sum_of_weights"`, `"sum_of_weights_squared"`, `"values"`, and
  `"variances"`. Boost-histogram's `WeightedMean` storage maps to this.

All storage types support **empty (metadata-only) histograms**, where the storage
contains only the `"type"` field and no data arrays. This is useful for creating
histograms that contain axes and metadata but no actual bin data. Empty storages
can be filled later or used for schema/template purposes. For example:

```json
{
  "storage": { "type": "int" }
}
```

Empty storages are compatible with all serialization formats and can be converted
to/from dense or sparse forms using the standard conversion functions.

```{versionadded} 1.1

Empty (metadata-only) histogram support.
```

Current backends (such as zip and hdf5) allow flexibility in the size of
integer and floating point storage. It is allowed to use a smaller floating
point or integer storage type for such storages; the reference is 64-bit floats
and 64-bit integers.

A library can fill the optional `"writer_info"` field with a key specific to
the library containing library specific metadata anywhere a metadata field is
allowed. There is one defined key at the Histogram level, `"version"`, which
contains the version of the library that created the histogram. Libraries
should include this key when creating a histogram. It is not required for
reading histograms.  Histogram libraries can put custom metadata here that they
can use to record provenance information or help with same-library round trips.
For example, a histogram created with boost-histogram might contain:

```json
{
  "writer_info": {
    "boost-histogram": {
      "version": "1.0.0",
    }
  },
  "...": "...",
}
```

There is one more required key for each histogram: `"uhi_schema"`, which must
be set to 1 currently. If there is a future revision with a backward
incompatible change, this will be bumped to 2, and readers should always error
on future schemas, and support all older schemas. This is hoped to be
unlikely/rare, but this also serves as a check that this is in fact a uhi
serialization object. Non-breaking changes like additions are allowed without
bumping the schema.

### Named and single histograms

A file can hold either a dictionary of named histograms, or a single histogram
stored directly at the top level:

```json
{
  "one": { "uhi_schema": 1, "axes": ["..."], "storage": { "...": "..." } },
  "two": { "uhi_schema": 1, "axes": ["..."], "storage": { "...": "..." } }
}
```

```json
{ "uhi_schema": 1, "axes": ["..."], "storage": { "...": "..." } }
```

Readers can tell the two forms apart by the `"uhi_schema"` key: it is present
(and required) in a single histogram, and a histogram name is never
`"uhi_schema"` in a dictionary of histograms. The single form is the natural output of `json.dumps` on one
histogram, and it matches the HDF5 layout, where each histogram is a group.

Two schemas are provided. `histogram.schema.json` describes one histogram,
the intermediate representation. `histograms.schema.json` describes a JSON
file, in either form above, and refers to the first schema for each histogram.

```{versionadded} 1.2

The single histogram form is accepted, and the schema is split into
`histogram.schema.json` (one histogram) and `histograms.schema.json` (a file).
```

## Sparse storage

For sparse histograms, storage contains an `index` key. This is a 2D array; the
first dimension has the same number of entries as the number of axes, and the
second dimension has the same number of entries as the number of filled bins.
There should not be any duplicate entries. The values start at 0 for the
underflow bin (if there is one), and are in the same order as the axes. The
data in this case are 1D arrays, one for each bin. For example, take the
following sparse histogram with three filled bins:

```json
{
    "storage": {
        "index": [[0, 1, 2],[3, 3, 4]],
        "values": [5, 6, 7],
    }
}
```

The `0, 3` bin is filled with 5, the `1, 3` bin is filled with 6, and the
`2, 4` bin is filled with 7. If the first axes has `"underflow"` enabled, that
first bin is an underflow bin.

Empty (metadata-only) histograms are unaffected by sparse/dense conversions; they
remain as-is since there is no data to convert.

If a histogram library doesn't support sparse histograms, you can convert a
sparse histogram to a dense one. UHI provides helpers `uhi.io.to_sparse` and
`uhi.io.from_sparse` that can be used to support a library that doesn't support
sparse histograms. Scalar histograms (with no axes) are always dense.


## Adding histograms

`uhi.io.ops.add` sums histograms bin-by-bin, like ROOT's `hadd`. It works on the
intermediate representation (or anything with `_to_uhi_`), so histograms from
different libraries or files can be combined without a histogram library:

```python
import uhi.io.ops

total = uhi.io.ops.add(h1, h2, h3)
```

All inputs must have identical axes (metadata and `writer_info` are ignored
when comparing) and the same storage type. Empty (metadata-only) storages count
as zero. `"mean"` and `"weighted_mean"` storages are merged correctly, not just
summed. The metadata and `writer_info` of the first histogram are kept. The
result is sparse if every input is sparse, and dense otherwise.

```{versionadded} 1.2
```

## CLI/API

The `uhi` command (also `python -m uhi`) provides `add`, which sums the
histograms in several files into one file, like `hadd`:

```console
$ uhi add total.zip run1.zip run2.zip run3.zip
```

Histograms are matched by name. A name that is only in some of the inputs is
copied through. The format is chosen by the file extension: `.json` (a JSON
object mapping names to histograms, or a single histogram), `.zip`,
`.h5`/`.hdf5`/`.hdf` (every group with a `uhi_schema` attribute, at any depth), or
`.root` (every RNTuple, at any depth). The input and output formats do not
have to match, so this also converts between formats. Pass `-f`/`--force` to
overwrite an existing output file.

Add `:path` to an input to select one histogram by name, or a directory or
group of histograms. If every input is a single histogram, the result is a
single histogram; add `:name` to the output to name it (this is required for
the zip and ROOT formats). For named histograms, `:dir` on the output
prefixes every name:

```console
$ uhi add total.json:h run1.json:h run2.zip:sub/h single.json
$ uhi add out.root:merged run1.h5:results run2.h5:results
```

```{versionadded} 1.2
```

You can test a file against the schema with `uhi validate`. This needs the
`schema` extra (`pip install uhi[schema]`). The format is selected by the file
suffix: `.json`, `.zip`, `.h5`/`.hdf5`/`.hdf` (needs the
`hdf5` extra), or `.root` (needs the `uproot` extra or PyROOT). Every histogram in a zip file (each
`*.json` entry), HDF5 file (each group with a `uhi_schema` attribute), or ROOT
file (each RNTuple, searched recursively) is checked:

```console
$ uhi validate some/file.json some/other.zip some/data.h5 some/data.root
```

Add `:path` to restrict the check to one histogram by name, or to a group or
directory inside a zip, HDF5, or ROOT file:

```console
$ uhi validate some/file.json:h some/data.h5:run1/results some/data.root:analysis/main
```

```{versionadded} 1.2
```

Or with code:

```python
import json

import uhi.schema

with filename.open(encoding="utf-8") as f:
    data = json.load(f)

uhi.schema.validate(data)
```

`validate` checks a JSON file object, in either form. Use
`uhi.schema.validate_histogram` to check a single histogram (the intermediate
representation).

`uhi.schema.load` reads any supported file into a JSON-compatible dict (or a
single histogram), with an optional `path` keyword to select a histogram,
group, or directory inside the file:

```python
uhi.schema.validate(uhi.schema.load("data.root", path="analysis"))
```


## Format specific details and helpers

The `uhi` library contains reference implementations of target formats. You can
implement these yourself, but if you are using or have access to Python, feel
free to use `uhi` if that helps.

If an object has a `_to_uhi_` method, that will be used to convert it to a
dictionary following the schema. A `_from_uhi_` classmethod is also
recommended; however, this is generally part of the histogram constructor; if a
UHI object is passed, it should be converted automatically.

### JSON

The simplest format, useful for writing tests. The JSON version is nearly
identical to the intermediate representation; the only difference is that data
is stored as nested lists. It is not intended for large histograms; the ZIP
format (below) is nearly identical and builds on this with out-of-band data.

Two utilities are provided; `uhi.io.json.default` and
`uhi.io.json.object_hook`. These are used with Python's built-in json module to
handle conversions.

```python
import json
import uhi.io.json

ob = json.dumps(h, default=uhi.io.json.default)
uhi_hist = json.loads(ob, object_hook=uhi.io.json.object_hook)
```

Above, `h` is a histogram that supports `_to_uhi_` or an intermediate
representation,`ob` is a JSON string, and `uhi_hist` is an intermediate
representation; you can pass it to `boost_histogram.Histogram` or `hist.Hist`.
This stores a single histogram directly. To store several histograms in one
file, pass a dictionary of histograms instead; both forms are valid.


### ZIP

The zip format is very similar to JSON, but stores data in the numpy zip format.
Arrays are replaced by strings, which represent the `.npy` file inside the zip file
containing the array. The names are arbitrary; see the uhi code if you want to see
how uhi creates names. The metadata is in a file with the name of the histogram and
a `.json` extension.

We provide `uhi.io.zip.write` and `uhi.io.zip.read`, which work with open
`zipfile.ZipFile` objects from the standard library (or probably anything with
a similar API).

```python
import zipfile

import uhi.io.zip

with zipfile.ZipFile("myfile.zip", "w") as zip_file:
    uhi.io.zip.write(zip_file, "histogram", h)

with zipfile.ZipFile("myfile.zip", "r") as zip_file:
    h2 = uhi.io.zip.read(zip_file, "histogram")
```

Above, `h` is a histogram that supports `_to_uhi_` or an intermediate
representation, and `h2` is an intermediate representation; you can pass
it to `boost_histogram.Histogram` or `hist.Hist`. The metadata name in the file
is `"histogram.json"`. The contents of that file are identical to the JSON
format, except arrays are replaced by string names to files inside the zipfile.

### HDF5

The HDF5 format is ideal for combining histograms with other data. You need the
`h5py` library installed too to use this format. There is some extra structure
here compared to the other formats. The groups are `"axes"`, `"ref_axes"`,
`"metadata"`, and `"storage"`. Arrays for the axes are placed in `"ref_axes"`,
since hdf5 doesn't have lists of arrays. Storage arrays are in-place. A
Reference type is used to link the axes array with the data. `"edges"` and
`"categories"` are datasets; the other axes values are attributes (or groups
with attributes, like `"metadata"` and `"writer_info"`, which is a nested
group).

Likewise, the `"storage"` group sets `"type"` as an attribute, the others are
datasets.

We provide `uhi.io.hdf5.read` and `uhi.io.hdf5.write` to write to an open
group.  The structure is relative; you can place it anywhere inside a hdf5
file.

```python
import h5py

import uhi.io.hdf5

with h5py.File("myfile.hdf5", "w") as h5_file:
    uhi.io.hdf5.write(h5_file.create_group("histogram"), h)

with h5py.File("myfile.hdf5", "r") as h5_file:
    h2 = uhi.io.hdf5.read(h5_file["histogram"])
```

Above, `h` is a histogram that supports `_to_uhi_` or an intermediate
representation, and `h2` is an intermediate representation; you can pass it to
`boost_histogram.Histogram` or `hist.Hist`. You should create the group
you want the histogram to be in.

By default, we do not compress arrays smaller than 1,000 elements. You can
control this by setting `min_compress_elements`; set it to 0 to compress all
arrays. You can also pass through `compression` and `compression_opts`.

### ROOT

The ROOT format stores each histogram as a single-entry
[RNTuple](https://root.cern/doc/master/classROOT_1_1RNTuple.html). You can use
[uproot](https://uproot.readthedocs.io) 5.7+ (`pip install uhi[uproot]`) or
[ROOT](https://root.cern) 6.36+ (`conda install -c conda-forge root`) for this
format; both write the same files. The `root` extra installs the `ROOT` package
from PyPI, which is a prerelease and only has Linux wheels. We recommend ROOT
from conda-forge, or uproot. The RNTuple has a `"uhi"` string
field holding the IR as a string and arrays are replaced
by the name of the field holding them. Storage arrays are stored flattened in
`std::vector` fields named after their key (`"values"`, `"variances"`, ...). The shape of these arrays is recovered from the axes when reading.
The `edges` of a variable axis is stored the same way in
a field named `"axis_{i}_edges"`, where `i` is the axis index.

We provide `uhi.io.root.read` and `uhi.io.root.write`, which work with an open
`TFile` or other `TDirectory`.

```python
import ROOT
import uhi.io.root

with ROOT.TFile.Open("myfile.root", "RECREATE") as root_file:
    uhi.io.root.write(root_file, "histogram", h)

with ROOT.TFile.Open("myfile.root") as root_file:
    h2 = uhi.io.root.read(root_file, "histogram")
```

Above, `h` is a histogram that supports `_to_uhi_` or an intermediate
representation, and `h2` is an intermediate representation;
you can pass it to `ROOT.TH1*` or `boost_histogram.Histogram` or `hist.Hist`.

```{versionadded} 1.2
```

With uproot, use `uhi.io.uproot.read` and `uhi.io.uproot.write` with an open
uproot file or directory. Names can include a directory, like `"dir/histogram"`.

```python
import uproot
import uhi.io.uproot

with uproot.recreate("myfile.root") as root_file:
    uhi.io.uproot.write(root_file, "histogram", h)

with uproot.open("myfile.root") as root_file:
    h2 = uhi.io.uproot.read(root_file, "histogram")
```

The `uhi` command uses uproot if it is installed, and PyROOT otherwise.

## Schema

A typing helper for the intermediate representation, `HistogramIR`, is provided
in `uhi.typing.serialization` as a `TypedDict`. The schema, provided in
`resources` as `histogram.schema.json`, also allows strings for data members,
since some formats (like ZIP) put data into an optimized location and specify a
reference to them. The JSON file schema, `histograms.schema.json`, wraps it.

### Rendered schema

```{jsonschema} ../src/uhi/resources/histograms.schema.json
```

```{jsonschema} ../src/uhi/resources/histogram.schema.json
```


### Full schema

The full schemas are below:

```{literalinclude} ../src/uhi/resources/histograms.schema.json
:language: json
```

```{literalinclude} ../src/uhi/resources/histogram.schema.json
:language: json
```
