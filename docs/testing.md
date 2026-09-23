# Testing

UHI has some testing helpers for use in test suites. This is primarily for
library authors.

## Indexing

You can see if your library passes the indexing test suite. We provide
three sets of tests: 1D, 2D, and 3D tests. These can be implemented on
your own library (`my.Histogram` in this example) like this:

```python
import uhi.testing.indexing


class TestAccess1D(uhi.testing.indexing.Indexing1D[my.Histogram]):
    @classmethod
    def make_histogram(cls) -> my.Histogram:
        return my.Histogram(cls.get_uhi())


class TestAccess2D(uhi.testing.indexing.Indexing2D[my.Histogram]):
    @classmethod
    def make_histogram(cls) -> my.Histogram:
        return my.Histogram(cls.get_uhi())


class TestAccess3D(uhi.testing.indexing.Indexing3D[my.Histogram]):
    @classmethod
    def make_histogram(cls) -> my.Histogram:
        return my.Histogram(cls.get_uhi())
```

If you don't support serialization, then you can manually set the values with
the UHI item, or check the docstrings to see what the correct parameters are.

Import the module (`import uhi.testing.indexing`), as in the example above. Do
not use `from uhi.testing.indexing import Indexing1D`: this puts the base classes
in your test module, and some runners (such as unittest) then try to run them as
tests too.
