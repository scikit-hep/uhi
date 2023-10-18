# Serialization

:::{warning}

Serialization is in draft currently. Once at least one implementation is ready,
we will remove this warning and release UHI 0.5.

:::

## Introduction

Histogram serialization has to cover a wide range of formats. As such, we
describe a form for serialization that covers the metadata structure as
JSON-like, with a provided JSON-schema. The data (bins and/or variable edges)
is stored out-of-band in a binary format based on what type of data file you
are in.  For very small (primarily 1D) histograms, data is allowed inline as
well.

The following formats are being targeted:

```
┌────────┐ ┌────────┐ ┌───────┐
│  ROOT  │ │  HDF5  │ │  ZIP  │
└────────┘ └────────┘ └───────┘
```

Other formats can be used as well, assuming they support out-of-band data and
text attributes or files for the metadata.

## Caveats

This structure was based heavily on boost-histogram, but it is intended to be
general, and can be expanded in the future as needed. As such, the following
limitations are required:

* Serialization followed by deserialisation may cause axis changes. Axis types
  may change to an equivalent but less performant axis, growth status will be
  lost, etc.
* Metadata must be expressible as JSON. It should also be reasonably sized; some
  formats like HDF5 may limit the size of attributes to 64K.
* Floating point errors could be incurred on conversion, as the storage format
  uses a stable but different representation.
* Axis `name` is only part of the metadata, and is not standardized. This is
  due to lack of support from boost-histogram.

## Design

The following axes types are supported:

* `"regular"`: A regularly spaced set of even bins. Boost-histogram's "integer"
  axes maps to this axis as well. Has `upper`, `lower`, `bins`, `underflow`,
  `overflow`, and `circular` properties. `circular` defaults to False if not
  present.
* `"variable"`: A continuous axis defined by bins+1 edges. Has `edges`, which
  is either an in-line list of numbers or a string pointing to an out-of-band data source.
  Also has `underflow`, `overflow`, and `circular` properties. `circular`
  defaults to False if not present.
* `"category_int"`: A list of integer bins, non-continuous. Has `categories`,
  which is an in-line list of integers. Also has `flow`.
* `"category_str"`: A list of string bins. Has `categories`,
  which is an in-line list of strings. Also has `flow`.
* `"boolean"`: A true/false axis.

Axes with gaps are currently not supported.

All axes support `metadata`, a string-valued dictionary of arbitrary, JSON-like data.

The following storages are supported:

* `"int"`: A collection of integers. Boost-histogram's Int64 and AtomicInt64
  map to this, and sometimes Unlimited.
* `"double"`: A collection of 64-bit floating point values. Boost-histogram's
  Double storage maps to this, and sometimes Unlimited.
* `"weighted"`: A collection of two arrays of 64-bit floating point values,
  `"value"` and `"variance"`. Boost-histogram's Weight storage maps to this.
* `"mean"`: A collection of three arrays of 64-bit floating point values,
  "count", "value", and "variance". Boost-histogram's Mean storage maps to
  this.
* `"weighted_mean"`: A collection of four arrays of 64-bit floating point
  values, `"sum_of_weights"`, `"sum_of_weights_squared"`, `"values"`, and
  `"variances"`. Boost-histogram's WeighedMean storage maps to this.

## CLI/API

You can currently test a JSON file against the schema by running:

```console
$ python -m uhi.schema some/file.json
```

Or with code:

```python
import uhi.schema

uhi.schema.validate("some/file.json")
```

Eventually this should also be usable for JSON's inside zip, HDF5 attributes,
and maybe more.

```{warning}

Currently, this spec describes **how to prepare the metadata** for one of the
targeted backends. It does not yet cover backend specific details, like how to
define and use the binary resource locator strings or how to store the data.
JSON is not a target spec, but just part of the ZIP spec, meaning the files
that currently "pass" the tool above would be valid inside a `.zip` file
eventually, but are not valid by themselves.
```

## Rendered schema

```{jsonschema} ../src/uhi/resources/histogram.schema.json
```


## Full schema

The full schema is below:

```{literalinclude} ../src/uhi/resources/histogram.schema.json
:language: json
```
